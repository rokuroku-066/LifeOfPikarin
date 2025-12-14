from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple

from pygame.math import Vector2

if TYPE_CHECKING:
    from .agent import Agent


@dataclass
class GridEntry:
    id: int
    position: Vector2
    agent: "Agent | None" = None


class SpatialGrid:
    def __init__(self, cell_size: float) -> None:
        self._cell_size = cell_size
        self._cells: Dict[Tuple[int, int], List[GridEntry]] = {}
        self._neighbor_scratch: List[GridEntry] = []

    def clear(self) -> None:
        for bucket in self._cells.values():
            bucket.clear()

    def insert(self, agent_id: int, position: Vector2, agent: "Agent | None" = None) -> None:
        key = self._cell_key(position)
        bucket = self._cells.setdefault(key, [])
        bucket.append(GridEntry(agent_id, position, agent))

    def get_neighbors(self, position: Vector2, radius: float) -> List[GridEntry]:
        self._neighbor_scratch.clear()
        base_key = self._cell_key(position)
        cell_range = int(math.ceil(radius / self._cell_size))
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

    def collect_neighbors(
        self,
        position: Vector2,
        radius: float,
        out_agents: List["Agent"],
        out_offsets: List[Vector2],
        exclude_id: int | None = None,
    ) -> None:
        """
        Fill the provided buffers with agent references and their offsets from `position`.

        This is allocation-free and avoids id->agent lookups when callers insert with `agent` set.
        Callers must clear/consume the buffers after use.
        """

        out_agents.clear()
        out_offsets.clear()
        base_key = self._cell_key(position)
        cell_range = int(math.ceil(radius / self._cell_size))
        radius_sq = radius * radius

        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                key = (base_key[0] + dx, base_key[1] + dy)
                bucket = self._cells.get(key)
                if not bucket:
                    continue
                for entry in bucket:
                    if entry.agent is None:
                        continue
                    if exclude_id is not None and entry.agent.id == exclude_id:
                        continue
                    offset = entry.position - position
                    if offset.length_squared() <= radius_sq:
                        out_agents.append(entry.agent)
                        out_offsets.append(offset)

    def _cell_key(self, position: Vector2) -> Tuple[int, int]:
        return (int(position.x // self._cell_size), int(position.y // self._cell_size))
