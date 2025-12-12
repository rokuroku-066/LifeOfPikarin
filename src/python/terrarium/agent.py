from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .vector import Vec2


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
    position: Vec2
    velocity: Vec2
    energy: float
    age: float
    state: AgentState
    alive: bool = True
    stress: float = 0.0
