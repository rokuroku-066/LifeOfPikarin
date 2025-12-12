from __future__ import annotations

import math
import random
from typing import Optional

from pygame.math import Vector2


class DeterministicRng:
    def __init__(self, seed: int):
        self._seed = seed
        self._random = random.Random(seed)

    def reset(self) -> None:
        self._random.seed(self._seed)

    def next_float(self) -> float:
        return self._random.random()

    def next_range(self, low: float, high: float) -> float:
        return self._random.uniform(low, high)

    def next_int(self, max_value: int) -> int:
        return self._random.randrange(max_value)

    def next_unit_circle(self) -> Vector2:
        angle = self._random.uniform(0, 2 * math.pi)
        vector = Vector2()
        vector.from_polar((1, math.degrees(angle)))
        return vector

    def sample_choice(self, items: list[Optional[int]]) -> Optional[int]:
        if not items:
            return None
        return self._random.choice(items)
