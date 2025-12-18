from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from pygame.math import Vector2

from .config import EnvironmentConfig, ResourcePatchConfig

_ORTHOGONAL_OFFSETS: Tuple[Tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class FoodCell:
    value: float
    max: float
    regen_per_second: float


class EnvironmentGrid:
    def __init__(self, cell_size: float, config: EnvironmentConfig, world_size: float):
        self._cell_size = cell_size
        self._world_size = world_size
        self._max_index = max(1, int(math.ceil(world_size / cell_size)))
        self._default_max_food = config.food_per_cell
        self._default_food_regen_per_second = config.food_regen_per_second
        self._default_initial_food = min(config.food_per_cell, config.food_per_cell * 0.8)
        self._food_diffusion_rate = config.food_diffusion_rate
        self._food_decay_rate = config.food_decay_rate
        self._pheromone_diffusion_rate = config.pheromone_diffusion_rate
        self._pheromone_decay_rate = config.pheromone_decay_rate
        self._danger_diffusion_rate = config.danger_diffusion_rate
        self._danger_decay_rate = config.danger_decay_rate
        self._group_food_max = config.group_food_max_per_cell
        self._group_food_diffusion_rate = config.group_food_diffusion_rate
        self._group_food_decay_rate = config.group_food_decay_rate
        self._patches: Iterable[ResourcePatchConfig] = config.resource_patches or []

        self._food_cells: Dict[Tuple[int, int], FoodCell] = {}
        self._food_buffer: Dict[Tuple[int, int], float] = {}
        self._danger_field: Dict[Tuple[int, int], float] = {}
        self._danger_buffer: Dict[Tuple[int, int], float] = {}
        self._pheromone_field: Dict[Tuple[int, int, int], float] = {}
        self._pheromone_buffer: Dict[Tuple[int, int, int], float] = {}
        self._group_food_field: Dict[Tuple[int, int, int], float] = {}
        self._group_food_buffer: Dict[Tuple[int, int, int], float] = {}
        self._food_regen_multiplier = 1.0

        self._initialize_patches()

    def export_food_cells(self) -> Dict[str, object]:
        cells = [
            {"x": x, "y": y, "value": cell.value}
            for (x, y), cell in self._food_cells.items()
            if cell.value > 0.0
        ]
        return {"cells": cells, "resolution": self._max_index, "cell_size": self._cell_size}

    def export_pheromone_field(self) -> Dict[str, object]:
        if not self._pheromone_field:
            return {"cells": [], "resolution": self._max_index, "cell_size": self._cell_size}

        per_cell: Dict[Tuple[int, int], Tuple[float, int]] = {}
        for (x, y, group_id), value in self._pheromone_field.items():
            if value <= 0.0:
                continue
            best = per_cell.get((x, y))
            if best is None or value > best[0]:
                per_cell[(x, y)] = (value, group_id)

        cells = [
            {"x": x, "y": y, "value": value, "group": group_id}
            for (x, y), (value, group_id) in per_cell.items()
            if value > 0.0
        ]
        return {"cells": cells, "resolution": self._max_index, "cell_size": self._cell_size}

    def reset(self) -> None:
        self._food_cells.clear()
        self._food_buffer.clear()
        self._danger_field.clear()
        self._danger_buffer.clear()
        self._pheromone_field.clear()
        self._pheromone_buffer.clear()
        self._group_food_field.clear()
        self._group_food_buffer.clear()
        self._food_regen_multiplier = 1.0
        self._initialize_patches()

    @property
    def food_regen_multiplier(self) -> float:
        return self._food_regen_multiplier

    def set_food_regen_multiplier(self, multiplier: float) -> None:
        self._food_regen_multiplier = max(0.0, float(multiplier))

    def _sanitize_food_keys(self) -> None:
        if not self._food_cells:
            return
        for key, cell in list(self._food_cells.items()):
            clamped_key = (
                max(0, min(self._max_index - 1, key[0])),
                max(0, min(self._max_index - 1, key[1])),
            )
            if clamped_key != key:
                self._food_cells.pop(key, None)
                existing = self._food_cells.get(clamped_key)
                if existing:
                    existing.value = min(existing.max, existing.value + cell.value)
                else:
                    self._food_cells[clamped_key] = cell

    def sample_food(self, position: Vector2) -> float:
        key = self._cell_key(position)
        cell = self._get_or_create_food_cell(key)
        self._food_cells[key] = cell
        return cell.value

    def peek_food(self, position: Vector2) -> float:
        cell = self._food_cells.get(self._cell_key(position))
        return cell.value if cell is not None else 0.0

    def consume_food(self, position: Vector2, amount: float) -> None:
        key = self._cell_key(position)
        cell = self._get_or_create_food_cell(key)
        cell.value = max(0.0, cell.value - amount)
        self._food_cells[key] = cell

    def add_food(self, position: Vector2, amount: float) -> None:
        if amount <= 0:
            return
        key = self._cell_key(position)
        cell = self._get_or_create_food_cell(key, initial_value=0.0)
        cell.value = min(cell.max, cell.value + amount)
        self._food_cells[key] = cell

    def sample_group_food(self, position: Vector2, group_id: int) -> float:
        if group_id < 0:
            return 0.0
        key = (*self._cell_key(position), group_id)
        return self._group_food_field.get(key, 0.0)

    def consume_group_food(self, position: Vector2, group_id: int, amount: float) -> None:
        if group_id < 0 or amount <= 0:
            return
        key = (*self._cell_key(position), group_id)
        current = self._group_food_field.get(key)
        if current is None:
            return
        new_value = max(0.0, current - amount)
        if new_value <= 1e-6:
            self._group_food_field.pop(key, None)
        else:
            self._group_food_field[key] = new_value

    def add_group_food(self, position: Vector2, group_id: int, amount: float) -> None:
        if amount <= 0 or group_id < 0:
            return
        key = (*self._cell_key(position), group_id)
        existing = self._group_food_field.get(key, 0.0)
        new_value = min(self._group_food_max, existing + amount)
        if new_value <= 0.0:
            return
        self._group_food_field[key] = new_value

    def sample_danger(self, position: Vector2) -> float:
        return self._danger_field.get(self._cell_key(position), 0.0)

    def add_danger(self, position: Vector2, amount: float) -> None:
        key = self._cell_key(position)
        self._danger_field[key] = self._danger_field.get(key, 0.0) + amount

    def has_danger(self) -> bool:
        return bool(self._danger_field)

    def sample_pheromone(self, position: Vector2, group_id: int) -> float:
        field_key = (*self._cell_key(position), group_id)
        return self._pheromone_field.get(field_key, 0.0)

    def add_pheromone(self, position: Vector2, group_id: int, amount: float) -> None:
        key = (*self._cell_key(position), group_id)
        self._pheromone_field[key] = self._pheromone_field.get(key, 0.0) + amount

    def tick(self, delta_time: float) -> None:
        self._sanitize_food_keys()
        self._regen_food(delta_time)
        self._diffuse_food(delta_time)
        if self._group_food_diffusion_rate > 0 or self._group_food_decay_rate > 0:
            self._diffuse_group_food(delta_time)
        if self._danger_diffusion_rate > 0 or self._danger_decay_rate > 0:
            self._diffuse_field(self._danger_field, self._danger_buffer, self._danger_diffusion_rate, self._danger_decay_rate, delta_time)
        if self._pheromone_diffusion_rate > 0 or self._pheromone_decay_rate > 0:
            self._diffuse_field(self._pheromone_field, self._pheromone_buffer, self._pheromone_diffusion_rate, self._pheromone_decay_rate, delta_time)

    def _regen_food(self, delta_time: float) -> None:
        multiplier = self._food_regen_multiplier
        for key, cell in list(self._food_cells.items()):
            clamped_key = (
                max(0, min(self._max_index - 1, key[0])),
                max(0, min(self._max_index - 1, key[1])),
            )
            if clamped_key != key:
                self._food_cells.pop(key, None)
                key = clamped_key
            cell.value = min(cell.max, cell.value + cell.regen_per_second * multiplier * delta_time)
            self._food_cells[key] = cell

    def _diffuse_food(self, delta_time: float) -> None:
        if self._food_diffusion_rate <= 0 and self._food_decay_rate <= 0:
            return

        self._food_buffer.clear()
        for key, cell in self._food_cells.items():
            if cell.value <= 0:
                continue
            decayed = cell.value * max(0.0, 1.0 - self._food_decay_rate * delta_time)
            spread_portion = decayed * min(1.0, self._food_diffusion_rate * delta_time)
            remain = decayed - spread_portion
            share = spread_portion * 0.25

            self._accumulate(self._food_buffer, key, remain)
            self._accumulate(self._food_buffer, (key[0] + 1, key[1]), share)
            self._accumulate(self._food_buffer, (key[0] - 1, key[1]), share)
            self._accumulate(self._food_buffer, (key[0], key[1] + 1), share)
            self._accumulate(self._food_buffer, (key[0], key[1] - 1), share)

        for key, value in self._food_buffer.items():
            if value <= 1e-4:
                continue
            cell = self._get_or_create_food_cell(key, create_if_missing=True, initial_value=0.0)
            cell.value = min(cell.max, value)
            self._food_cells[key] = cell

        for key in list(self._food_cells.keys()):
            if key not in self._food_buffer and self._food_cells[key].value <= 1e-4:
                self._food_cells.pop(key, None)

    def _diffuse_group_food(self, delta_time: float) -> None:
        if not self._group_food_field:
            return
        if self._group_food_diffusion_rate <= 0 and self._group_food_decay_rate <= 0:
            return

        self._group_food_buffer.clear()
        diffusion = max(0.0, self._group_food_diffusion_rate)
        decay = max(0.0, self._group_food_decay_rate)
        for key, value in self._group_food_field.items():
            if value <= 0:
                continue
            decayed = value * max(0.0, 1.0 - decay * delta_time)
            spread = decayed * min(1.0, diffusion * delta_time)
            remain = decayed - spread
            share = spread * 0.25

            self._accumulate(self._group_food_buffer, key, remain)
            for ox, oy in _ORTHOGONAL_OFFSETS:
                self._accumulate(self._group_food_buffer, self._add_key(key, ox, oy), share)

        self._group_food_field.clear()
        for key, value in self._group_food_buffer.items():
            if value > 1e-5:
                self._group_food_field[key] = min(self._group_food_max, value)

    def _diffuse_field(self, field: Dict[Tuple[int, ...], float], buffer: Dict[Tuple[int, ...], float], diffusion_rate: float, decay_rate: float, delta_time: float) -> None:
        buffer.clear()
        for key, value in field.items():
            if value <= 0:
                continue
            decayed = value * max(0.0, 1.0 - decay_rate * delta_time)
            spread = decayed * min(1.0, diffusion_rate * delta_time)
            remain = decayed - spread
            share = spread * 0.25

            self._accumulate(buffer, key, remain)
            for ox, oy in _ORTHOGONAL_OFFSETS:
                self._accumulate(buffer, self._add_key(key, ox, oy), share)

        field.clear()
        for key, value in buffer.items():
            if value > 1e-5:
                field[key] = value

    def prune_pheromones(self, active_groups: Set[int]) -> None:
        if not self._pheromone_field:
            return
        if not active_groups:
            self._pheromone_field.clear()
            return
        for key in list(self._pheromone_field.keys()):
            if key[2] not in active_groups:
                self._pheromone_field.pop(key, None)

    def prune_group_food(self, active_groups: Set[int]) -> None:
        if not self._group_food_field:
            return
        if not active_groups:
            self._group_food_field.clear()
            return
        for key in list(self._group_food_field.keys()):
            if key[2] not in active_groups:
                self._group_food_field.pop(key, None)

    def _add_key(self, key: Tuple[int, ...], dx: int, dy: int) -> Tuple[int, ...]:
        if len(key) == 2:
            return self._add_key2(key, dx, dy)
        return self._add_key3(key, dx, dy)

    def _add_key2(self, key: Tuple[int, int], dx: int, dy: int) -> Tuple[int, int]:
        clamped_x = max(0, min(self._max_index - 1, key[0] + dx))
        clamped_y = max(0, min(self._max_index - 1, key[1] + dy))
        return (clamped_x, clamped_y)

    def _add_key3(self, key: Tuple[int, int, int], dx: int, dy: int) -> Tuple[int, int, int]:
        clamped_x = max(0, min(self._max_index - 1, key[0] + dx))
        clamped_y = max(0, min(self._max_index - 1, key[1] + dy))
        return (clamped_x, clamped_y, key[2])

    def _accumulate(self, buffer: Dict[Tuple[int, ...], float], key: Tuple[int, ...], value: float) -> None:
        buffer[key] = buffer.get(key, 0.0) + value

    def _get_or_create_food_cell(self, key: Tuple[int, int], create_if_missing: bool = True, initial_value: float | None = None) -> FoodCell:
        if key in self._food_cells:
            return self._food_cells[key]
        if not create_if_missing:
            return FoodCell(0.0, 0.0, 0.0)

        max_food = self._default_max_food
        regen = self._default_food_regen_per_second
        start_value = self._default_initial_food if initial_value is None else initial_value
        for patch in self._patches:
            px, py = patch.position
            dx = key[0] * self._cell_size - px
            dy = key[1] * self._cell_size - py
            if math.hypot(dx, dy) <= patch.radius:
                max_food = patch.resource_per_cell
                regen = patch.regen_per_second
                start_value = patch.initial_resource
                break

        cell = FoodCell(value=start_value, max=max_food, regen_per_second=regen)
        self._food_cells[key] = cell
        return cell

    def _cell_key(self, position: Vector2) -> Tuple[int, int]:
        clamped_x = max(0.0, min(self._world_size, position.x))
        clamped_y = max(0.0, min(self._world_size, position.y))
        ix = max(0, min(self._max_index - 1, int(clamped_x // self._cell_size)))
        iy = max(0, min(self._max_index - 1, int(clamped_y // self._cell_size)))
        return (ix, iy)

    def _initialize_patches(self) -> None:
        if not self._patches:
            return

        for patch in self._patches:
            cx = int(patch.position[0] // self._cell_size)
            cy = int(patch.position[1] // self._cell_size)
            radius_cells = int(max(1, patch.radius // self._cell_size))
            for dx in range(-radius_cells, radius_cells + 1):
                for dy in range(-radius_cells, radius_cells + 1):
                    key = (cx + dx, cy + dy)
                    cell = FoodCell(
                        value=patch.initial_resource,
                        max=patch.resource_per_cell,
                        regen_per_second=patch.regen_per_second,
                    )
                    self._food_cells[key] = cell
