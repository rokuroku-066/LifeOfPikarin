from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, List, Tuple

from pygame.math import Vector2

if TYPE_CHECKING:
    from .agent import Agent


class SpatialGrid:
    def __init__(self, cell_size: float) -> None:
        self._cell_size = cell_size
        self._cells: Dict[Tuple[int, int], List["Agent"]] = {}
        self._neighbor_scratch: List["Agent"] = []
        self._active_keys: List[Tuple[int, int]] = []

    def build_neighbor_cell_offsets(self, radius: float) -> List[Tuple[int, int]]:
        cell_range = int(math.ceil(radius / self._cell_size))
        return [(dx, dy) for dx in range(-cell_range, cell_range + 1) for dy in range(-cell_range, cell_range + 1)]

    def clear(self) -> None:
        for key in self._active_keys:
            bucket = self._cells.get(key)
            if bucket:
                bucket.clear()
        self._active_keys.clear()

    def insert(self, agent: "Agent") -> None:
        key = self._cell_key(agent.position)
        bucket = self._cells.get(key)
        if bucket is None:
            bucket = []
            self._cells[key] = bucket
            self._active_keys.append(key)
        elif not bucket:
            # Bucket exists but was cleared at the start of this tick; mark it active again.
            self._active_keys.append(key)
        bucket.append(agent)

    def get_neighbors(self, position: Vector2, radius: float) -> List["Agent"]:
        self._neighbor_scratch.clear()
        base_key = self._cell_key(position)
        cell_range = int(math.ceil(radius / self._cell_size))
        radius_sq = radius * radius
        pos_x = position.x
        pos_y = position.y

        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                key = (base_key[0] + dx, base_key[1] + dy)
                bucket = self._cells.get(key)
                if not bucket:
                    continue
                for agent in bucket:
                    pos = agent.position
                    offset_x = pos.x - pos_x
                    offset_y = pos.y - pos_y
                    if offset_x * offset_x + offset_y * offset_y <= radius_sq:
                        self._neighbor_scratch.append(agent)
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

        This is allocation-free and avoids id->agent lookups.
        Callers must clear/consume the buffers after use.
        """

        out_agents.clear()
        offset_count = 0
        base_key = self._cell_key(position)
        cell_range = int(math.ceil(radius / self._cell_size))
        radius_sq = radius * radius
        pos_x = position.x
        pos_y = position.y

        cells = self._cells
        append_agent = out_agents.append
        append_offset = out_offsets.append

        for dx in range(-cell_range, cell_range + 1):
            for dy in range(-cell_range, cell_range + 1):
                bucket = cells.get((base_key[0] + dx, base_key[1] + dy))
                if not bucket:
                    continue
                for agent in bucket:
                    if exclude_id is not None and agent.id == exclude_id:
                        continue
                    pos = agent.position
                    offset_x = pos.x - pos_x
                    offset_y = pos.y - pos_y
                    if offset_x * offset_x + offset_y * offset_y <= radius_sq:
                        append_agent(agent)
                        if offset_count < len(out_offsets):
                            out_offsets[offset_count].update(offset_x, offset_y)
                        else:
                            append_offset(Vector2(offset_x, offset_y))
                        offset_count += 1

        del out_offsets[offset_count:]

    def collect_neighbors_precomputed(
        self,
        position: Vector2,
        cell_offsets: List[Tuple[int, int]],
        radius_sq: float,
        out_agents: List["Agent"],
        out_offsets: List[Vector2],
        exclude_id: int | None = None,
        out_dist_sq: List[float] | None = None,
    ) -> None:
        """
        Collect neighbors using precomputed cell offsets and radius squared values to reduce per-call overhead.
        """

        out_agents.clear()
        offset_count = 0
        if out_dist_sq is not None:
            out_dist_sq.clear()
        base_key = self._cell_key(position)
        pos_x = position.x
        pos_y = position.y
        cells = self._cells
        append_agent = out_agents.append
        append_offset = out_offsets.append
        dist_buffer = out_dist_sq
        append_dist = dist_buffer.append if dist_buffer is not None else None

        for dx, dy in cell_offsets:
            bucket = cells.get((base_key[0] + dx, base_key[1] + dy))
            if not bucket:
                continue
            for agent in bucket:
                if exclude_id is not None and agent.id == exclude_id:
                    continue
                pos = agent.position
                offset_x = pos.x - pos_x
                offset_y = pos.y - pos_y
                dist_sq = offset_x * offset_x + offset_y * offset_y
                if dist_sq <= radius_sq:
                    append_agent(agent)
                    if offset_count < len(out_offsets):
                        out_offsets[offset_count].update(offset_x, offset_y)
                    else:
                        append_offset(Vector2(offset_x, offset_y))
                    if dist_buffer is not None:
                        if offset_count < len(dist_buffer):
                            dist_buffer[offset_count] = dist_sq
                        else:
                            append_dist(dist_sq)
                    offset_count += 1

        del out_offsets[offset_count:]
        if dist_buffer is not None:
            del dist_buffer[offset_count:]

    def _cell_key(self, position: Vector2) -> Tuple[int, int]:
        return (int(position.x // self._cell_size), int(position.y // self._cell_size))
