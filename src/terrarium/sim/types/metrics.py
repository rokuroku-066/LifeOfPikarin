from __future__ import annotations

from dataclasses import dataclass


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
    group_memory_entries: int = 0
    group_food_memory_hits: int = 0
    group_food_memory_misses: int = 0
    group_danger_memory_reports: int = 0
    group_memory_inheritance_events: int = 0
    group_memory_entropy: float = 0.0
