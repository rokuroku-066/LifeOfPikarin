from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Set
from time import perf_counter

from pygame.math import Vector2

from .agent import Agent, AgentState, AgentTraits
from .config import SimulationConfig
from .environment import EnvironmentGrid
from .rng import DeterministicRng
from .spatial_grid import SpatialGrid

ZERO = Vector2()
_CLIMATE_RNG_SALT = 0xC0A1F00D5EED1234


def _derive_stream_seed(seed: int, salt: int) -> int:
    return (int(seed) ^ int(salt)) & 0xFFFFFFFFFFFFFFFF


def _safe_normalize(vector: Vector2) -> Vector2:
    return _safe_normalize_xy(vector.x, vector.y)


def _safe_normalize_xy(x: float, y: float) -> Vector2:
    magnitude_sq = x * x + y * y
    if magnitude_sq < 1e-10:
        return Vector2()
    inv = 1.0 / math.sqrt(magnitude_sq)
    return Vector2(x * inv, y * inv)


def _clamp_length_xy(x: float, y: float, max_length: float) -> Vector2:
    if max_length <= 0:
        return Vector2()
    magnitude_sq = x * x + y * y
    if magnitude_sq <= max_length * max_length:
        return Vector2(x, y)
    if magnitude_sq == 0:
        return Vector2()
    inv = max_length / math.sqrt(magnitude_sq)
    return Vector2(x * inv, y * inv)


def _clamp_length_xy_f(x: float, y: float, max_length: float) -> tuple[float, float]:
    if max_length <= 0.0:
        return 0.0, 0.0
    magnitude_sq = x * x + y * y
    max_sq = max_length * max_length
    if magnitude_sq <= max_sq:
        return x, y
    if magnitude_sq <= 1e-18:
        return 0.0, 0.0
    inv = max_length / math.sqrt(magnitude_sq)
    return x * inv, y * inv


def _clamp_length(vector: Vector2, max_length: float) -> Vector2:
    if max_length <= 0:
        return Vector2()
    magnitude_sq = vector.length_squared()
    if magnitude_sq <= max_length * max_length:
        return vector
    if magnitude_sq == 0:
        return Vector2()
    return vector.normalize() * max_length


def _heading_from_velocity(vector: Vector2) -> float:
    if vector.length_squared() < 1e-12:
        return 0.0
    return math.atan2(vector.y, vector.x)


def _clamp_value(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


@dataclass(slots=True)
class TickMetrics:
    tick: int
    population: int
    births: int
    deaths: int
    average_energy: float
    average_age: float
    groups: int
    neighbor_checks: int
    ungrouped: int
    tick_duration_ms: float = 0.0


@dataclass(slots=True)
class Snapshot:
    tick: int
    metrics: TickMetrics
    agents: List[Dict[str, Any]]
    world: "SnapshotWorld"
    metadata: "SnapshotMetadata"
    fields: "SnapshotFields"


@dataclass(slots=True)
class SnapshotWorld:
    size: float


@dataclass(slots=True)
class SnapshotMetadata:
    world_size: float
    sim_dt: float
    tick_rate: float
    seed: int
    config_version: str


@dataclass(slots=True)
class SnapshotFields:
    food: Dict[str, Any]
    pheromones: Dict[str, Any]


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
                self._decay_group_cooldown(agent)
            else:
                same_group_neighbors = self._update_group_membership(
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
                desired, sensed_danger = self._compute_desired_velocity(
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
            new_position = self._resolve_overlap(new_position, self._neighbor_offsets, neighbor_dist_sq)
            reflected_position, reflected_velocity = self._reflect(
                new_position, agent.velocity, config.world_size
            )
            agent.position = reflected_position
            agent.velocity.update(reflected_velocity)
            self._update_heading(agent)
            agent.age += dt

            births += self._apply_life_cycle(
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
        self._prune_group_bases(active_groups)
        self._apply_field_events()
        self._tick_environment(active_groups)

        elapsed_ms = (perf_counter() - start) * 1000.0
        stats = self._update_cached_population_stats(population, energy_sum, age_sum, group_ids, ungrouped)
        metrics = self._create_metrics(tick, births, deaths, neighbor_checks, elapsed_ms, stats)
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

    def _decay_group_cooldown(self, agent: Agent) -> None:
        if agent.group_cooldown > 0.0:
            agent.group_cooldown = max(0.0, agent.group_cooldown - self._config.time_step)

    def _set_group(self, agent: Agent, group_id: int) -> None:
        agent.group_id = group_id
        agent.group_lonely_seconds = 0.0
        if group_id == self._UNGROUPED:
            agent.group_cooldown = 0.0
            return
        if self._config.feedback.group_merge_cooldown_seconds > 0.0:
            agent.group_cooldown = max(
                agent.group_cooldown, self._config.feedback.group_merge_cooldown_seconds
            )

    def _register_group_base(self, group_id: int, position: Vector2) -> None:
        if group_id == self._UNGROUPED:
            return
        if group_id in self._group_bases:
            return
        self._group_bases[group_id] = Vector2(position)

    def _prune_group_bases(self, active_groups: Set[int]) -> None:
        if not self._group_bases:
            return
        if not active_groups:
            self._group_bases.clear()
            return
        for gid in list(self._group_bases.keys()):
            if gid not in active_groups:
                self._group_bases.pop(gid, None)

    def _recruit_split_neighbors(
        self, previous_group: int, new_group: int, neighbors: List[Agent], neighbor_offsets: List[Vector2]
    ) -> None:
        max_recruits = self._config.feedback.group_split_recruitment_count
        if max_recruits <= 0 or new_group == self._UNGROUPED:
            return
        radius_sq = self._config.feedback.group_cohesion_radius * self._config.feedback.group_cohesion_radius
        candidates: List[tuple[float, Agent]] = []
        for other, offset in zip(neighbors, neighbor_offsets):
            if other.group_id != previous_group:
                continue
            dist_sq = offset.length_squared()
            if dist_sq > radius_sq:
                continue
            candidates.append((dist_sq, other))
        if not candidates:
            return
        candidates.sort(key=lambda item: item[0])
        for _, recruit in candidates[:max_recruits]:
            self._set_group(recruit, new_group)

    def _update_group_membership(
        self,
        agent: Agent,
        neighbors: List[Agent],
        neighbor_offsets: List[Vector2],
        neighbor_dist_sq: List[float],
        can_form_groups: bool,
        traits: AgentTraits | None = None,
    ) -> int:
        original_group = agent.group_id
        traits = self._clamp_traits(agent.traits) if traits is None else traits
        feedback = self._config.feedback
        loyalty = max(0.1, traits.loyalty)
        kin_bias = traits.kin_bias
        use_kin_bias = abs(kin_bias - 1.0) > 1e-6
        prev_lonely = agent.group_lonely_seconds
        self._decay_group_cooldown(agent)
        self._group_counts_scratch.clear()
        self._ungrouped_neighbors.clear()
        if use_kin_bias:
            self._group_lineage_counts.clear()
        same_group_neighbors = 0
        same_group_close_neighbors = 0
        detach_radius_sq = feedback.group_detach_radius * feedback.group_detach_radius
        close_threshold = feedback.group_detach_close_neighbor_threshold

        for other, offset, dist_sq in zip(neighbors, neighbor_offsets, neighbor_dist_sq):
            if other.group_id == self._UNGROUPED:
                self._ungrouped_neighbors.append(other)
            if agent.group_id != self._UNGROUPED and other.group_id == agent.group_id:
                same_group_neighbors += 1
                if dist_sq <= detach_radius_sq:
                    same_group_close_neighbors += 1
            if other.group_id >= 0:
                self._group_counts_scratch[other.group_id] = self._group_counts_scratch.get(other.group_id, 0) + 1
                if use_kin_bias and other.lineage_id == agent.lineage_id:
                    self._group_lineage_counts[other.group_id] = self._group_lineage_counts.get(other.group_id, 0) + 1

        majority_group = self._UNGROUPED
        majority_count = 0
        switch_group = self._UNGROUPED
        switch_count = 0
        majority_score = -float("inf")
        switch_score = -float("inf")
        for gid, count in self._group_counts_scratch.items():
            if use_kin_bias:
                kin_count = self._group_lineage_counts.get(gid, 0)
                score = count + (kin_bias - 1.0) * kin_count
            else:
                score = float(count)
            if score > majority_score or (math.isclose(score, majority_score) and count > majority_count):
                majority_group = gid
                majority_count = count
                majority_score = score
            if gid == agent.group_id:
                continue
            if score > switch_score or (math.isclose(score, switch_score) and count > switch_count):
                switch_group = gid
                switch_count = count
                switch_score = score

        if agent.group_id == self._UNGROUPED:
            agent.group_lonely_seconds = 0.0
        else:
            if same_group_close_neighbors >= close_threshold:
                agent.group_lonely_seconds = 0.0
            else:
                agent.group_lonely_seconds = prev_lonely + self._config.time_step
            effective_detach_seconds = feedback.group_detach_after_seconds * loyalty
            if agent.group_lonely_seconds >= effective_detach_seconds:
                switch_threshold = max(1, feedback.group_adoption_neighbor_threshold)
                switch_chance = min(1.0, feedback.group_switch_chance / max(0.1, loyalty))
                if (
                    switch_group != self._UNGROUPED
                    and switch_count >= switch_threshold
                    and self._rng.next_float() < switch_chance
                ):
                    self._set_group(agent, switch_group)
                else:
                    if (
                        can_form_groups
                        and self._rng.next_float()
                        < min(1.0, feedback.group_detach_new_group_chance * max(0.0, traits.founder))
                    ):
                        new_group = self._next_group_id
                        self._next_group_id += 1
                        self._register_group_base(new_group, agent.position)
                        self._set_group(agent, new_group)
                    else:
                        self._set_group(agent, self._UNGROUPED)
                agent.group_lonely_seconds = 0.0

        if can_form_groups:
            self._try_form_group(agent)
            if agent.group_id == original_group:
                self._try_adopt_group(
                    agent, majority_group, majority_count, same_group_neighbors, traits=traits
                )
        if agent.group_id == self._UNGROUPED and self._group_bases:
            seek_radius = self._config.feedback.group_seek_radius * 1.5
            seek_radius_sq = seek_radius * seek_radius
            nearest_group = self._UNGROUPED
            nearest_dist_sq = seek_radius_sq
            for gid, base in self._group_bases.items():
                offset = base - agent.position
                dist_sq = offset.length_squared()
                if dist_sq <= 1e-12 or dist_sq > seek_radius_sq:
                    continue
                if dist_sq < nearest_dist_sq:
                    nearest_group = gid
                    nearest_dist_sq = dist_sq
            if nearest_group != self._UNGROUPED and self._rng.next_float() < feedback.group_adoption_chance:
                self._set_group(agent, nearest_group)
        if agent.group_id == original_group:
            self._try_split_group(
                agent, same_group_neighbors, neighbors, neighbor_offsets, can_form_groups, traits=traits
            )
        return same_group_neighbors

    def _try_form_group(self, agent: Agent) -> None:
        if agent.group_id != self._UNGROUPED:
            return
        if len(self._ungrouped_neighbors) < self._config.feedback.group_formation_neighbor_threshold:
            return
        if self._rng.next_float() >= self._config.feedback.group_formation_chance:
            return

        new_group = self._next_group_id
        self._next_group_id += 1
        self._register_group_base(new_group, agent.position)
        self._set_group(agent, new_group)
        recruits = min(len(self._ungrouped_neighbors), self._config.feedback.group_formation_neighbor_threshold + 2)
        for neighbor in self._ungrouped_neighbors[:recruits]:
            self._set_group(neighbor, new_group)

    def _try_adopt_group(
        self,
        agent: Agent,
        majority_group: int,
        majority_count: int,
        same_group_neighbors: int,
        traits: AgentTraits | None = None,
    ) -> None:
        if majority_group == self._UNGROUPED or agent.group_id == majority_group:
            return
        if agent.group_cooldown > 0.0:
            return
        if agent.group_id != self._UNGROUPED and same_group_neighbors >= self._config.feedback.group_adoption_guard_min_allies:
            return
        target_size = self._group_sizes.get(majority_group, majority_count)
        size_for_threshold = target_size if target_size > 0 else majority_count
        effective_threshold = max(
            1,
            min(self._config.feedback.group_adoption_neighbor_threshold, max(1, size_for_threshold)),
        )
        if majority_count < effective_threshold:
            return
        base_chance = self._config.feedback.group_adoption_chance
        small_bonus = self._config.feedback.group_adoption_small_group_bonus
        size_for_bonus = max(1, target_size)
        traits = self._clamp_traits(agent.traits) if traits is None else traits
        sociality = max(0.0, traits.sociality)
        loyalty = max(0.1, traits.loyalty)
        adoption_chance = base_chance * (1.0 + small_bonus / size_for_bonus) * sociality
        if agent.group_id != self._UNGROUPED:
            adoption_chance *= 1.0 / loyalty
        adoption_chance = min(1.0, max(0.0, adoption_chance))
        if self._rng.next_float() < adoption_chance:
            self._set_group(agent, majority_group)

    def _try_split_group(
        self,
        agent: Agent,
        same_group_neighbors: int,
        neighbors: List[Agent],
        neighbor_offsets: List[Vector2],
        can_form_groups: bool,
        traits: AgentTraits | None = None,
    ) -> None:
        if agent.group_id == self._UNGROUPED:
            return
        traits = self._clamp_traits(agent.traits) if traits is None else traits
        if same_group_neighbors < self._config.feedback.group_split_neighbor_threshold:
            return
        effective_stress = agent.stress + same_group_neighbors * self._config.feedback.group_split_size_stress_weight
        if effective_stress < self._config.feedback.group_split_stress_threshold:
            return
        bonus_neighbors = max(0, same_group_neighbors - self._config.feedback.group_split_neighbor_threshold)
        size_bonus = bonus_neighbors * self._config.feedback.group_split_size_bonus_per_neighbor
        base_chance = self._config.feedback.group_split_chance
        split_chance = base_chance + size_bonus
        split_chance = min(self._config.feedback.group_split_chance_max, split_chance, 1.0)
        if split_chance <= 0.0:
            return
        if self._rng.next_float() < split_chance:
            previous_group = agent.group_id
            target_group = self._UNGROUPED
            if (
                can_form_groups
                and self._rng.next_float()
                < min(1.0, self._config.feedback.group_split_new_group_chance * max(0.0, traits.founder))
            ):
                target_group = self._next_group_id
                self._next_group_id += 1
                self._register_group_base(target_group, agent.position)
            self._set_group(agent, target_group)
            if target_group != self._UNGROUPED and can_form_groups:
                self._recruit_split_neighbors(previous_group, target_group, neighbors, neighbor_offsets)

    def _compute_desired_velocity(
        self,
        agent: Agent,
        neighbors: List[Agent],
        neighbor_offsets: List[Vector2],
        base_speed: float,
        return_sensed: bool = False,
        neighbor_dist_sq: List[float] | None = None,
        traits: AgentTraits | None = None,
        danger_present: bool | None = None,
        base_cell_key: tuple[int, int] | None = None,
    ) -> tuple[Vector2, bool] | Vector2:
        desired_x = 0.0
        desired_y = 0.0
        flee_vector = Vector2()
        sensed_danger = False
        traits = self._clamp_traits(agent.traits) if traits is None else traits
        species = self._config.species
        feedback = self._config.feedback
        environment = self._config.environment
        sociality = max(0.0, traits.sociality)
        territoriality = max(0.0, traits.territoriality)
        dist_sq_list = neighbor_dist_sq
        if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
            dist_sq_list = self._neighbor_dist_sq
            dist_sq_list.clear()
            for offset in neighbor_offsets:
                dist_sq_list.append(offset.x * offset.x + offset.y * offset.y)

        if danger_present is None:
            danger_present = self._environment.has_danger()
        if base_cell_key is None:
            base_cell_key = self._cell_key(agent.position)
        danger_level = 0.0
        danger_gradient = Vector2()
        if danger_present:
            danger_level = self._environment.sample_danger(base_cell_key)
            danger_gradient = self._danger_gradient(agent.position, base_cell_key)
        if danger_level > 0.1:
            sensed_danger = True
            if danger_gradient.length_squared() < 1e-4:
                danger_gradient = self._rng.next_unit_circle()
            if danger_gradient.length_squared() > 1e-12:
                danger_gradient.normalize_ip()
                flee_scale = base_speed * min(1.0, danger_level)
                flee_vector.x -= danger_gradient.x * flee_scale
                flee_vector.y -= danger_gradient.y * flee_scale

        for other, dist_sq, offset in zip(neighbors, dist_sq_list, neighbor_offsets):
            groups_differ = (
                agent.group_id != self._UNGROUPED
                and other.group_id != self._UNGROUPED
                and other.group_id != agent.group_id
            )
            if groups_differ and dist_sq < 4.0:
                if dist_sq > 1e-12:
                    inv_len = 1.0 / math.sqrt(dist_sq)
                    flee_vector.x -= offset.x * inv_len * base_speed
                    flee_vector.y -= offset.y * inv_len * base_speed
                    sensed_danger = True

        if flee_vector.length_squared() > 1e-3:
            agent.state = AgentState.FLEE
            return flee_vector, sensed_danger

        food_here = self._environment.sample_food(base_cell_key)
        food_gradient = Vector2()
        pheromone_gradient = (
            ZERO
            if agent.group_id == self._UNGROUPED
            else self._pheromone_gradient(agent.group_id, agent.position, base_cell_key)
        )
        grouped = agent.group_id != self._UNGROUPED
        if neighbors:
            personal_space_bias = (
                self._personal_space(neighbor_offsets, dist_sq_list)
                if feedback.personal_space_weight > 0.0 and feedback.personal_space_radius > 1e-6
                else ZERO
            )
            separation_bias = (
                self._separation(agent, neighbors, neighbor_offsets, dist_sq_list)
                if feedback.ally_separation_weight > 0.0
                or feedback.other_group_separation_weight > 0.0
                or feedback.min_separation_weight > 0.0
                else ZERO
            )
            intergroup_bias = (
                self._intergroup_avoidance(agent, neighbors, neighbor_offsets, dist_sq_list)
                if grouped
                and territoriality > 1e-6
                and feedback.other_group_avoid_weight > 0.0
                and feedback.other_group_avoid_radius > 1e-6
                else ZERO
            )
            group_cohesion_bias = (
                self._group_cohesion(agent, neighbors, neighbor_offsets, dist_sq_list)
                if grouped
                and sociality > 1e-6
                and feedback.group_cohesion_weight > 0.0
                and feedback.ally_cohesion_weight > 0.0
                and feedback.group_cohesion_radius > 1e-6
                else ZERO
            )
            alignment_bias = self._alignment(agent, neighbors) if grouped and sociality > 1e-6 else ZERO
        else:
            personal_space_bias = ZERO
            separation_bias = ZERO
            intergroup_bias = ZERO
            group_cohesion_bias = ZERO
            alignment_bias = ZERO
        group_seek_bias = (
            self._group_seek_bias(agent, neighbors, neighbor_offsets, dist_sq_list)
            if not grouped and feedback.group_seek_weight > 0.0 and feedback.group_seek_radius > 1e-6
            else ZERO
        )
        base_bias = (
            self._group_base_attraction(agent)
            if grouped and feedback.group_base_attraction_weight > 0.0
            else ZERO
        )

        food_bias = ZERO
        pheromone_bias_x = 0.0
        pheromone_bias_y = 0.0
        pheromone_len_sq = pheromone_gradient.length_squared()
        if pheromone_len_sq > 1e-4:
            inv_len = 1.0 / math.sqrt(pheromone_len_sq)
            pheromone_bias_x = pheromone_gradient.x * inv_len
            pheromone_bias_y = pheromone_gradient.y * inv_len
        danger_bias_x = 0.0
        danger_bias_y = 0.0
        danger_len_sq = danger_gradient.length_squared()
        if danger_len_sq > 1e-4:
            inv_len = 1.0 / math.sqrt(danger_len_sq)
            danger_bias_x = danger_gradient.x * inv_len
            danger_bias_y = danger_gradient.y * inv_len

        needs_food = agent.energy < species.reproduction_energy_threshold * 0.6 or food_here > environment.food_per_cell * 0.5
        if needs_food:
            food_gradient = self._food_gradient(agent.position, base_cell_key)
            if food_gradient.length_squared() > 1e-4:
                food_gradient.normalize_ip()
                food_bias = food_gradient
        if needs_food:
            agent.state = AgentState.SEEKING_FOOD
            food_scale = base_speed * 0.4
            desired_x += food_bias.x * food_scale
            desired_y += food_bias.y * food_scale
            wander = self._wander_direction(agent)
            wander_scale = base_speed * 0.25
            desired_x += wander.x * wander_scale
            desired_y += wander.y * wander_scale
        elif agent.energy > species.reproduction_energy_threshold and agent.age > species.adult_age:
            agent.state = AgentState.SEEKING_MATE
            cohesion_all = self._cohesion(neighbor_offsets)
            cohesion_scale = base_speed * 0.8
            desired_x += cohesion_all.x * cohesion_scale
            desired_y += cohesion_all.y * cohesion_scale
            pheromone_scale = base_speed * 0.25
            desired_x += pheromone_bias_x * pheromone_scale
            desired_y += pheromone_bias_y * pheromone_scale
        else:
            agent.state = AgentState.WANDER
            wander = self._wander_direction(agent)
            wander_scale = base_speed * species.wander_jitter
            desired_x += wander.x * wander_scale
            desired_y += wander.y * wander_scale
            pheromone_scale = base_speed * 0.15
            desired_x += pheromone_bias_x * pheromone_scale
            desired_y += pheromone_bias_y * pheromone_scale

        personal_scale = base_speed * feedback.personal_space_weight
        desired_x += personal_space_bias.x * personal_scale
        desired_y += personal_space_bias.y * personal_scale
        intergroup_scale = base_speed * feedback.other_group_avoid_weight * territoriality
        desired_x += intergroup_bias.x * intergroup_scale
        desired_y += intergroup_bias.y * intergroup_scale
        seek_scale = base_speed * feedback.group_seek_weight
        desired_x += group_seek_bias.x * seek_scale
        desired_y += group_seek_bias.y * seek_scale
        separation_scale = base_speed * 1.4
        desired_x += separation_bias.x * separation_scale
        desired_y += separation_bias.y * separation_scale
        alignment_scale = base_speed * 0.3 * sociality
        desired_x += alignment_bias.x * alignment_scale
        desired_y += alignment_bias.y * alignment_scale
        cohesion_scale = base_speed * feedback.group_cohesion_weight * feedback.ally_cohesion_weight * sociality
        desired_x += group_cohesion_bias.x * cohesion_scale
        desired_y += group_cohesion_bias.y * cohesion_scale
        base_scale = base_speed * feedback.group_base_attraction_weight
        desired_x += base_bias.x * base_scale
        desired_y += base_bias.y * base_scale
        boundary_bias, boundary_proximity = self._boundary_avoidance(agent.position)
        boundary_scale = base_speed * self._config.boundary_avoidance_weight
        desired_x += boundary_bias.x * boundary_scale
        desired_y += boundary_bias.y * boundary_scale
        boundary_len_sq = boundary_bias.x * boundary_bias.x + boundary_bias.y * boundary_bias.y
        desired_len_sq = desired_x * desired_x + desired_y * desired_y
        if boundary_proximity > 0.0 and boundary_len_sq > 1e-8 and desired_len_sq > 1e-8:
            turn = min(1.0, boundary_proximity * self._config.boundary_turn_weight)
            inward_x = boundary_bias.x * base_speed
            inward_y = boundary_bias.y * base_speed
            desired_x += (inward_x - desired_x) * turn
            desired_y += (inward_y - desired_y) * turn
        danger_scale = base_speed * 0.2
        desired_x -= danger_bias_x * danger_scale
        desired_y -= danger_bias_y * danger_scale
        desired = Vector2(desired_x, desired_y)
        if return_sensed:
            return desired, sensed_danger
        return desired

    def _separation(
        self,
        agent: Agent,
        neighbors: List[Agent],
        neighbor_vectors: List[Vector2],
        neighbor_dist_sq: List[float] | None = None,
    ) -> Vector2:
        if not neighbor_vectors:
            return ZERO
        feedback = self._config.feedback
        dist_sq_list = neighbor_dist_sq
        if dist_sq_list is None or len(dist_sq_list) != len(neighbor_vectors):
            dist_sq_list = [offset.length_squared() for offset in neighbor_vectors]
        accum_x = 0.0
        accum_y = 0.0
        closest_dist_sq = float("inf")
        min_sep = max(0.0, float(feedback.min_separation_distance))
        min_sep_sq = min_sep * min_sep
        min_sep_weight = max(0.0, float(feedback.min_separation_weight))
        ally_weight = float(feedback.ally_separation_weight)
        other_weight = float(feedback.other_group_separation_weight)
        for other, offset, raw_dist_sq in zip(neighbors, neighbor_vectors, dist_sq_list):
            if raw_dist_sq < closest_dist_sq:
                closest_dist_sq = raw_dist_sq
            dist_sq = max(raw_dist_sq, 0.1)
            same_group = agent.group_id != self._UNGROUPED and other.group_id == agent.group_id
            weight = ally_weight if same_group else other_weight
            inv_dist_sq = 1.0 / dist_sq
            accum_x -= offset.x * inv_dist_sq * weight
            accum_y -= offset.y * inv_dist_sq * weight
            if min_sep_weight > 0.0 and min_sep_sq > 1e-12 and raw_dist_sq > 1e-12 and raw_dist_sq < min_sep_sq:
                strength = (min_sep_sq - raw_dist_sq) / min_sep_sq
                strength = max(0.0, min(1.0, strength))
                dist = math.sqrt(raw_dist_sq)
                inv_len = 1.0 / dist
                scale = (strength * strength) * min_sep_weight
                accum_x -= offset.x * inv_len * scale
                accum_y -= offset.y * inv_len * scale
        if accum_x * accum_x + accum_y * accum_y < 1e-12:
            return ZERO
        if closest_dist_sq < float("inf") and closest_dist_sq > 1e-12 and min_sep > 1e-6:
            closest = math.sqrt(closest_dist_sq)
            if closest < min_sep:
                scale = min(4.0, max(1.0, min_sep / max(closest, 1e-4)))
                accum_x *= scale
                accum_y *= scale
        return _clamp_length_xy(accum_x, accum_y, 3.5)

    def _resolve_overlap(
        self, position: Vector2, neighbor_offsets: List[Vector2], neighbor_dist_sq: List[float] | None = None
    ) -> Vector2:
        min_sep = max(0.0, float(self._config.feedback.min_separation_distance))
        if min_sep <= 1e-6 or not neighbor_offsets:
            return position
        dist_sq_list = neighbor_dist_sq
        if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
            dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
        min_sep_sq = min_sep * min_sep
        correction_x = 0.0
        correction_y = 0.0
        count = 0
        for offset, dist_sq in zip(neighbor_offsets, dist_sq_list):
            if dist_sq <= 1e-12 or dist_sq >= min_sep_sq:
                continue
            dist = math.sqrt(dist_sq)
            overlap = min_sep - dist
            if overlap <= 0.0:
                continue
            inv_len = 1.0 / dist
            correction_x -= offset.x * inv_len * overlap
            correction_y -= offset.y * inv_len * overlap
            count += 1
        if count == 0:
            return position
        inv = 1.0 / count
        correction_x *= inv
        correction_y *= inv
        correction = _clamp_length_xy(correction_x, correction_y, min_sep * 0.5)
        return position + correction

    def _alignment(self, agent: Agent, neighbors: List[Agent]) -> Vector2:
        if agent.group_id == self._UNGROUPED:
            return ZERO
        sum_x = 0.0
        sum_y = 0.0
        count = 0
        for other in neighbors:
            if other.group_id != agent.group_id:
                continue
            velocity = other.velocity
            sum_x += velocity.x
            sum_y += velocity.y
            count += 1
        if count == 0:
            return ZERO
        inv = 1.0 / count
        return _safe_normalize_xy(sum_x * inv, sum_y * inv)

    def _group_seek_bias(
        self,
        agent: Agent,
        neighbors: List[Agent],
        neighbor_offsets: List[Vector2],
        neighbor_dist_sq: List[float] | None = None,
    ) -> Vector2:
        if agent.group_id != self._UNGROUPED:
            return ZERO
        feedback = self._config.feedback
        radius = max(0.0, float(feedback.group_seek_radius))
        if radius <= 1e-6:
            return ZERO
        radius_sq = radius * radius
        accum_x = 0.0
        accum_y = 0.0
        weight_sum = 0.0
        base_bias_x = 0.0
        base_bias_y = 0.0
        dist_sq_list = neighbor_dist_sq
        if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
            dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
        if self._group_bases:
            nearest_dx = 0.0
            nearest_dy = 0.0
            nearest_dist_sq = radius_sq
            for base in self._group_bases.values():
                dx = base.x - agent.position.x
                dy = base.y - agent.position.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= 1e-12 or dist_sq > radius_sq:
                    continue
                if dist_sq < nearest_dist_sq:
                    nearest_dx = dx
                    nearest_dy = dy
                    nearest_dist_sq = dist_sq
            if nearest_dist_sq < radius_sq:
                dist = math.sqrt(nearest_dist_sq)
                falloff = 1.0 - min(1.0, dist / radius)
                if falloff > 1e-6 and dist > 1e-12:
                    inv_len = 1.0 / dist
                    base_bias_x = nearest_dx * inv_len * falloff
                    base_bias_y = nearest_dy * inv_len * falloff
        for other, offset, dist_sq in zip(neighbors, neighbor_offsets, dist_sq_list):
            if other.group_id == self._UNGROUPED:
                continue
            if dist_sq <= 1e-12 or dist_sq > radius_sq:
                continue
            dist = math.sqrt(dist_sq)
            falloff = 1.0 - min(1.0, dist / radius)
            if falloff <= 1e-5:
                continue
            accum_x += offset.x * falloff
            accum_y += offset.y * falloff
            weight_sum += falloff
        if weight_sum <= 1e-6:
            return _safe_normalize_xy(base_bias_x, base_bias_y)
        inv = 1.0 / weight_sum
        blended_x = accum_x * inv
        blended_y = accum_y * inv
        if base_bias_x * base_bias_x + base_bias_y * base_bias_y > 1e-12:
            blended_x += base_bias_x
            blended_y += base_bias_y
        return _safe_normalize_xy(blended_x, blended_y)

    def _group_cohesion(
        self,
        agent: Agent,
        neighbors: List[Agent],
        neighbor_offsets: List[Vector2],
        neighbor_dist_sq: List[float] | None = None,
    ) -> Vector2:
        if agent.group_id == self._UNGROUPED:
            return ZERO
        feedback = self._config.feedback
        cohesion_radius_sq = feedback.group_cohesion_radius * feedback.group_cohesion_radius
        sum_x = 0.0
        sum_y = 0.0
        count = 0
        dist_sq_list = neighbor_dist_sq
        if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
            dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
        for other, offset, dist_sq in zip(neighbors, neighbor_offsets, dist_sq_list):
            if other.group_id != agent.group_id:
                continue
            if dist_sq > cohesion_radius_sq:
                continue
            sum_x += offset.x
            sum_y += offset.y
            count += 1
        if count == 0:
            return ZERO
        inv = 1.0 / count
        return _safe_normalize_xy(sum_x * inv, sum_y * inv)

    def _group_base_attraction(self, agent: Agent) -> Vector2:
        if agent.group_id == self._UNGROUPED:
            return ZERO
        base = self._group_bases.get(agent.group_id)
        if base is None:
            return ZERO
        feedback = self._config.feedback
        to_base = base - agent.position
        dist_sq = to_base.length_squared()
        if dist_sq <= 1e-12:
            return ZERO
        dead_zone = max(0.0, float(feedback.group_base_dead_zone))
        dead_sq = dead_zone * dead_zone
        if dist_sq <= dead_sq:
            return ZERO
        soft_radius = max(dead_zone, float(feedback.group_base_soft_radius))
        soft_sq = soft_radius * soft_radius
        strength = 1.0
        if soft_radius > dead_zone and dist_sq < soft_sq:
            denom = max(1e-12, soft_sq - dead_sq)
            t = (dist_sq - dead_sq) / denom
            t = max(0.0, min(1.0, t))
            strength = t * t
        if to_base.length_squared() < 1e-12:
            return ZERO
        to_base.normalize_ip()
        to_base *= strength
        return to_base

    def _personal_space(
        self, neighbor_offsets: List[Vector2], neighbor_dist_sq: List[float] | None = None
    ) -> Vector2:
        feedback = self._config.feedback
        radius = feedback.personal_space_radius
        if radius <= 1e-6 or not neighbor_offsets:
            return ZERO
        radius_sq = radius * radius
        dist_sq_list = neighbor_dist_sq
        if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
            dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
        accum_x = 0.0
        accum_y = 0.0
        count = 0
        for offset, dist_sq in zip(neighbor_offsets, dist_sq_list):
            if dist_sq <= 1e-9 or dist_sq > radius_sq:
                continue
            dist = math.sqrt(dist_sq)
            if dist <= 1e-12:
                continue
            strength = 1.0 - min(1.0, dist / radius)
            inv_len = 1.0 / dist
            accum_x -= offset.x * inv_len * strength
            accum_y -= offset.y * inv_len * strength
            count += 1
        if count == 0:
            return ZERO
        inv = 1.0 / count
        return _safe_normalize_xy(accum_x * inv, accum_y * inv)

    def _intergroup_avoidance(
        self,
        agent: Agent,
        neighbors: List[Agent],
        neighbor_offsets: List[Vector2],
        neighbor_dist_sq: List[float] | None = None,
    ) -> Vector2:
        feedback = self._config.feedback
        radius = feedback.other_group_avoid_radius
        if radius <= 1e-6:
            return ZERO
        radius_sq = radius * radius
        dist_sq_list = neighbor_dist_sq
        if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
            dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
        accum_x = 0.0
        accum_y = 0.0
        count = 0
        for other, offset, dist_sq in zip(neighbors, neighbor_offsets, dist_sq_list):
            if agent.group_id == self._UNGROUPED or other.group_id == self._UNGROUPED:
                continue
            if other.group_id == agent.group_id:
                continue
            if dist_sq <= 1e-9 or dist_sq > radius_sq:
                continue
            dist = math.sqrt(dist_sq)
            if dist <= 1e-12:
                continue
            falloff = 1.0 - min(1.0, dist / radius)
            if falloff <= 1e-5:
                continue
            inv_len = 1.0 / dist
            accum_x -= offset.x * inv_len * falloff
            accum_y -= offset.y * inv_len * falloff
            count += 1
        if count == 0:
            return ZERO
        inv = 1.0 / count
        return _safe_normalize_xy(accum_x * inv, accum_y * inv)

    def _wander_direction(self, agent: Agent) -> Vector2:
        refresh = max(1e-4, self._config.species.wander_refresh_seconds)
        if agent.wander_time <= 0.0 or agent.wander_dir.length_squared() < 1e-10:
            agent.wander_dir = self._rng.next_unit_circle()
            agent.wander_time = refresh
        else:
            agent.wander_time -= self._config.time_step
        return agent.wander_dir

    def _boundary_avoidance(self, position: Vector2) -> tuple[Vector2, float]:
        margin = self._config.boundary_margin
        size = self._config.world_size
        if margin <= 1e-6 or size <= 0.0:
            return ZERO, 0.0
        x = position.x
        y = position.y
        if margin <= x <= size - margin and margin <= y <= size - margin:
            return ZERO, 0.0

        push_x = 0.0
        push_y = 0.0
        if x < margin:
            push_x += 1.0 - (x / margin)
        elif x > size - margin:
            push_x -= 1.0 - ((size - x) / margin)
        if y < margin:
            push_y += 1.0 - (y / margin)
        elif y > size - margin:
            push_y -= 1.0 - ((size - y) / margin)

        proximity_x = 1.0 - min(x, size - x) / margin
        proximity_y = 1.0 - min(y, size - y) / margin
        if proximity_x < 0.0:
            proximity_x = 0.0
        if proximity_y < 0.0:
            proximity_y = 0.0
        proximity = min(1.0, max(proximity_x, proximity_y))

        push_len_sq = push_x * push_x + push_y * push_y
        if push_len_sq < 1e-8 or proximity <= 0.0:
            return ZERO, 0.0

        strength = proximity * (0.4 + 0.6 * proximity)
        inv_len = 1.0 / math.sqrt(push_len_sq)
        return Vector2(push_x * inv_len * strength, push_y * inv_len * strength), proximity

    @staticmethod
    def _cohesion(neighbor_vectors: List[Vector2]) -> Vector2:
        if not neighbor_vectors:
            return ZERO
        sum_x = 0.0
        sum_y = 0.0
        for offset in neighbor_vectors:
            sum_x += offset.x
            sum_y += offset.y
        inv = 1.0 / len(neighbor_vectors)
        return _safe_normalize_xy(sum_x * inv, sum_y * inv)

    def _clamp_position(self, position: Vector2) -> Vector2:
        size = self._config.world_size
        return Vector2(
            max(0.0, min(size, position.x)),
            max(0.0, min(size, position.y)),
        )

    def _cell_key(self, position: Vector2) -> tuple[int, int]:
        return self._environment._cell_key(position)

    def _orthogonal_neighbor_keys(
        self, position: Vector2, base_key: tuple[int, int] | None = None
    ) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
        if base_key is None:
            base_key = self._environment._cell_key(position)
        add_key = self._environment._add_key2
        right = add_key(base_key, 1, 0)
        left = add_key(base_key, -1, 0)
        up = add_key(base_key, 0, 1)
        down = add_key(base_key, 0, -1)
        return (right, left, up, down)

    def _food_gradient(self, position: Vector2, base_key: tuple[int, int] | None = None) -> Vector2:
        right_key, left_key, up_key, down_key = self._orthogonal_neighbor_keys(position, base_key)
        right = self._environment.peek_food(right_key)
        left = self._environment.peek_food(left_key)
        up = self._environment.peek_food(up_key)
        down = self._environment.peek_food(down_key)
        return Vector2(right - left, up - down)

    def _pheromone_gradient(
        self, group_id: int, position: Vector2, base_key: tuple[int, int] | None = None
    ) -> Vector2:
        right_key, left_key, up_key, down_key = self._orthogonal_neighbor_keys(position, base_key)
        right = self._environment.sample_pheromone(right_key, group_id)
        left = self._environment.sample_pheromone(left_key, group_id)
        up = self._environment.sample_pheromone(up_key, group_id)
        down = self._environment.sample_pheromone(down_key, group_id)
        return Vector2(right - left, up - down)

    def _danger_gradient(self, position: Vector2, base_key: tuple[int, int] | None = None) -> Vector2:
        right_key, left_key, up_key, down_key = self._orthogonal_neighbor_keys(position, base_key)
        right = self._environment.sample_danger(right_key)
        left = self._environment.sample_danger(left_key)
        up = self._environment.sample_danger(up_key)
        down = self._environment.sample_danger(down_key)
        return Vector2(right - left, up - down)

    def _tick_environment(self, active_groups: Set[int]) -> None:
        env_dt = self._config.environment_tick_interval if self._config.environment_tick_interval > 1e-6 else self._config.time_step
        self._environment_accumulator += self._config.time_step
        while self._environment_accumulator >= env_dt:
            self._environment.prune_pheromones(active_groups)
            self._environment.set_food_regen_multiplier(self._update_food_regen_noise(env_dt))
            self._environment.tick(env_dt)
            self._environment_accumulator -= env_dt

    def _update_food_regen_noise(self, env_dt: float) -> float:
        config = self._config.environment
        amplitude = max(0.0, float(config.food_regen_noise_amplitude))
        interval = float(config.food_regen_noise_interval_seconds)
        smooth = max(0.0, float(config.food_regen_noise_smooth_seconds))

        if amplitude <= 1e-9 or interval <= 1e-6:
            self._food_regen_noise_multiplier = 1.0
            self._food_regen_noise_target = 1.0
            self._food_regen_noise_time_to_next_sample = 0.0
            return self._food_regen_noise_multiplier

        low = max(0.0, 1.0 - amplitude)
        high = 1.0 + amplitude

        if self._food_regen_noise_time_to_next_sample <= 0.0:
            self._food_regen_noise_time_to_next_sample = interval

        self._food_regen_noise_time_to_next_sample -= env_dt
        while self._food_regen_noise_time_to_next_sample <= 0.0:
            self._food_regen_noise_target = self._climate_rng.next_range(low, high)
            self._food_regen_noise_time_to_next_sample += interval
            if smooth <= 1e-6:
                self._food_regen_noise_multiplier = self._food_regen_noise_target

        if smooth > 1e-6:
            alpha = 1.0 - math.exp(-env_dt / smooth)
            self._food_regen_noise_multiplier += (self._food_regen_noise_target - self._food_regen_noise_multiplier) * alpha

        self._food_regen_noise_multiplier = max(low, min(high, self._food_regen_noise_multiplier))
        return self._food_regen_noise_multiplier

    def _apply_life_cycle(
        self,
        agent: Agent,
        neighbor_count: int,
        same_group_neighbors: int,
        can_create_groups: bool,
        population: int | None = None,
        sim_time: float = 0.0,
        traits: AgentTraits | None = None,
    ) -> int:
        dt = self._config.time_step
        births_added = 0
        if population is None:
            population = len(self._agents)
        traits = self._clamp_traits(agent.traits) if traits is None else traits
        base_cell_key = self._cell_key(agent.position)
        pending_food = self._pending_food
        pending_pheromone = self._pending_pheromone
        metabolism_multiplier = self._trait_metabolism_multiplier(traits)
        speed_cost = agent.velocity.length() * 0.05 * metabolism_multiplier
        metabolism = (self._config.species.metabolism_per_second * metabolism_multiplier + speed_cost) * dt
        excess_energy = max(0.0, agent.energy - self._config.species.energy_soft_cap)
        metabolism += excess_energy * self._config.species.high_energy_metabolism_slope * dt * metabolism_multiplier
        stress_drain = neighbor_count * self._config.feedback.stress_drain_per_neighbor * dt
        agent.energy -= metabolism + stress_drain + agent.stress * dt

        if neighbor_count > self._config.feedback.local_density_soft_cap:
            agent.stress += 0.1 * dt
            disease_resistance = self._trait_disease_resistance(traits)
            disease_risk = neighbor_count * self._config.feedback.disease_probability_per_neighbor * dt
            disease_risk = disease_risk / max(0.1, disease_resistance)
            if self._rng.next_float() < disease_risk:
                agent.alive = False
                pending_food[base_cell_key] = (
                    pending_food.get(base_cell_key, 0.0)
                    + self._config.environment.food_from_death
                )
                return births_added
        else:
            agent.stress = max(0.0, agent.stress - 0.05 * dt)

        max_consumption = self._config.environment.food_consumption_rate * dt
        gained_energy = 0.0
        remaining = max_consumption
        if remaining > 0.0:
            available = self._environment.sample_food(base_cell_key)
            if available > 0:
                consumed = min(available, remaining)
                self._environment.consume_food(base_cell_key, consumed)
                gained_energy += consumed
        agent.energy += gained_energy

        allow_reproduction = self._config.initial_population >= 10
        if (
            allow_reproduction
            and agent.energy > self._config.species.reproduction_energy_threshold
            and agent.age > self._config.species.adult_age
            and len(self._agents) + len(self._birth_queue) < self._config.max_population
        ):
            density_factor = 1.0
            if neighbor_count > self._config.feedback.local_density_soft_cap:
                excess = neighbor_count - self._config.feedback.local_density_soft_cap
                drop = excess * self._config.feedback.density_reproduction_slope
                density_factor = max(0.0, min(1.0, self._config.feedback.density_reproduction_penalty - drop))
            group_factor = 1.0
            if agent.group_id != self._UNGROUPED:
                penalty = same_group_neighbors * self._config.feedback.group_reproduction_penalty_per_ally
                group_factor = max(
                    self._config.feedback.group_reproduction_min_factor,
                    1.0 - penalty,
                )
            trait_factor = self._trait_reproduction_factor(traits)
            base_reproduction = max(0.0, float(self._config.feedback.reproduction_base_chance))
            reproduction_chance = max(0.0, min(1.0, base_reproduction * density_factor * group_factor * trait_factor))
            if self._rng.next_float() < reproduction_chance:
                child_energy = agent.energy * 0.5
                agent.energy -= child_energy + self._config.species.birth_energy_cost
                child_group = self._mutate_group(agent.group_id, can_create_groups, agent.position, traits)
                if agent.group_id == self._UNGROUPED and child_group != self._UNGROUPED:
                    self._set_group(agent, child_group)
                child_cooldown = (
                    self._config.feedback.group_merge_cooldown_seconds
                    if child_group != self._UNGROUPED and self._config.feedback.group_merge_cooldown_seconds > 0.0
                    else 0.0
                )
                spawn_distance = max(0.5, float(self._config.feedback.min_separation_distance))
                child_lineage = agent.lineage_id
                child_traits = self._copy_traits(traits)
                if self._config.evolution.enabled:
                    if (
                        self._config.evolution.lineage_mutation_chance > 0.0
                        and self._rng.next_float() < self._config.evolution.lineage_mutation_chance
                    ):
                        child_lineage = self._allocate_lineage_id()
                    child_traits = self._mutate_traits(traits)
                child_velocity = _clamp_length(agent.velocity, self._trait_speed_limit(child_traits))
                child = Agent(
                    id=self._next_id,
                    generation=agent.generation + 1,
                    group_id=child_group,
                    position=agent.position + self._rng.next_unit_circle() * spawn_distance,
                    velocity=child_velocity,
                    heading=self._heading_from_velocity(child_velocity),
                    energy=child_energy,
                    age=0.0,
                    state=AgentState.WANDER,
                    lineage_id=child_lineage,
                    traits=child_traits,
                    traits_dirty=False,
                    group_cooldown=child_cooldown,
                    last_desired=child_velocity.copy(),
                )
                self._next_id += 1
                self._birth_queue.append(child)
                births_added += 1
                if child_group != self._UNGROUPED:
                    pheromone_key = (base_cell_key, child_group)
                    pending_pheromone[pheromone_key] = (
                        pending_pheromone.get(pheromone_key, 0.0)
                        + self._config.environment.pheromone_deposit_on_birth
                    )

        hazard_per_second = (
            self._config.feedback.base_death_probability_per_second
            + agent.age * self._config.feedback.age_death_probability_per_second
            + neighbor_count * self._config.feedback.density_death_probability_per_neighbor_per_second
        )
        hazard_chance = min(1.0, hazard_per_second * dt)
        if hazard_chance > 0.0 and self._rng.next_float() < hazard_chance:
            agent.alive = False
            pending_food[base_cell_key] = (
                pending_food.get(base_cell_key, 0.0)
                + self._config.environment.food_from_death
            )
            return births_added

        if agent.energy <= 0 or agent.age >= self._config.species.max_age:
            agent.alive = False
            pending_food[base_cell_key] = (
                pending_food.get(base_cell_key, 0.0)
                + self._config.environment.food_from_death
            )
        return births_added

    def _mutate_group(self, group_id: int, can_create_groups: bool, position: Vector2, traits: AgentTraits) -> int:
        if not can_create_groups:
            return group_id
        founder = max(0.0, self._clamp_traits(traits).founder)
        if group_id == self._UNGROUPED:
            if self._rng.next_float() < min(1.0, self._config.feedback.group_birth_seed_chance * founder):
                new_group = self._next_group_id
                self._next_group_id += 1
                self._register_group_base(new_group, position)
                return new_group
            return self._UNGROUPED
        if self._rng.next_float() < min(1.0, self._config.feedback.group_mutation_chance * founder):
            new_group = self._next_group_id
            self._next_group_id += 1
            self._register_group_base(new_group, position)
            return new_group
        return group_id

    def _apply_field_events(self) -> None:
        for cell_key, amt in self._pending_food.items():
            self._environment.add_food(cell_key, amt)
        for cell_key, amt in self._pending_danger.items():
            self._environment.add_danger(cell_key, amt)
        for (cell_key, gid), amt in self._pending_pheromone.items():
            self._environment.add_pheromone(cell_key, gid, amt)
        self._pending_food.clear()
        self._pending_danger.clear()
        self._pending_pheromone.clear()

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

    def _create_metrics(
        self,
        tick: int,
        births: int,
        deaths: int,
        neighbor_checks: int,
        duration_ms: float,
        stats: tuple[int, float, float, int, int],
    ) -> TickMetrics:
        population, avg_energy, avg_age, groups, ungrouped = stats
        return TickMetrics(
            tick=tick,
            population=population,
            births=births,
            deaths=deaths,
            average_energy=avg_energy,
            average_age=avg_age,
            groups=groups,
            neighbor_checks=neighbor_checks,
            ungrouped=ungrouped,
            tick_duration_ms=duration_ms,
        )

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
