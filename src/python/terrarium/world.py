from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from pygame.math import Vector2

from .agent import Agent, AgentState
from .config import SimulationConfig
from .environment import EnvironmentGrid
from .rng import DeterministicRng
from .spatial_grid import GridEntry, SpatialGrid

ZERO = Vector2()


def _safe_normalize(vector: Vector2) -> Vector2:
    if vector.length_squared() < 1e-10:
        return Vector2()
    return vector.normalize()


def _clamp_length(vector: Vector2, max_length: float) -> Vector2:
    if max_length <= 0:
        return Vector2()
    magnitude_sq = vector.length_squared()
    if magnitude_sq <= max_length * max_length:
        return vector
    if magnitude_sq == 0:
        return Vector2()
    return vector.normalize() * max_length


@dataclass
class TickMetrics:
    tick: int
    population: int
    births: int
    deaths: int
    average_energy: float
    average_age: float
    groups: int
    neighbor_checks: int
    tick_duration_ms: float = 0.0


@dataclass
class Snapshot:
    tick: int
    metrics: TickMetrics
    agents: List[Dict[str, float]]


class World:
    _UNGROUPED = -1

    def __init__(self, config: SimulationConfig):
        self._config = config
        self._rng = DeterministicRng(config.seed)
        self._grid = SpatialGrid(config.cell_size)
        self._environment = EnvironmentGrid(config.cell_size, config.environment)
        self._agents: List[Agent] = []
        self._birth_queue: List[Agent] = []
        self._id_to_index: Dict[int, int] = {}
        self._neighbor_offsets: List[Vector2] = []
        self._neighbor_agents: List[Agent] = []
        self._group_scratch: Set[int] = set()
        self._pending_food: List[tuple[Vector2, float]] = []
        self._pending_danger: List[tuple[Vector2, float]] = []
        self._pending_pheromone: List[tuple[Vector2, int, float]] = []
        self._ungrouped_neighbors: List[Agent] = []
        self._group_counts_scratch: Dict[int, int] = {}
        self._next_id = 0
        self._next_group_id = 0
        self._metrics: List[TickMetrics] = []
        self._bootstrap_population()

    @property
    def agents(self) -> List[Agent]:
        return self._agents

    @property
    def metrics(self) -> List[TickMetrics]:
        return self._metrics

    def reset(self) -> None:
        self._agents.clear()
        self._birth_queue.clear()
        self._environment.reset()
        self._grid.clear()
        self._neighbor_offsets.clear()
        self._neighbor_agents.clear()
        self._group_scratch.clear()
        self._pending_food.clear()
        self._pending_danger.clear()
        self._pending_pheromone.clear()
        self._rng.reset()
        self._id_to_index.clear()
        self._metrics.clear()
        self._next_id = 0
        self._next_group_id = 0
        self._bootstrap_population()

    def step(self, tick: int) -> TickMetrics:
        from time import perf_counter

        start = perf_counter()
        self._pending_food.clear()
        self._pending_danger.clear()
        self._pending_pheromone.clear()

        sim_time = tick * self._config.time_step
        can_form_groups = sim_time >= self._config.feedback.group_formation_warmup_seconds

        self._refresh_index_map()
        self._grid.clear()
        for agent in self._agents:
            self._grid.insert(agent.id, agent.position)

        neighbor_checks = 0
        births = 0
        deaths = 0

        for i, agent in enumerate(list(self._agents)):
            if not agent.alive:
                continue

            neighbors = self._grid.get_neighbors(agent.position, self._config.species.vision_radius)
            self._collect_neighbor_data(agent, neighbors)
            neighbor_checks += len(self._neighbor_agents)

            self._update_group_membership(agent, self._neighbor_agents, can_form_groups)
            desired, sensed_danger = self._compute_desired_velocity(agent, self._neighbor_agents, self._neighbor_offsets)
            accel = desired - agent.velocity
            accel = _clamp_length(accel, self._config.species.max_acceleration)
            agent.velocity = _clamp_length(
                agent.velocity + accel * self._config.time_step,
                self._config.species.base_speed,
            )
            agent.position = self._wrap(agent.position + agent.velocity * self._config.time_step, self._config.world_size)
            agent.age += self._config.time_step

            births += self._apply_life_cycle(agent, len(self._neighbor_agents), can_form_groups)
            if agent.state == AgentState.FLEE or sensed_danger:
                self._pending_danger.append((agent.position, self._config.environment.danger_pulse_on_flee))

        self._apply_field_events()
        self._environment.tick(self._config.time_step)
        self._apply_births()
        deaths += self._remove_dead()

        elapsed_ms = (perf_counter() - start) * 1000.0
        metrics = self._create_metrics(tick, births, deaths, neighbor_checks, elapsed_ms)
        self._metrics.append(metrics)
        return metrics

    def snapshot(self, tick: int) -> Snapshot:
        metrics = self._metrics[-1] if self._metrics else TickMetrics(tick, len(self._agents), 0, 0, 0.0, 0.0, 0, 0)
        agents_payload = [
            {
                "id": agent.id,
                "x": agent.position.x,
                "y": agent.position.y,
                "group": agent.group_id,
                "energy": agent.energy,
                "state": agent.state.value,
            }
            for agent in self._agents
            if agent.alive
        ]
        return Snapshot(tick=tick, metrics=metrics, agents=agents_payload)

    def _bootstrap_population(self) -> None:
        for _ in range(self._config.initial_population):
            pos = Vector2(
                self._rng.next_range(0.0, self._config.world_size),
                self._rng.next_range(0.0, self._config.world_size),
            )
            agent = Agent(
                id=self._next_id,
                generation=0,
                group_id=self._UNGROUPED,
                position=pos,
                velocity=self._rng.next_unit_circle() * (self._config.species.base_speed * 0.3),
                energy=self._config.species.reproduction_energy_threshold * self._config.species.initial_energy_fraction_of_threshold,
                age=self._sample_initial_age(),
                state=AgentState.WANDER,
            )
            self._agents.append(agent)
            self._id_to_index[self._next_id] = len(self._agents) - 1
            self._next_id += 1

    def _sample_initial_age(self) -> float:
        min_age = max(0.0, self._config.species.initial_age_min)
        default_max = min(self._config.species.adult_age, self._config.species.max_age * 0.5)
        max_age = self._config.species.initial_age_max if self._config.species.initial_age_max > 0 else default_max
        max_age = max(0.0, min(max_age, self._config.species.max_age))
        if max_age < min_age:
            min_age, max_age = max_age, min_age
        return self._rng.next_range(min_age, max_age)

    def _collect_neighbor_data(self, agent: Agent, neighbors: List[GridEntry]) -> None:
        self._neighbor_offsets.clear()
        self._neighbor_agents.clear()
        for entry in neighbors:
            if entry.id == agent.id:
                continue
            other = self._try_get_agent(entry.id)
            if other is None or not other.alive:
                continue
            self._neighbor_offsets.append(entry.position - agent.position)
            self._neighbor_agents.append(other)

    def _update_group_membership(self, agent: Agent, neighbors: List[Agent], can_form_groups: bool) -> None:
        original_group = agent.group_id
        self._group_counts_scratch.clear()
        self._ungrouped_neighbors.clear()
        same_group_neighbors = 0

        for other in neighbors:
            if other.group_id == self._UNGROUPED:
                self._ungrouped_neighbors.append(other)
            if agent.group_id != self._UNGROUPED and other.group_id == agent.group_id:
                same_group_neighbors += 1
            if other.group_id >= 0:
                self._group_counts_scratch[other.group_id] = self._group_counts_scratch.get(other.group_id, 0) + 1

        majority_group = self._UNGROUPED
        majority_count = 0
        for gid, count in self._group_counts_scratch.items():
            if count > majority_count:
                majority_group = gid
                majority_count = count

        if can_form_groups:
            self._try_form_group(agent)
            if agent.group_id == original_group:
                self._try_adopt_group(agent, majority_group, majority_count)
        self._try_split_group(agent, same_group_neighbors, can_form_groups)
        self._group_counts_scratch.clear()
        self._ungrouped_neighbors.clear()

    def _try_form_group(self, agent: Agent) -> None:
        if agent.group_id != self._UNGROUPED:
            return
        if len(self._ungrouped_neighbors) < self._config.feedback.group_formation_neighbor_threshold:
            return
        if self._rng.next_float() >= self._config.feedback.group_formation_chance:
            return

        new_group = self._next_group_id
        self._next_group_id += 1
        self._adopt_group(agent, new_group)
        recruits = min(len(self._ungrouped_neighbors), self._config.feedback.group_formation_neighbor_threshold + 2)
        for neighbor in self._ungrouped_neighbors[:recruits]:
            self._adopt_group(neighbor, new_group)

    def _try_adopt_group(self, agent: Agent, majority_group: int, majority_count: int) -> None:
        if majority_group == self._UNGROUPED or agent.group_id == majority_group:
            return
        if majority_count < self._config.feedback.group_adoption_neighbor_threshold:
            return
        if self._rng.next_float() < self._config.feedback.group_adoption_chance:
            agent.group_id = majority_group

    def _try_split_group(self, agent: Agent, same_group_neighbors: int, can_form_groups: bool) -> None:
        if agent.group_id == self._UNGROUPED:
            return
        if same_group_neighbors < self._config.feedback.group_split_neighbor_threshold:
            return
        if agent.stress < self._config.feedback.group_split_stress_threshold:
            return
        if self._rng.next_float() < self._config.feedback.group_split_chance:
            if can_form_groups and self._rng.next_float() < self._config.feedback.group_split_new_group_chance:
                agent.group_id = self._next_group_id
                self._next_group_id += 1
            else:
                agent.group_id = self._UNGROUPED

    @staticmethod
    def _adopt_group(agent: Agent, group_id: int) -> None:
        agent.group_id = group_id

    def _compute_desired_velocity(self, agent: Agent, neighbors: List[Agent], neighbor_offsets: List[Vector2]) -> tuple[Vector2, bool]:
        desired = ZERO
        flee_vector = ZERO
        sensed_danger = False

        danger_level = self._environment.sample_danger(agent.position)
        if danger_level > 0.1:
            sensed_danger = True
            danger_gradient = self._danger_gradient(agent.position)
            if danger_gradient.length_squared() < 1e-4:
                danger_gradient = self._rng.next_unit_circle()
            flee_vector = flee_vector - _safe_normalize(danger_gradient) * (
                self._config.species.base_speed * min(1.0, danger_level)
            )

        for other, offset in zip(neighbors, neighbor_offsets):
            groups_differ = agent.group_id != self._UNGROUPED and other.group_id != self._UNGROUPED and other.group_id != agent.group_id
            if groups_differ and offset.length_squared() < 4.0:
                flee_vector = flee_vector - _safe_normalize(offset) * self._config.species.base_speed
                sensed_danger = True

        if flee_vector.length_squared() > 1e-3:
            agent.state = AgentState.FLEE
            return flee_vector, sensed_danger

        food_here = self._environment.sample_food(agent.position)
        food_gradient = self._food_gradient(agent.position)
        pheromone_gradient = ZERO if agent.group_id == self._UNGROUPED else self._pheromone_gradient(agent.group_id, agent.position)
        danger_gradient_away = self._danger_gradient(agent.position)

        food_bias = _safe_normalize(food_gradient) if food_gradient.length_squared() > 1e-4 else ZERO
        pheromone_bias = _safe_normalize(pheromone_gradient) if pheromone_gradient.length_squared() > 1e-4 else ZERO
        danger_bias = _safe_normalize(danger_gradient_away) if danger_gradient_away.length_squared() > 1e-4 else ZERO

        if agent.energy < self._config.species.reproduction_energy_threshold * 0.6 or food_here > self._config.environment.food_per_cell * 0.5 or food_gradient.length_squared() > 0.01:
            agent.state = AgentState.SEEKING_FOOD
            desired = desired + food_bias * (self._config.species.base_speed * 0.4)
            desired = desired + self._rng.next_unit_circle() * (self._config.species.base_speed * 0.25)
        elif agent.energy > self._config.species.reproduction_energy_threshold and agent.age > self._config.species.adult_age:
            agent.state = AgentState.SEEKING_MATE
            desired = desired + self._cohesion(neighbor_offsets) * (self._config.species.base_speed * 0.8)
            desired = desired + pheromone_bias * (self._config.species.base_speed * 0.25)
        else:
            agent.state = AgentState.WANDER
            desired = desired + self._rng.next_unit_circle() * (self._config.species.base_speed * self._config.species.wander_jitter)
            desired = desired + pheromone_bias * (self._config.species.base_speed * 0.15)

        desired = desired + self._separation(neighbor_offsets) * (self._config.species.base_speed * 1.2)
        desired = desired + self._alignment(agent, neighbors) * (self._config.species.base_speed * 0.3)
        desired = desired - danger_bias * (self._config.species.base_speed * 0.2)
        return desired, sensed_danger

    @staticmethod
    def _separation(neighbor_vectors: List[Vector2]) -> Vector2:
        if not neighbor_vectors:
            return ZERO
        accum = ZERO
        for offset in neighbor_vectors:
            dist_sq = max(offset.length_squared(), 0.1)
            accum = accum - (offset / dist_sq)
        return _safe_normalize(accum)

    def _alignment(self, agent: Agent, neighbors: List[Agent]) -> Vector2:
        if agent.group_id == self._UNGROUPED:
            return ZERO
        accum = ZERO
        count = 0
        for other in neighbors:
            if other.group_id != agent.group_id:
                continue
            accum = accum + other.velocity
            count += 1
        if count == 0:
            return ZERO
        return _safe_normalize(accum / count)

    @staticmethod
    def _cohesion(neighbor_vectors: List[Vector2]) -> Vector2:
        if not neighbor_vectors:
            return ZERO
        center = ZERO
        for offset in neighbor_vectors:
            center = center + offset
        center = center / len(neighbor_vectors)
        return _safe_normalize(center)

    def _food_gradient(self, position: Vector2) -> Vector2:
        step = self._config.cell_size
        right = self._environment.peek_food(position + Vector2(step, 0))
        left = self._environment.peek_food(position + Vector2(-step, 0))
        up = self._environment.peek_food(position + Vector2(0, step))
        down = self._environment.peek_food(position + Vector2(0, -step))
        return Vector2(right - left, up - down)

    def _pheromone_gradient(self, group_id: int, position: Vector2) -> Vector2:
        step = self._config.cell_size
        right = self._environment.sample_pheromone(position + Vector2(step, 0), group_id)
        left = self._environment.sample_pheromone(position + Vector2(-step, 0), group_id)
        up = self._environment.sample_pheromone(position + Vector2(0, step), group_id)
        down = self._environment.sample_pheromone(position + Vector2(0, -step), group_id)
        return Vector2(right - left, up - down)

    def _danger_gradient(self, position: Vector2) -> Vector2:
        step = self._config.cell_size
        right = self._environment.sample_danger(position + Vector2(step, 0))
        left = self._environment.sample_danger(position + Vector2(-step, 0))
        up = self._environment.sample_danger(position + Vector2(0, step))
        down = self._environment.sample_danger(position + Vector2(0, -step))
        return Vector2(right - left, up - down)

    def _apply_life_cycle(self, agent: Agent, neighbor_count: int, can_create_groups: bool) -> int:
        dt = self._config.time_step
        births_added = 0
        speed_cost = agent.velocity.length() * 0.05
        metabolism = self._config.species.metabolism_per_second * dt + speed_cost * dt
        excess_energy = max(0.0, agent.energy - self._config.species.energy_soft_cap)
        metabolism += excess_energy * self._config.species.high_energy_metabolism_slope * dt
        stress_drain = neighbor_count * self._config.feedback.stress_drain_per_neighbor * dt
        agent.energy -= metabolism + stress_drain + agent.stress * dt

        if neighbor_count > self._config.feedback.local_density_soft_cap:
            agent.stress += 0.1 * dt
            if self._rng.next_float() < neighbor_count * self._config.feedback.disease_probability_per_neighbor * dt:
                agent.alive = False
                self._pending_food.append((agent.position, self._config.environment.food_from_death))
                return births_added
        else:
            agent.stress = max(0.0, agent.stress - 0.05 * dt)

        available = self._environment.sample_food(agent.position)
        if available > 0:
            consumed = min(available, self._config.environment.food_consumption_rate * dt)
            self._environment.consume_food(agent.position, consumed)
            agent.energy += consumed

        if (
            agent.energy > self._config.species.reproduction_energy_threshold
            and agent.age > self._config.species.adult_age
            and len(self._agents) + len(self._birth_queue) < self._config.max_population
        ):
            density_factor = 1.0
            if neighbor_count > self._config.feedback.local_density_soft_cap:
                excess = neighbor_count - self._config.feedback.local_density_soft_cap
                drop = excess * self._config.feedback.density_reproduction_slope
                density_factor = max(0.0, min(1.0, self._config.feedback.density_reproduction_penalty - drop))
            reproduction_chance = max(0.0, min(1.0, 0.25 * density_factor))
            if self._rng.next_float() < reproduction_chance:
                child_energy = agent.energy * 0.5
                agent.energy -= child_energy + self._config.species.birth_energy_cost
                child_group = self._mutate_group(agent.group_id, can_create_groups)
                if agent.group_id == self._UNGROUPED and child_group != self._UNGROUPED:
                    agent.group_id = child_group
                child = Agent(
                    id=self._next_id,
                    generation=agent.generation + 1,
                    group_id=child_group,
                    position=agent.position + self._rng.next_unit_circle() * 0.5,
                    velocity=agent.velocity,
                    energy=child_energy,
                    age=0.0,
                    state=AgentState.WANDER,
                )
                self._next_id += 1
                self._birth_queue.append(child)
                births_added += 1
                if child_group != self._UNGROUPED:
                    self._pending_pheromone.append((agent.position, child_group, self._config.environment.pheromone_deposit_on_birth))

        hazard_per_second = (
            self._config.feedback.base_death_probability_per_second
            + agent.age * self._config.feedback.age_death_probability_per_second
            + neighbor_count * self._config.feedback.density_death_probability_per_neighbor_per_second
        )
        hazard_chance = min(1.0, hazard_per_second * dt)
        if hazard_chance > 0.0 and self._rng.next_float() < hazard_chance:
            agent.alive = False
            self._pending_food.append((agent.position, self._config.environment.food_from_death))
            return births_added

        if agent.energy <= 0 or agent.age >= self._config.species.max_age:
            agent.alive = False
            self._pending_food.append((agent.position, self._config.environment.food_from_death))
        return births_added
    def _mutate_group(self, group_id: int, can_create_groups: bool) -> int:
        if not can_create_groups:
            return group_id
        if group_id == self._UNGROUPED:
            if self._rng.next_float() < self._config.feedback.group_birth_seed_chance:
                new_group = self._next_group_id
                self._next_group_id += 1
                return new_group
            return self._UNGROUPED
        if self._rng.next_float() < self._config.feedback.group_mutation_chance:
            delta = self._rng.next_int(3) - 1
            return abs(group_id + delta) % 8
        return group_id

    def _apply_field_events(self) -> None:
        for pos, amt in self._pending_food:
            self._environment.add_food(pos, amt)
        for pos, amt in self._pending_danger:
            self._environment.add_danger(pos, amt)
        for pos, gid, amt in self._pending_pheromone:
            self._environment.add_pheromone(pos, gid, amt)
        self._pending_food.clear()
        self._pending_danger.clear()
        self._pending_pheromone.clear()

    def _apply_births(self) -> None:
        for agent in self._birth_queue:
            self._agents.append(agent)
            self._id_to_index[agent.id] = len(self._agents) - 1
        self._birth_queue.clear()

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
    def _wrap(position: Vector2, world_size: float) -> Vector2:
        x, y = position.x, position.y
        if x < 0:
            x += world_size
        if x > world_size:
            x -= world_size
        if y < 0:
            y += world_size
        if y > world_size:
            y -= world_size
        return Vector2(x, y)

    def _create_metrics(self, tick: int, births: int, deaths: int, neighbor_checks: int, duration_ms: float) -> TickMetrics:
        population = len(self._agents)
        energy_sum = sum(agent.energy for agent in self._agents)
        age_sum = sum(agent.age for agent in self._agents)
        self._group_scratch.clear()
        for agent in self._agents:
            if agent.group_id != self._UNGROUPED:
                self._group_scratch.add(agent.group_id)
        avg_energy = 0.0 if population == 0 else energy_sum / population
        avg_age = 0.0 if population == 0 else age_sum / population
        return TickMetrics(
            tick=tick,
            population=population,
            births=births,
            deaths=deaths,
            average_energy=avg_energy,
            average_age=avg_age,
            groups=len(self._group_scratch),
            neighbor_checks=neighbor_checks,
            tick_duration_ms=duration_ms,
        )

    def _try_get_agent(self, agent_id: int) -> Optional[Agent]:
        idx = self._id_to_index.get(agent_id)
        if idx is None:
            return None
        if 0 <= idx < len(self._agents):
            return self._agents[idx]
        return None

    def _refresh_index_map(self) -> None:
        self._id_to_index = {agent.id: i for i, agent in enumerate(self._agents)}
