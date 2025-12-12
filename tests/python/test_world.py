from __future__ import annotations

from pygame.math import Vector2

from terrarium.agent import Agent, AgentState
from terrarium.config import FeedbackConfig, SimulationConfig, SpeciesConfig
from terrarium.world import World


def run_steps(config: SimulationConfig, steps: int):
    world = World(config)
    snapshots = []
    for tick in range(steps):
        metrics = world.step(tick)
        snapshots.append((metrics.population, metrics.births, metrics.deaths, round(metrics.average_energy, 4)))
    return snapshots


def test_deterministic_steps():
    config = SimulationConfig(seed=1234, initial_population=50, max_population=120)
    result_a = run_steps(config, 50)
    # recreate config to ensure RNG resets
    config_b = SimulationConfig(seed=1234, initial_population=50, max_population=120)
    result_b = run_steps(config_b, 50)
    assert result_a == result_b


def test_population_bounds_respected():
    config = SimulationConfig(seed=7, initial_population=20, max_population=25)
    world = World(config)
    for tick in range(200):
        world.step(tick)
        assert len(world.agents) <= config.max_population


def test_disease_death_returns_zero_births():
    config = SimulationConfig(
        seed=99,
        initial_population=1,
        feedback=FeedbackConfig(
            local_density_soft_cap=0,
            disease_probability_per_neighbor=1.0,
        ),
    )
    world = World(config)
    agent = world.agents[0]

    births = world._apply_life_cycle(agent, neighbor_count=100, can_create_groups=False)

    assert births == 0
    assert not agent.alive
    assert world._pending_food  # type: ignore[attr-defined]


def test_lonely_agent_switches_to_nearby_majority():
    config = SimulationConfig(
        seed=5,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=2.0,
            group_switch_chance=1.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=0,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=1,
                generation=0,
                group_id=1,
                position=Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=2,
                generation=0,
                group_id=1,
                position=Vector2(1.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 3
    world._refresh_index_map()

    for tick in range(3):
        world.step(tick)

    assert world.agents[0].group_id == 1
    assert world.agents[0].group_lonely_seconds == 0.0


def test_close_allies_reset_lonely_timer():
    config = SimulationConfig(
        seed=11,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=2.0,
            group_switch_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=10,
                generation=0,
                group_id=2,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
                group_lonely_seconds=1.5,
            ),
            Agent(
                id=11,
                generation=0,
                group_id=2,
                position=Vector2(0.3, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 12
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 2
    assert world.agents[0].group_lonely_seconds == 0.0


def test_detach_radius_separate_from_cohesion():
    config = SimulationConfig(
        seed=21,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=4.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=2.0,
            group_detach_radius=4.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=1.0,
            group_switch_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=20,
                generation=0,
                group_id=3,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=21,
                generation=0,
                group_id=3,
                position=Vector2(3.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 22
    world._refresh_index_map()

    world.step(0)
    world.step(1)

    assert world.agents[0].group_id == 3
    assert world.agents[0].group_lonely_seconds == 0.0
