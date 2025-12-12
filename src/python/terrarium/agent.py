from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pygame.math import Vector2


class AgentState(str, Enum):
    IDLE = "Idle"
    SEEKING_FOOD = "SeekingFood"
    SEEKING_MATE = "SeekingMate"
    FLEE = "Flee"
    WANDER = "Wander"


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
    alive: bool = True
    stress: float = 0.0
