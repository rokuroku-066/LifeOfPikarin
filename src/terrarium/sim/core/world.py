from __future__ import annotations

import math
from typing import Any, Dict, List, Set
from time import perf_counter

from pygame.math import Vector2

from .agent import Agent, AgentState, AgentTraits
from .config import SimulationConfig
from .environment import EnvironmentGrid
from .rng import DeterministicRng
from .spatial_grid import SpatialGrid
from ..systems import fields, groups, lifecycle, metrics as metrics_system, steering
from ..types.metrics import TickMetrics
from ..types.snapshot import Snapshot, SnapshotFields, SnapshotMetadata, SnapshotWorld
from ..utils.math2d import _clamp_length_xy_f, _clamp_value, _heading_from_velocity
_CLIMATE_RNG_SALT = 0xC0A1F00D5EED1234


def _derive_stream_seed(seed: int, salt: int) -> int:
    return (int(seed) ^ int(salt)) & 0xFFFFFFFFFFFFFFFF


class World:
    _UNGROUPED = -1

    def __init__(self, config: SimulationConfig):
        self._config = config
        self._rng = DeterministicRng(config.seed)
        self._climate_rng = DeterministicRng(_derive_stream_seed(config.seed, _CLIMATE_RNG_SALT))
        self._grid = SpatialGrid(config.cell_size)
        self._environment = EnvironmentGrid(config.cell_size, config.environment, config.world_size)
        self._agents: List[Agent] = []
        self._birth_queue: List[Agent] = []
        self._id_to_index: Dict[int, int] = {}
        self._neighbor_offsets: List[Vector2] = []
        self._neighbor_agents: List[Agent] = []
        self._neighbor_dist_sq: List[float] = []
        self._group_scratch: Set[int] = set()
        self._pending_food: Dict[tuple[int, int], float] = {}
        self._pending_danger: Dict[tuple[int, int], float] = {}
        self._pending_pheromone: Dict[tuple[tuple[int, int], int], float] = {}
        self._ungrouped_neighbors: List[Agent] = []
        self._group_counts_scratch: Dict[int, int] = {}
        self._group_lineage_counts: Dict[int, int] = {}
        self._group_sizes: Dict[int, int] = {}
        self._group_bases: Dict[int, Vector2] = {}
        self._next_lineage_id = 0
        self._next_id = 0
        self._next_group_id = 0
        self._max_population_seen = 0
        self._metrics: TickMetrics | None = None
        self._environment_accumulator = 0.0
        self._food_regen_noise_multiplier = 1.0
        self._food_regen_noise_target = 1.0
        self._food_regen_noise_time_to_next_sample = 0.0
        self._cached_population_stats: tuple[int, float, float, int, int] = (0, 0.0, 0.0, 0, 0)
        self._population_stats_dirty = True
        self._refresh_vision_cache()
        self._bootstrap_population()

    @property
    def agents(self) -> List[Agent]:
        return self._agents

    @property
    def metrics(self) -> TickMetrics | None:
        return self._metrics

    def reset(self) -> None:
        self._agents.clear()
        self._birth_queue.clear()
        self._environment.reset()
        self._grid.clear()
        self._neighbor_offsets.clear()
        self._neighbor_agents.clear()
        self._neighbor_dist_sq.clear()
        self._group_scratch.clear()
        self._pending_food.clear()
        self._pending_danger.clear()
        self._pending_pheromone.clear()
        self._group_sizes.clear()
        self._group_lineage_counts.clear()
        self._group_bases.clear()
        self._rng.reset()
        self._climate_rng.reset()
        self._next_lineage_id = 0
        self._id_to_index.clear()
        self._metrics = None
        self._next_id = 0
        self._next_group_id = 0
        self._max_population_seen = 0
        self._environment_accumulator = 0.0
        self._food_regen_noise_multiplier = 1.0
        self._food_regen_noise_target = 1.0
        self._food_regen_noise_time_to_next_sample = 0.0
        self._cached_population_stats = (0, 0.0, 0.0, 0, 0)
        self._population_stats_dirty = True
        self._refresh_vision_cache()
        self._bootstrap_population()

    def step(self, tick: int) -> TickMetrics:
        start = perf_counter()
        config = self._config
        species = config.species
        feedback = config.feedback
        dt = config.time_step
        self._pending_food.clear()
        self._pending_danger.clear()
        self._pending_pheromone.clear()

        sim_time = tick * self._config.time_step
        can_form_groups = sim_time >= self._config.feedback.group_formation_warmup_seconds

        self._group_sizes.clear()
        current_population = len(self._agents)
        if current_population > self._max_population_seen:
            self._max_population_seen = current_population

        group_update_stride = max(1, int(feedback.group_update_stride))
        group_update_threshold = max(0, int(feedback.group_update_population_threshold))
        use_group_stride = current_population >= group_update_threshold and group_update_stride > 1
        steering_stride = max(1, int(feedback.steering_update_stride))
        steering_threshold = max(0, int(feedback.steering_update_population_threshold))
        use_steering_stride = current_population >= steering_threshold and steering_stride > 1
        detach_radius_sq = (
            feedback.group_detach_radius * feedback.group_detach_radius if use_group_stride else 0.0
        )
        close_threshold = feedback.group_detach_close_neighbor_threshold if use_group_stride else 0

        self._grid.clear()
        for agent in self._agents:
            if agent.group_id >= 0:
                self._group_sizes[agent.group_id] = self._group_sizes.get(agent.group_id, 0) + 1
            self._grid.insert(agent)

        neighbor_checks = 0
        births = 0
        deaths = 0

        vision_cell_offsets = self._vision_cell_offsets
        vision_radius_sq = self._vision_radius_sq
        population = 0
        energy_sum = 0.0
        age_sum = 0.0
        ungrouped = 0
        group_ids = self._group_scratch
        group_ids.clear()
        danger_present = self._environment.has_danger()

        for agent in self._agents:
            if not agent.alive:
                continue

            if agent.traits_dirty:
                traits = self._clamp_traits(agent.traits)
                agent.traits_dirty = False
            else:
                traits = agent.traits
            speed_limit = self._trait_speed_limit(traits)

            self._grid.collect_neighbors_precomputed(
                agent.position,
                vision_cell_offsets,
                vision_radius_sq,
                self._neighbor_agents,
                self._neighbor_offsets,
                exclude_id=agent.id,
                out_dist_sq=self._neighbor_dist_sq,
            )
            neighbor_count = len(self._neighbor_agents)
            neighbor_checks += neighbor_count
            neighbor_dist_sq = self._neighbor_dist_sq
            if use_group_stride and (tick + agent.id) % group_update_stride != 0:
                same_group_neighbors = 0
                same_group_close_neighbors = 0
                if agent.group_id != self._UNGROUPED:
                    for other, dist_sq in zip(self._neighbor_agents, neighbor_dist_sq):
                        if other.group_id != agent.group_id:
                            continue
                        same_group_neighbors += 1
                        if dist_sq <= detach_radius_sq:
                            same_group_close_neighbors += 1
                    if same_group_close_neighbors >= close_threshold:
                        agent.group_lonely_seconds = 0.0
                    else:
                        agent.group_lonely_seconds += dt
                else:
                    agent.group_lonely_seconds = 0.0
                groups.decay_group_cooldown(self, agent)
            else:
                same_group_neighbors = groups.update_group_membership(
                    self,
                    agent,
                    self._neighbor_agents,
                    self._neighbor_offsets,
                    neighbor_dist_sq,
                    can_form_groups,
                    traits=traits,
                )

            steering_update = not use_steering_stride or (tick + agent.id) % steering_stride == 0
            if steering_update:
                base_cell_key = self._cell_key(agent.position)
                desired, sensed_danger = steering.compute_desired_velocity(
                    self,
                    agent,
                    self._neighbor_agents,
                    self._neighbor_offsets,
                    speed_limit,
                    return_sensed=True,
                    neighbor_dist_sq=neighbor_dist_sq,
                    traits=traits,
                    danger_present=danger_present,
                    base_cell_key=base_cell_key,
                )
                agent.last_desired = desired
                agent.last_sensed_danger = sensed_danger
            else:
                desired = agent.last_desired
                sensed_danger = agent.last_sensed_danger
            accel_x = desired.x - agent.velocity.x
            accel_y = desired.y - agent.velocity.y
            accel_x, accel_y = _clamp_length_xy_f(accel_x, accel_y, species.max_acceleration)
            vel_x = agent.velocity.x + accel_x * dt
            vel_y = agent.velocity.y + accel_y * dt
            vel_x, vel_y = _clamp_length_xy_f(vel_x, vel_y, speed_limit)
            agent.velocity.update(vel_x, vel_y)
            new_position = Vector2(
                agent.position.x + vel_x * dt,
                agent.position.y + vel_y * dt,
            )
            new_position = steering.resolve_overlap(
                self, new_position, self._neighbor_offsets, neighbor_dist_sq
            )
            reflected_position, reflected_velocity = self._reflect(
                new_position, agent.velocity, config.world_size
            )
            agent.position = reflected_position
            agent.velocity.update(reflected_velocity)
            self._update_heading(agent)
            agent.age += dt

            births += lifecycle.apply_life_cycle(
                self,
                agent,
                neighbor_count,
                same_group_neighbors,
                can_form_groups,
                current_population,
                sim_time,
                traits=traits,
            )
            if agent.state == AgentState.FLEE or sensed_danger:
                danger_key = self._cell_key(agent.position)
                pending_danger = self._pending_danger
                pending_danger[danger_key] = (
                    pending_danger.get(danger_key, 0.0)
                    + self._config.environment.danger_pulse_on_flee
                )
            if agent.alive:
                population += 1
                energy_sum += agent.energy
                age_sum += agent.age
                if agent.group_id == self._UNGROUPED:
                    ungrouped += 1
                else:
                    group_ids.add(agent.group_id)

        if self._birth_queue:
            for born in self._birth_queue:
                population += 1
                energy_sum += born.energy
                age_sum += born.age
                if born.group_id == self._UNGROUPED:
                    ungrouped += 1
                else:
                    group_ids.add(born.group_id)
        self._apply_births()
        deaths += self._remove_dead()
        active_groups = group_ids
        groups.prune_group_bases(self, active_groups)
        fields.apply_field_events(self)
        fields.tick_environment(self, active_groups)

        elapsed_ms = (perf_counter() - start) * 1000.0
        stats = self._update_cached_population_stats(population, energy_sum, age_sum, group_ids, ungrouped)
        metrics = metrics_system.create_metrics(
            tick, births, deaths, neighbor_checks, elapsed_ms, stats
        )
        self._metrics = metrics
        return metrics

    def snapshot(self, tick: int) -> Snapshot:
        metrics = self._metrics if self._metrics is not None else self._snapshot_metrics_from_state(tick)
        agents_payload = [self._agent_snapshot(agent) for agent in self._agents if agent.alive]
        metadata = SnapshotMetadata(
            world_size=self._config.world_size,
            sim_dt=self._config.time_step,
            tick_rate=0.0 if self._config.time_step <= 0 else 1.0 / self._config.time_step,
            seed=self._config.seed,
            config_version=self._config.config_version,
        )
        fields = SnapshotFields(
            food=self._environment.export_food_cells(),
            pheromones=self._environment.export_pheromone_field(),
        )
        return Snapshot(
            tick=tick,
            metrics=metrics,
            agents=agents_payload,
            world=SnapshotWorld(size=self._config.world_size),
            metadata=metadata,
            fields=fields,
        )

    def _bootstrap_population(self) -> None:
        for _ in range(self._config.initial_population):
            traits = self._clamp_traits(AgentTraits())
            lineage = self._allocate_lineage_id()
            speed_limit = self._trait_speed_limit(traits)
            pos = Vector2(
                self._rng.next_range(0.0, self._config.world_size),
                self._rng.next_range(0.0, self._config.world_size),
            )
            velocity = self._rng.next_unit_circle() * (speed_limit * 0.3)
            agent = Agent(
                id=self._next_id,
                generation=0,
                group_id=self._UNGROUPED,
                position=pos,
                velocity=velocity,
                heading=self._heading_from_velocity(velocity),
                energy=self._config.species.reproduction_energy_threshold * self._config.species.initial_energy_fraction_of_threshold,
                age=self._sample_initial_age(),
                state=AgentState.WANDER,
                lineage_id=lineage,
                traits=traits,
                traits_dirty=False,
                wander_dir=self._rng.next_unit_circle(),
                wander_time=self._config.species.wander_refresh_seconds,
                last_desired=velocity.copy(),
            )
            self._agents.append(agent)
            self._next_id += 1

    def _refresh_vision_cache(self) -> None:
        self._vision_radius = self._config.species.vision_radius
        self._vision_radius_sq = self._vision_radius * self._vision_radius
        self._vision_cell_offsets = self._grid.build_neighbor_cell_offsets(self._vision_radius)

    def _sample_initial_age(self) -> float:
        min_age = max(0.0, self._config.species.initial_age_min)
        default_max = min(self._config.species.adult_age, self._config.species.max_age * 0.5)
        max_age = self._config.species.initial_age_max if self._config.species.initial_age_max > 0 else default_max
        max_age = max(0.0, min(max_age, self._config.species.max_age))
        if max_age < min_age:
            min_age, max_age = max_age, min_age
        return self._rng.next_range(min_age, max_age)

    def _allocate_lineage_id(self) -> int:
        lineage = self._next_lineage_id
        self._next_lineage_id += 1
        return lineage

    @staticmethod
    def _heading_from_velocity(vector: Vector2) -> float:
        return _heading_from_velocity(vector)

    def _update_heading(self, agent: Agent) -> None:
        if agent.velocity.length_squared() > 1e-8:
            agent.heading = self._heading_from_velocity(agent.velocity)

    def _compute_size(self, agent: Agent) -> float:
        maturity = min(1.0, agent.age / max(1e-5, self._config.species.adult_age))
        energy_factor = min(1.0, agent.energy / max(1e-5, self._config.species.reproduction_energy_threshold))
        size = 0.4 + 0.4 * maturity + 0.2 * energy_factor
        return max(0.1, min(1.0, size))

    def _clamp_traits(self, traits: AgentTraits) -> AgentTraits:
        clamp = self._config.evolution.clamp
        traits.speed = _clamp_value(traits.speed, clamp.speed[0], clamp.speed[1])
        traits.metabolism = _clamp_value(traits.metabolism, clamp.metabolism[0], clamp.metabolism[1])
        traits.disease_resistance = _clamp_value(traits.disease_resistance, clamp.disease_resistance[0], clamp.disease_resistance[1])
        traits.fertility = _clamp_value(traits.fertility, clamp.fertility[0], clamp.fertility[1])
        traits.sociality = _clamp_value(traits.sociality, clamp.sociality[0], clamp.sociality[1])
        traits.territoriality = _clamp_value(traits.territoriality, clamp.territoriality[0], clamp.territoriality[1])
        traits.loyalty = _clamp_value(traits.loyalty, clamp.loyalty[0], clamp.loyalty[1])
        traits.founder = _clamp_value(traits.founder, clamp.founder[0], clamp.founder[1])
        traits.kin_bias = _clamp_value(traits.kin_bias, clamp.kin_bias[0], clamp.kin_bias[1])
        return traits

    def _copy_traits(self, traits: AgentTraits) -> AgentTraits:
        return AgentTraits(
            speed=traits.speed,
            metabolism=traits.metabolism,
            disease_resistance=traits.disease_resistance,
            fertility=traits.fertility,
            sociality=traits.sociality,
            territoriality=traits.territoriality,
            loyalty=traits.loyalty,
            founder=traits.founder,
            kin_bias=traits.kin_bias,
        )

    def _mutate_traits(self, parent_traits: AgentTraits) -> AgentTraits:
        evolution = self._config.evolution
        mutated = self._copy_traits(parent_traits)
        strength = evolution.mutation_strength
        if strength <= 0.0:
            return self._clamp_traits(mutated)
        mutated.speed += self._rng.next_range(-strength, strength) * evolution.speed_mutation_weight
        mutated.metabolism += self._rng.next_range(-strength, strength) * evolution.metabolism_mutation_weight
        mutated.disease_resistance += self._rng.next_range(-strength, strength) * evolution.disease_resistance_mutation_weight
        mutated.fertility += self._rng.next_range(-strength, strength) * evolution.fertility_mutation_weight
        mutated.sociality += self._rng.next_range(-strength, strength) * evolution.sociality_mutation_weight
        mutated.territoriality += self._rng.next_range(-strength, strength) * evolution.territoriality_mutation_weight
        mutated.loyalty += self._rng.next_range(-strength, strength) * evolution.loyalty_mutation_weight
        mutated.founder += self._rng.next_range(-strength, strength) * evolution.founder_mutation_weight
        mutated.kin_bias += self._rng.next_range(-strength, strength) * evolution.kin_bias_mutation_weight
        return self._clamp_traits(mutated)

    def _trait_reproduction_factor(self, traits: AgentTraits) -> float:
        resistance_penalty = 0.7 + 0.3 / max(0.5, traits.disease_resistance)
        speed_penalty = 0.8 + 0.2 / max(0.6, traits.speed)
        fertility_bonus = traits.fertility
        factor = fertility_bonus * resistance_penalty * speed_penalty
        return _clamp_value(factor, 0.35, 1.5)

    def _trait_speed_limit(self, traits: AgentTraits) -> float:
        return self._config.species.base_speed * traits.speed

    def _trait_metabolism_multiplier(self, traits: AgentTraits) -> float:
        speed_penalty = 0.6 + 0.4 * traits.speed
        return _clamp_value(traits.metabolism * speed_penalty, 0.2, 2.5)

    def _trait_disease_resistance(self, traits: AgentTraits) -> float:
        return _clamp_value(traits.disease_resistance, 0.25, 4.0)

    def _agent_snapshot(self, agent: Agent) -> Dict[str, float]:
        speed = agent.velocity.length()
        return {
            "id": agent.id,
            "x": agent.position.x,
            "y": agent.position.y,
            "vx": agent.velocity.x,
            "vy": agent.velocity.y,
            "group": agent.group_id,
            "behavior_state": agent.state.value,
            "phase": "end" if not agent.alive else "loop",
            "age": agent.age,
            "energy": agent.energy,
            "size": self._compute_size(agent),
            "is_alive": agent.alive,
            "speed": speed,
            "heading": agent.heading,
            "lineage_id": agent.lineage_id,
            "generation": agent.generation,
            "trait_speed": agent.traits.speed,
            "appearance_seed": agent.id,
            "importance": 1.0,
        }

    def _cell_key(self, position: Vector2) -> tuple[int, int]:
        return self._environment._cell_key(position)

    def _apply_births(self) -> None:
        for agent in self._birth_queue:
            self._agents.append(agent)
        self._birth_queue.clear()

    def _refresh_index_map(self) -> None:
        self._id_to_index = {agent.id: i for i, agent in enumerate(self._agents)}
        if self._agents:
            max_lineage = max(agent.lineage_id for agent in self._agents)
            self._next_lineage_id = max(self._next_lineage_id, max_lineage + 1)

    def _remove_dead(self) -> int:
        deaths = 0
        survivors = []
        for agent in self._agents:
            if agent.alive:
                survivors.append(agent)
            else:
                deaths += 1
        self._agents = survivors
        return deaths

    @staticmethod
    def _reflect(position: Vector2, velocity: Vector2, world_size: float) -> tuple[Vector2, Vector2]:
        x, y = position.x, position.y
        vx, vy = velocity.x, velocity.y

        while True:
            crossed = False
            if x < 0:
                x = -x
                vx = -vx
                crossed = True
            if x > world_size:
                x = 2 * world_size - x
                vx = -vx
                crossed = True
            if y < 0:
                y = -y
                vy = -vy
                crossed = True
            if y > world_size:
                y = 2 * world_size - y
                vy = -vy
                crossed = True
            if not crossed:
                break

        return Vector2(x, y), Vector2(vx, vy)

    def _active_group_ids(self) -> Set[int]:
        groups: Set[int] = set()
        for agent in self._agents:
            if agent.group_id != self._UNGROUPED:
                groups.add(agent.group_id)
        for agent in self._birth_queue:
            if agent.group_id != self._UNGROUPED:
                groups.add(agent.group_id)
        return groups

    def _snapshot_metrics_from_state(self, tick: int) -> TickMetrics:
        population, avg_energy, avg_age, groups, ungrouped = self._latest_population_stats()
        return TickMetrics(
            tick=tick,
            population=population,
            births=0,
            deaths=0,
            average_energy=avg_energy,
            average_age=avg_age,
            groups=groups,
            neighbor_checks=0,
            ungrouped=ungrouped,
            tick_duration_ms=0.0,
        )

    def _latest_population_stats(self) -> tuple[int, float, float, int, int]:
        if self._population_stats_dirty:
            return self._recalculate_population_stats()
        return self._cached_population_stats

    def _recalculate_population_stats(self) -> tuple[int, float, float, int, int]:
        population = 0
        energy_sum = 0.0
        age_sum = 0.0
        ungrouped = 0
        group_ids = self._group_scratch
        group_ids.clear()
        for agent in self._agents:
            if not agent.alive:
                continue
            population += 1
            energy_sum += agent.energy
            age_sum += agent.age
            if agent.group_id == self._UNGROUPED:
                ungrouped += 1
            else:
                group_ids.add(agent.group_id)
        return self._update_cached_population_stats(population, energy_sum, age_sum, group_ids, ungrouped)

    def _update_cached_population_stats(
        self, population: int, energy_sum: float, age_sum: float, group_ids: Set[int], ungrouped: int
    ) -> tuple[int, float, float, int, int]:
        avg_energy = 0.0 if population == 0 else energy_sum / population
        avg_age = 0.0 if population == 0 else age_sum / population
        groups = len(group_ids)
        group_ids.clear()
        self._cached_population_stats = (population, avg_energy, avg_age, groups, ungrouped)
        self._population_stats_dirty = False
        return self._cached_population_stats
