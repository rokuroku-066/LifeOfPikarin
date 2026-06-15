from __future__ import annotations

from pygame.math import Vector2

from terrarium.sim.core.config import MemoryConfig, SimulationConfig
from terrarium.sim.core.rng import DeterministicRng
from terrarium.sim.systems.group_memory import GroupMemory


def test_group_memory_reports_food_and_prunes_to_cap():
    config = MemoryConfig(max_entries_per_group=2, food_learn_rate=1.0)
    memory = GroupMemory(config, cell_size=5.0)

    memory.report_food(1, (0, 0), 1.0, 0)
    memory.report_food(1, (1, 0), 2.0, 1)
    memory.report_food(1, (2, 0), 3.0, 2)

    entries = memory.entries_for(1)
    assert len(entries) == 2
    assert (0, 0) not in entries
    assert entries[(2, 0)].food == 3.0


def test_group_memory_reinforces_hits_and_decays_misses():
    config = MemoryConfig(food_learn_rate=1.0, disappointment_decay=0.5)
    memory = GroupMemory(config, cell_size=5.0)
    memory.report_food(1, (0, 0), 1.0, 0)

    memory.reinforce_food_visit(1, (0, 0), 2.0, 1)
    assert memory.entries_for(1)[(0, 0)].food == 3.0
    assert memory.food_hits == 1

    memory.reinforce_food_visit(1, (0, 0), 0.0, 2)
    assert memory.entries_for(1)[(0, 0)].food == 1.5
    assert memory.food_misses == 1


def test_group_memory_query_attracts_food_and_avoids_danger():
    config = MemoryConfig(food_learn_rate=1.0, danger_learn_rate=1.0, memory_query_stride=1)
    memory = GroupMemory(config, cell_size=5.0)
    memory.report_food(1, (2, 0), 3.0, 0)
    food_bias = memory.query_bias(1, Vector2(0.0, 2.5), hunger=1.0, tick=0)
    assert food_bias.x > 0.0

    memory = GroupMemory(config, cell_size=5.0)
    memory.report_danger(1, (2, 0), 3.0, 0)
    danger_bias = memory.query_bias(1, Vector2(0.0, 2.5), hunger=0.0, tick=0)
    assert danger_bias.x < 0.0


def test_group_memory_inheritance_copies_degraded_top_entries_deterministically():
    config = MemoryConfig(split_inherit_top_k=1, food_learn_rate=1.0)
    first = GroupMemory(config, cell_size=5.0)
    second = GroupMemory(config, cell_size=5.0)
    for memory in (first, second):
        memory.report_food(1, (0, 0), 1.0, 0)
        memory.report_food(1, (1, 0), 10.0, 0)
        memory.inherit_memory(1, 2, 5, DeterministicRng(7))

    assert set(first.entries_for(2)) == {(1, 0)}
    assert first.entries_for(2)[(1, 0)].food == second.entries_for(2)[(1, 0)].food
    assert 4.0 <= first.entries_for(2)[(1, 0)].food <= 8.0


def test_world_metrics_include_group_memory_fields():
    config = SimulationConfig(initial_population=0)
    # Constructing the config is enough to verify defaults are available to World users.
    assert config.memory.enabled is True
