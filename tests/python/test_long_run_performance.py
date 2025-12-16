import pytest

from terrarium.config import SimulationConfig
from terrarium.world import World


def test_long_run_population_groups_and_performance():
    config = SimulationConfig()
    world = World(config)

    for tick in range(5000):
        world.step(tick)

    populations = [m.population for m in world.metrics]
    max_population = max(populations)
    average_tick_ms = sum(m.tick_duration_ms for m in world.metrics) / len(world.metrics)
    final_metrics = world.metrics[-1]
    final_groups = final_metrics.groups

    assert 400 <= max_population
    assert 5 <= final_groups <= 10
    assert average_tick_ms <= 25.0
    assert final_metrics.ungrouped <= final_metrics.population * 0.25
