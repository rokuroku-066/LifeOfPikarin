from __future__ import annotations

from typing import Tuple

from ..types.metrics import TickMetrics
from .group_memory import MemorySummary


def create_metrics(
    tick: int,
    births: int,
    deaths: int,
    neighbor_checks: int,
    duration_ms: float,
    stats: Tuple[int, float, float, int, int],
    memory_summary: MemorySummary | None = None,
) -> TickMetrics:
    population, avg_energy, avg_age, groups, ungrouped = stats
    if memory_summary is None:
        memory_summary = MemorySummary()
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
        group_memory_entries=memory_summary.entries,
        group_food_memory_hits=memory_summary.food_hits,
        group_food_memory_misses=memory_summary.food_misses,
        group_danger_memory_reports=memory_summary.danger_reports,
        group_memory_inheritance_events=memory_summary.inheritance_events,
        group_memory_entropy=memory_summary.entropy,
    )
