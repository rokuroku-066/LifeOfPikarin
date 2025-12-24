from __future__ import annotations

from pygame.math import Vector2

from terrarium.sim.core.config import EnvironmentConfig, ResourcePatchConfig
from terrarium.sim.core.environment import EnvironmentGrid


def test_pheromone_diffusion_is_bounded_and_fades():
    config = EnvironmentConfig(
        pheromone_diffusion_rate=0.5,
        pheromone_decay_rate=0.2,
    )
    env = EnvironmentGrid(cell_size=1.0, config=config, world_size=4.0)

    env.add_pheromone(Vector2(3.9, 3.9), group_id=1, amount=5.0)

    # Diffusion should stay within world bounds and not exceed grid cell count.
    for _ in range(3):
        env.tick(1.0)
        assert all(0 <= k[0] < env._max_index and 0 <= k[1] < env._max_index for k in env._pheromone_field)
        assert len(env._pheromone_field) <= env._max_index ** 2

    # With decay > 0 the field should eventually dissipate.
    for _ in range(120):
        env.tick(1.0)
        if not env._pheromone_field:
            break
    assert len(env._pheromone_field) == 0


def test_prune_pheromones_limits_groups_and_decay():
    config = EnvironmentConfig(
        pheromone_diffusion_rate=0.25,
        pheromone_decay_rate=1.0,
    )
    env = EnvironmentGrid(cell_size=1.0, config=config, world_size=3.0)

    for gid in range(5):
        for x in range(-1, 5):
            for y in range(-1, 5):
                env.add_pheromone(Vector2(x, y), group_id=gid, amount=1.0)

    env.prune_pheromones({1, 2})

    assert all(k[2] in {1, 2} for k in env._pheromone_field)
    max_cells = env._max_index ** 2
    assert len(env._pheromone_field) <= max_cells * 2

    for _ in range(6):
        env.tick(1.0)

    assert len(env._pheromone_field) == 0


def test_food_diffusion_stays_within_bounds():
    config = EnvironmentConfig(
        food_diffusion_rate=0.5,
        food_decay_rate=0.0,
        resource_patches=[
            ResourcePatchConfig(
                position=(-2.0, -2.0),
                radius=4.0,
                resource_per_cell=3.0,
                regen_per_second=0.0,
                initial_resource=3.0,
            )
        ],
    )
    env = EnvironmentGrid(cell_size=1.0, config=config, world_size=3.0)

    assert all(0 <= x < env._max_index and 0 <= y < env._max_index for x, y in env._food_cells)

    env.add_food(Vector2(2.9, 2.9), amount=5.0)

    for _ in range(5):
        env.tick(1.0)
        assert all(0 <= x < env._max_index and 0 <= y < env._max_index for x, y in env._food_cells)
        assert len(env._food_cells) <= env._max_index**2
