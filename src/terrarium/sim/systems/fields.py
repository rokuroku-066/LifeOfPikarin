from __future__ import annotations

import math
from typing import Set, TYPE_CHECKING

from pygame.math import Vector2

if TYPE_CHECKING:
    from ..core.world import World


def cell_key(world: World, position: Vector2) -> tuple[int, int]:
    return world._environment._cell_key(position)


def orthogonal_neighbor_keys(
    world: World, position: Vector2, base_key: tuple[int, int] | None = None
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
    if base_key is None:
        base_key = world._environment._cell_key(position)
    add_key = world._environment._add_key2
    right = add_key(base_key, 1, 0)
    left = add_key(base_key, -1, 0)
    up = add_key(base_key, 0, 1)
    down = add_key(base_key, 0, -1)
    return (right, left, up, down)


def food_gradient(world: World, position: Vector2, base_key: tuple[int, int] | None = None) -> Vector2:
    right_key, left_key, up_key, down_key = orthogonal_neighbor_keys(world, position, base_key)
    right = world._environment.peek_food(right_key)
    left = world._environment.peek_food(left_key)
    up = world._environment.peek_food(up_key)
    down = world._environment.peek_food(down_key)
    return Vector2(right - left, up - down)


def pheromone_gradient(
    world: World, group_id: int, position: Vector2, base_key: tuple[int, int] | None = None
) -> Vector2:
    right_key, left_key, up_key, down_key = orthogonal_neighbor_keys(world, position, base_key)
    right = world._environment.sample_pheromone(right_key, group_id)
    left = world._environment.sample_pheromone(left_key, group_id)
    up = world._environment.sample_pheromone(up_key, group_id)
    down = world._environment.sample_pheromone(down_key, group_id)
    return Vector2(right - left, up - down)


def danger_gradient(world: World, position: Vector2, base_key: tuple[int, int] | None = None) -> Vector2:
    right_key, left_key, up_key, down_key = orthogonal_neighbor_keys(world, position, base_key)
    right = world._environment.sample_danger(right_key)
    left = world._environment.sample_danger(left_key)
    up = world._environment.sample_danger(up_key)
    down = world._environment.sample_danger(down_key)
    return Vector2(right - left, up - down)


def tick_environment(world: World, active_groups: Set[int]) -> None:
    env_dt = (
        world._config.environment_tick_interval
        if world._config.environment_tick_interval > 1e-6
        else world._config.time_step
    )
    world._environment_accumulator += world._config.time_step
    while world._environment_accumulator >= env_dt:
        world._environment.prune_pheromones(active_groups)
        world._environment.set_food_regen_multiplier(update_food_regen_noise(world, env_dt))
        world._environment.tick(env_dt)
        world._environment_accumulator -= env_dt


def update_food_regen_noise(world: World, env_dt: float) -> float:
    config = world._config.environment
    amplitude = max(0.0, float(config.food_regen_noise_amplitude))
    interval = float(config.food_regen_noise_interval_seconds)
    smooth = max(0.0, float(config.food_regen_noise_smooth_seconds))

    if amplitude <= 1e-9 or interval <= 1e-6:
        world._food_regen_noise_multiplier = 1.0
        world._food_regen_noise_target = 1.0
        world._food_regen_noise_time_to_next_sample = 0.0
        return world._food_regen_noise_multiplier

    low = max(0.0, 1.0 - amplitude)
    high = 1.0 + amplitude

    if world._food_regen_noise_time_to_next_sample <= 0.0:
        world._food_regen_noise_time_to_next_sample = interval

    world._food_regen_noise_time_to_next_sample -= env_dt
    while world._food_regen_noise_time_to_next_sample <= 0.0:
        world._food_regen_noise_target = world._climate_rng.next_range(low, high)
        world._food_regen_noise_time_to_next_sample += interval
        if smooth <= 1e-6:
            world._food_regen_noise_multiplier = world._food_regen_noise_target

    if smooth > 1e-6:
        alpha = 1.0 - math.exp(-env_dt / smooth)
        world._food_regen_noise_multiplier += (
            world._food_regen_noise_target - world._food_regen_noise_multiplier
        ) * alpha

    world._food_regen_noise_multiplier = max(low, min(high, world._food_regen_noise_multiplier))
    return world._food_regen_noise_multiplier


def apply_field_events(world: World) -> None:
    for cell_key, amt in world._pending_food.items():
        world._environment.add_food(cell_key, amt)
    for cell_key, amt in world._pending_danger.items():
        world._environment.add_danger(cell_key, amt)
    for (cell_key, gid), amt in world._pending_pheromone.items():
        world._environment.add_pheromone(cell_key, gid, amt)
    world._pending_food.clear()
    world._pending_danger.clear()
    world._pending_pheromone.clear()
