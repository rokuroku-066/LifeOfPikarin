import pytest

from terrarium.config import SimulationConfig
from terrarium.world import World


@pytest.mark.config_change
def test_long_run_population_groups_and_performance():
    config = SimulationConfig()
    world = World(config)

    for tick in range(5000):
        world.step(tick)

    populations = [m.population for m in world.metrics]
    max_population = max(populations)
    average_tick_ms = sum(m.tick_duration_ms for m in world.metrics) / len(world.metrics)
    final_groups = world.metrics[-1].groups
    max_groups = max(m.groups for m in world.metrics)

    assert 400 <= max_population <= 500
    assert 5 <= final_groups <= 10
    assert max_groups <= 10
    assert average_tick_ms <= 25.0
