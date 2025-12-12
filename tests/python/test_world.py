from __future__ import annotations

from terrarium.config import FeedbackConfig, SimulationConfig
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
