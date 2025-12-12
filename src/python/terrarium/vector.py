from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Vec2:
    x: float
    y: float

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def normalized(self) -> "Vec2":
        mag = self.length()
        if mag < 1e-5:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / mag, self.y / mag)

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> "Vec2":
        return Vec2(self.x / scalar, self.y / scalar)

    @staticmethod
    def dot(a: "Vec2", b: "Vec2") -> float:
        return a.x * b.x + a.y * b.y

    @staticmethod
    def lerp(a: "Vec2", b: "Vec2", t: float) -> "Vec2":
        return Vec2(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)

    def clamp_length(self, max_length: float) -> "Vec2":
        mag_sq = self.length_squared()
        if mag_sq <= max_length * max_length:
            return self
        mag = math.sqrt(mag_sq)
        if mag <= 0:
            return Vec2(0.0, 0.0)
        scale = max_length / mag
        return Vec2(self.x * scale, self.y * scale)


ZERO = Vec2(0.0, 0.0)
