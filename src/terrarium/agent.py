from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pygame.math import Vector2


class AgentState(str, Enum):
    IDLE = "Idle"
    SEEKING_FOOD = "SeekingFood"
    SEEKING_MATE = "SeekingMate"
    FLEE = "Flee"
    WANDER = "Wander"


@dataclass
class AgentTraits:
    speed: float = 1.0
    metabolism: float = 1.0
    disease_resistance: float = 1.0
    fertility: float = 1.0


@dataclass
class Agent:
    id: int
    generation: int
    group_id: int
    position: Vector2
    velocity: Vector2
    energy: float
    age: float
    state: AgentState
    lineage_id: int = 0
    traits: AgentTraits = field(default_factory=AgentTraits)
    alive: bool = True
    stress: float = 0.0
    group_lonely_seconds: float = 0.0
    group_cooldown: float = 0.0
    heading: float = 0.0
    wander_dir: Vector2 = field(default_factory=Vector2)
    wander_time: float = 0.0
