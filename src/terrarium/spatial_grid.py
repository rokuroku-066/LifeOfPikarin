from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from pygame.math import Vector2


@dataclass
class GridEntry:
    id: int
    position: Vector2


class SpatialGrid:
    def __init__(self, cell_size: float) -> None:
        self._cell_size = cell_size
        self._cells: Dict[Tuple[int, int], List[GridEntry]] = {}
        self._neighbor_scratch: List[GridEntry] = []

    def clear(self) -> None:
        for bucket in self._cells.values():
            bucket.clear()

    def insert(self, agent_id: int, position: Vector2) -> None:
        key = self._cell_key(position)
        bucket = self._cells.setdefault(key, [])
        bucket.append(GridEntry(agent_id, position))

    def get_neighbors(self, position: Vector2, radius: float) -> List[GridEntry]:
        self._neighbor_scratch.clear()
        base_key = self._cell_key(position)
        cell_range = int((radius + self._cell_size - 1e-6) // self._cell_size) + 1
        radius_sq = radius * radius

        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                key = (base_key[0] + dx, base_key[1] + dy)
                bucket = self._cells.get(key)
                if not bucket:
                    continue
                for entry in bucket:
                    if entry.position.distance_squared_to(position) <= radius_sq:
                        self._neighbor_scratch.append(entry)
        return self._neighbor_scratch

    def _cell_key(self, position: Vector2) -> Tuple[int, int]:
        return (int(position.x // self._cell_size), int(position.y // self._cell_size))
