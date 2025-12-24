from __future__ import annotations

import math

from pygame.math import Vector2

ZERO = Vector2()


def _safe_normalize(vector: Vector2) -> Vector2:
    return _safe_normalize_xy(vector.x, vector.y)


def _safe_normalize_xy(x: float, y: float) -> Vector2:
    magnitude_sq = x * x + y * y
    if magnitude_sq < 1e-10:
        return Vector2()
    inv = 1.0 / math.sqrt(magnitude_sq)
    return Vector2(x * inv, y * inv)


def _clamp_length_xy(x: float, y: float, max_length: float) -> Vector2:
    if max_length <= 0:
        return Vector2()
    magnitude_sq = x * x + y * y
    if magnitude_sq <= max_length * max_length:
        return Vector2(x, y)
    if magnitude_sq == 0:
        return Vector2()
    inv = max_length / math.sqrt(magnitude_sq)
    return Vector2(x * inv, y * inv)


def _clamp_length_xy_f(x: float, y: float, max_length: float) -> tuple[float, float]:
    if max_length <= 0.0:
        return 0.0, 0.0
    magnitude_sq = x * x + y * y
    max_sq = max_length * max_length
    if magnitude_sq <= max_sq:
        return x, y
    if magnitude_sq <= 1e-18:
        return 0.0, 0.0
    inv = max_length / math.sqrt(magnitude_sq)
    return x * inv, y * inv


def _clamp_length(vector: Vector2, max_length: float) -> Vector2:
    if max_length <= 0:
        return Vector2()
    magnitude_sq = vector.length_squared()
    if magnitude_sq <= max_length * max_length:
        return vector
    if magnitude_sq == 0:
        return Vector2()
    return vector.normalize() * max_length


def _heading_from_velocity(vector: Vector2) -> float:
    if vector.length_squared() < 1e-12:
        return 0.0
    return math.atan2(vector.y, vector.x)


def _clamp_value(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))
