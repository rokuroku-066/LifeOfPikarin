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
