from __future__ import annotations

from typing import TYPE_CHECKING

from pygame.math import Vector2

from ..core.agent import Agent, AgentTraits, AgentState
from ..utils.math2d import _clamp_length
from .groups import register_group_base, set_group

if TYPE_CHECKING:
    from ..core.world import World


def mutate_group(
    world: World, group_id: int, can_create_groups: bool, position: Vector2, traits: AgentTraits
) -> int:
    if not can_create_groups:
        return group_id
    founder = max(0.0, world._clamp_traits(traits).founder)
    if group_id == world._UNGROUPED:
        if world._rng.next_float() < min(1.0, world._config.feedback.group_birth_seed_chance * founder):
            new_group = world._next_group_id
            world._next_group_id += 1
            register_group_base(world, new_group, position)
            return new_group
        return world._UNGROUPED
    if world._rng.next_float() < min(1.0, world._config.feedback.group_mutation_chance * founder):
        new_group = world._next_group_id
        world._next_group_id += 1
        register_group_base(world, new_group, position)
        return new_group
    return group_id


def apply_life_cycle(
    world: World,
    agent: Agent,
    neighbor_count: int,
    same_group_neighbors: int,
    can_create_groups: bool,
    population: int | None = None,
    sim_time: float = 0.0,
    traits: AgentTraits | None = None,
) -> int:
    dt = world._config.time_step
    births_added = 0
    if population is None:
        population = len(world._agents)
    traits = world._clamp_traits(agent.traits) if traits is None else traits
    base_cell_key = world._cell_key(agent.position)
    pending_food = world._pending_food
    pending_pheromone = world._pending_pheromone
    metabolism_multiplier = world._trait_metabolism_multiplier(traits)
    speed_cost = agent.velocity.length() * 0.05 * metabolism_multiplier
    metabolism = (world._config.species.metabolism_per_second * metabolism_multiplier + speed_cost) * dt
    excess_energy = max(0.0, agent.energy - world._config.species.energy_soft_cap)
    metabolism += (
        excess_energy * world._config.species.high_energy_metabolism_slope * dt * metabolism_multiplier
    )
    stress_drain = neighbor_count * world._config.feedback.stress_drain_per_neighbor * dt
    agent.energy -= metabolism + stress_drain + agent.stress * dt

    if neighbor_count > world._config.feedback.local_density_soft_cap:
        agent.stress += 0.1 * dt
        disease_resistance = world._trait_disease_resistance(traits)
        disease_risk = neighbor_count * world._config.feedback.disease_probability_per_neighbor * dt
        disease_risk = disease_risk / max(0.1, disease_resistance)
        if world._rng.next_float() < disease_risk:
            agent.alive = False
            pending_food[base_cell_key] = (
                pending_food.get(base_cell_key, 0.0) + world._config.environment.food_from_death
            )
            return births_added
    else:
        agent.stress = max(0.0, agent.stress - 0.05 * dt)

    max_consumption = world._config.environment.food_consumption_rate * dt
    gained_energy = 0.0
    remaining = max_consumption
    if remaining > 0.0:
        available = world._environment.sample_food(base_cell_key)
        if available > 0:
            consumed = min(available, remaining)
            world._environment.consume_food(base_cell_key, consumed)
            gained_energy += consumed
    agent.energy += gained_energy

    allow_reproduction = world._config.initial_population >= 10
    if (
        allow_reproduction
        and agent.energy > world._config.species.reproduction_energy_threshold
        and agent.age > world._config.species.adult_age
        and len(world._agents) + len(world._birth_queue) < world._config.max_population
    ):
        density_factor = 1.0
        if neighbor_count > world._config.feedback.local_density_soft_cap:
            excess = neighbor_count - world._config.feedback.local_density_soft_cap
            drop = excess * world._config.feedback.density_reproduction_slope
            density_factor = max(
                0.0, min(1.0, world._config.feedback.density_reproduction_penalty - drop)
            )
        group_factor = 1.0
        if agent.group_id != world._UNGROUPED:
            penalty = same_group_neighbors * world._config.feedback.group_reproduction_penalty_per_ally
            group_factor = max(
                world._config.feedback.group_reproduction_min_factor,
                1.0 - penalty,
            )
        trait_factor = world._trait_reproduction_factor(traits)
        base_reproduction = max(0.0, float(world._config.feedback.reproduction_base_chance))
        reproduction_chance = max(
            0.0, min(1.0, base_reproduction * density_factor * group_factor * trait_factor)
        )
        if world._rng.next_float() < reproduction_chance:
            child_energy = agent.energy * 0.5
            agent.energy -= child_energy + world._config.species.birth_energy_cost
            child_group = mutate_group(world, agent.group_id, can_create_groups, agent.position, traits)
            if agent.group_id == world._UNGROUPED and child_group != world._UNGROUPED:
                set_group(world, agent, child_group)
            child_cooldown = (
                world._config.feedback.group_merge_cooldown_seconds
                if child_group != world._UNGROUPED
                and world._config.feedback.group_merge_cooldown_seconds > 0.0
                else 0.0
            )
            spawn_distance = max(0.5, float(world._config.feedback.min_separation_distance))
            child_lineage = agent.lineage_id
            child_traits = world._copy_traits(traits)
            if world._config.evolution.enabled:
                if (
                    world._config.evolution.lineage_mutation_chance > 0.0
                    and world._rng.next_float() < world._config.evolution.lineage_mutation_chance
                ):
                    child_lineage = world._allocate_lineage_id()
                child_traits = world._mutate_traits(traits)
            child_appearance_h, child_appearance_s, child_appearance_l = world._inherit_appearance(agent)
            child_velocity = _clamp_length(agent.velocity, world._trait_speed_limit(child_traits))
            child = Agent(
                id=world._next_id,
                generation=agent.generation + 1,
                group_id=child_group,
                position=agent.position + world._rng.next_unit_circle() * spawn_distance,
                velocity=child_velocity,
                heading=world._heading_from_velocity(child_velocity),
                energy=child_energy,
                age=0.0,
                state=AgentState.WANDER,
                lineage_id=child_lineage,
                traits=child_traits,
                traits_dirty=False,
                appearance_h=child_appearance_h,
                appearance_s=child_appearance_s,
                appearance_l=child_appearance_l,
                group_cooldown=child_cooldown,
                last_desired=child_velocity.copy(),
            )
            world._next_id += 1
            world._birth_queue.append(child)
            births_added += 1
            if child_group != world._UNGROUPED:
                pheromone_key = (base_cell_key, child_group)
                pending_pheromone[pheromone_key] = (
                    pending_pheromone.get(pheromone_key, 0.0)
                    + world._config.environment.pheromone_deposit_on_birth
                )

    hazard_per_second = (
        world._config.feedback.base_death_probability_per_second
        + agent.age * world._config.feedback.age_death_probability_per_second
        + neighbor_count * world._config.feedback.density_death_probability_per_neighbor_per_second
    )
    hazard_chance = min(1.0, hazard_per_second * dt)
    if hazard_chance > 0.0 and world._rng.next_float() < hazard_chance:
        agent.alive = False
        pending_food[base_cell_key] = (
            pending_food.get(base_cell_key, 0.0) + world._config.environment.food_from_death
        )
        return births_added

    if agent.energy <= 0 or agent.age >= world._config.species.max_age:
        agent.alive = False
        pending_food[base_cell_key] = (
            pending_food.get(base_cell_key, 0.0) + world._config.environment.food_from_death
        )
    return births_added
