from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .metrics import TickMetrics


@dataclass(slots=True)
class Snapshot:
    tick: int
    metrics: TickMetrics
    agents: List[Dict[str, Any]]
    world: "SnapshotWorld"
    metadata: "SnapshotMetadata"
    fields: "SnapshotFields"


@dataclass(slots=True)
class SnapshotWorld:
    size: float


@dataclass(slots=True)
class SnapshotMetadata:
    world_size: float
    sim_dt: float
    tick_rate: float
    seed: int
    config_version: str


@dataclass(slots=True)
class SnapshotFields:
    food: Dict[str, Any]
    pheromones: Dict[str, Any]
