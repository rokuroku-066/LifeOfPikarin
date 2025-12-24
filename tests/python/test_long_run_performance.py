# import pytest

# from terrarium.sim.core.config import SimulationConfig
# from terrarium.sim.core.world import World


# def test_long_run_population_groups_and_performance():
#     config = SimulationConfig()
#     world = World(config)

#     for tick in range(5000):
#         world.step(tick)

#     populations = [m.population for m in world.metrics]
#     births = [m.births for m in world.metrics]
#     deaths = [m.deaths for m in world.metrics]
#     average_tick_ms = sum(m.tick_duration_ms for m in world.metrics) / len(world.metrics)
#     final_metrics = world.metrics[-1]
#     final_groups = final_metrics.groups
#     max_deaths_per_tick = max(deaths)

#     zero_birth_streak = 0
#     worst_zero_birth_streak = 0
#     for value in births:
#         if value == 0:
#             zero_birth_streak += 1
#             worst_zero_birth_streak = max(worst_zero_birth_streak, zero_birth_streak)
#         else:
#             zero_birth_streak = 0

#     summary = (
#         f"final_pop={final_metrics.population}, "
#         f"final_groups={final_groups}, "
#         f"ungrouped={final_metrics.ungrouped}, "
#         f"avg_tick_ms={average_tick_ms:.2f}, "
#         f"max_deaths_per_tick={max_deaths_per_tick}, "
#         f"worst_zero_birth_streak={worst_zero_birth_streak}"
#     )

#     assert final_metrics.population >= 250, summary
#     assert 5 <= final_groups <= 10, summary
#     assert final_metrics.ungrouped < final_metrics.population * 0.25, summary
#     assert average_tick_ms <= 35.0, summary
#     assert max_deaths_per_tick <= 10, summary
#     assert worst_zero_birth_streak < 20, summary
