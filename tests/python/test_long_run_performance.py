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
    peak_idx = populations.index(max_population)
    post_peak_min = min(populations[peak_idx:])
    trailing_window = populations[-1000:]
    average_tick_ms = sum(m.tick_duration_ms for m in world.metrics) / len(world.metrics)

    max_deaths_per_tick = max(m.deaths for m in world.metrics)
    zero_birth_streak = 0
    max_zero_birth_streak = 0
    for metrics in world.metrics:
        if metrics.births == 0:
            zero_birth_streak += 1
            max_zero_birth_streak = max(max_zero_birth_streak, zero_birth_streak)
        else:
            zero_birth_streak = 0

    final_metrics = world.metrics[-1]
    final_groups = final_metrics.groups

    assert 400 <= max_population
    assert post_peak_min >= max_population * 0.15
    assert final_metrics.population >= max_population * 0.15
    assert len(set(trailing_window)) > 5
    assert 4 <= final_groups <= 10
    assert average_tick_ms <= 30.0
    assert final_metrics.ungrouped <= final_metrics.population * 0.25
    assert max_deaths_per_tick < 10
    assert max_zero_birth_streak < 20
