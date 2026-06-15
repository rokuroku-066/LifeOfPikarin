from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pygame.math import Vector2

from ..utils.math2d import _clamp_length_xy

if TYPE_CHECKING:
    from ..core.config import MemoryConfig
    from ..core.rng import DeterministicRng


@dataclass(slots=True)
class MemoryEntry:
    cell: tuple[int, int]
    food: float = 0.0
    danger: float = 0.0
    success: float = 0.0
    last_seen_tick: int = 0
    hits: int = 0


@dataclass(slots=True)
class MemorySummary:
    entries: int = 0
    food_hits: int = 0
    food_misses: int = 0
    danger_reports: int = 0
    inheritance_events: int = 0
    entropy: float = 0.0


class GroupMemory:
    """Bounded, deterministic shared memory keyed by group id and cell."""

    def __init__(self, config: MemoryConfig, cell_size: float):
        self._config = config
        self._cell_size = cell_size
        self._entries: dict[int, dict[tuple[int, int], MemoryEntry]] = {}
        self.food_hits = 0
        self.food_misses = 0
        self.danger_reports = 0
        self.inheritance_events = 0

    def clear(self) -> None:
        self._entries.clear()
        self.food_hits = 0
        self.food_misses = 0
        self.danger_reports = 0
        self.inheritance_events = 0

    def entries_for(self, group_id: int) -> dict[tuple[int, int], MemoryEntry]:
        return self._entries.get(group_id, {})

    def report_food(self, group_id: int, cell: tuple[int, int], strength: float, tick: int) -> None:
        if not self._config.enabled or group_id < 0 or strength <= self._config.min_report_food:
            return
        entry = self._entry(group_id, cell, tick)
        entry.food += max(0.0, strength) * self._config.food_learn_rate
        entry.last_seen_tick = tick
        self._prune(group_id, tick)

    def report_danger(self, group_id: int, cell: tuple[int, int], strength: float, tick: int) -> None:
        if not self._config.enabled or group_id < 0 or strength <= self._config.min_report_danger:
            return
        entry = self._entry(group_id, cell, tick)
        entry.danger += max(0.0, strength) * self._config.danger_learn_rate
        entry.last_seen_tick = tick
        self.danger_reports += 1
        self._prune(group_id, tick)

    def report_success(self, group_id: int, cell: tuple[int, int], strength: float, tick: int) -> None:
        if not self._config.enabled or group_id < 0 or strength <= 0.0:
            return
        entry = self._entry(group_id, cell, tick)
        entry.success += strength * self._config.success_learn_rate
        entry.last_seen_tick = tick
        self._prune(group_id, tick)

    def reinforce_food_visit(
        self, group_id: int, cell: tuple[int, int], food_eaten: float, tick: int
    ) -> None:
        if not self._config.enabled or group_id < 0:
            return
        group_entries = self._entries.get(group_id)
        if not group_entries or cell not in group_entries:
            return
        entry = group_entries[cell]
        entry.last_seen_tick = tick
        if food_eaten > self._config.min_report_food:
            entry.food += food_eaten * self._config.food_learn_rate
            entry.hits += 1
            self.food_hits += 1
        else:
            entry.food *= self._config.disappointment_decay
            self.food_misses += 1

    def decay(self, active_groups: set[int]) -> None:
        if not self._config.enabled:
            return
        for group_id in list(self._entries.keys()):
            if group_id not in active_groups:
                self._entries.pop(group_id, None)
                continue
            group_entries = self._entries[group_id]
            for cell in list(group_entries.keys()):
                entry = group_entries[cell]
                entry.food *= self._config.food_decay_per_env_tick
                entry.danger *= self._config.danger_decay_per_env_tick
                entry.success *= self._config.success_decay_per_env_tick
                if (
                    entry.food < self._config.eps
                    and entry.danger < self._config.eps
                    and entry.success < self._config.eps
                ):
                    group_entries.pop(cell, None)
            if not group_entries:
                self._entries.pop(group_id, None)

    def query_bias(self, group_id: int, position: Vector2, hunger: float, tick: int) -> Vector2:
        if not self._config.enabled or group_id < 0:
            return Vector2()
        group_entries = self._entries.get(group_id)
        if not group_entries:
            return Vector2()
        vx = 0.0
        vy = 0.0
        for entry in group_entries.values():
            center_x, center_y = self._cell_center(entry.cell)
            dx = center_x - position.x
            dy = center_y - position.y
            dist_sq = dx * dx + dy * dy + 1e-6
            freshness = self._freshness(entry, tick)
            distance_weight = 1.0 / (1.0 + dist_sq * 0.05)
            food_score = entry.food * hunger * freshness * distance_weight * self._config.food_memory_weight
            danger_score = entry.danger * freshness * distance_weight * self._config.danger_memory_weight
            success_score = entry.success * freshness * distance_weight * self._config.success_memory_weight
            attract = food_score + success_score
            vx += dx * attract
            vy += dy * attract
            vx -= dx * danger_score
            vy -= dy * danger_score
        return _clamp_length_xy(vx, vy, self._config.max_bias)

    def inherit_memory(self, parent_group: int, child_group: int, tick: int, rng: DeterministicRng) -> None:
        if not self._config.enabled or parent_group < 0 or child_group < 0 or parent_group == child_group:
            return
        parent_entries = self._entries.get(parent_group)
        if not parent_entries:
            return
        top_k = max(0, int(self._config.split_inherit_top_k))
        if top_k <= 0:
            return
        ranked = sorted(parent_entries.values(), key=lambda entry: self._score(entry, tick), reverse=True)
        copied = 0
        low = self._config.split_inherit_decay_min
        high = max(low, self._config.split_inherit_decay_max)
        child_entries = self._entries.setdefault(child_group, {})
        for entry in ranked[:top_k]:
            factor = rng.next_range(low, high)
            child_entries[entry.cell] = MemoryEntry(
                cell=entry.cell,
                food=entry.food * factor,
                danger=entry.danger * factor,
                success=entry.success * factor,
                last_seen_tick=tick,
                hits=max(0, int(entry.hits * factor)),
            )
            copied += 1
        if copied:
            self.inheritance_events += 1
            self._prune(child_group, tick)

    def summary(self, tick: int) -> MemorySummary:
        total_entries = sum(len(entries) for entries in self._entries.values())
        weights: list[float] = []
        for entries in self._entries.values():
            for entry in entries.values():
                weight = max(0.0, entry.food + entry.danger + entry.success)
                if weight > 0.0:
                    weights.append(weight)
        entropy = 0.0
        total = sum(weights)
        if total > 0.0:
            for weight in weights:
                p = weight / total
                entropy -= p * math.log(p)
        return MemorySummary(
            entries=total_entries,
            food_hits=self.food_hits,
            food_misses=self.food_misses,
            danger_reports=self.danger_reports,
            inheritance_events=self.inheritance_events,
            entropy=entropy,
        )

    def _entry(self, group_id: int, cell: tuple[int, int], tick: int) -> MemoryEntry:
        group_entries = self._entries.setdefault(group_id, {})
        entry = group_entries.get(cell)
        if entry is None:
            entry = MemoryEntry(cell=cell, last_seen_tick=tick)
            group_entries[cell] = entry
        return entry

    def _cell_center(self, cell: tuple[int, int]) -> tuple[float, float]:
        return ((cell[0] + 0.5) * self._cell_size, (cell[1] + 0.5) * self._cell_size)

    def _freshness(self, entry: MemoryEntry, tick: int) -> float:
        age = max(0, tick - entry.last_seen_tick)
        return 1.0 / (1.0 + age * 0.002)

    def _score(self, entry: MemoryEntry, tick: int) -> float:
        return (entry.food + entry.danger + entry.success + 0.05 * entry.hits) * self._freshness(entry, tick)

    def _prune(self, group_id: int, tick: int) -> None:
        group_entries = self._entries.get(group_id)
        if not group_entries:
            return
        max_entries = max(0, int(self._config.max_entries_per_group))
        if max_entries <= 0:
            self._entries.pop(group_id, None)
            return
        while len(group_entries) > max_entries:
            cell = min(group_entries, key=lambda key: self._score(group_entries[key], tick))
            group_entries.pop(cell, None)
