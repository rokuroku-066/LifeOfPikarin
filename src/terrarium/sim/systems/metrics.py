from __future__ import annotations

from typing import Tuple

from ..types.metrics import TickMetrics


def create_metrics(
    tick: int,
    births: int,
    deaths: int,
    neighbor_checks: int,
    duration_ms: float,
    stats: Tuple[int, float, float, int, int],
) -> TickMetrics:
    population, avg_energy, avg_age, groups, ungrouped = stats
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
    )
