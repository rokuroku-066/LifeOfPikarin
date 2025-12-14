from __future__ import annotations

from pygame.math import Vector2

from terrarium.config import EnvironmentConfig
from terrarium.environment import EnvironmentGrid


def test_pheromone_diffusion_is_bounded_and_fades():
    config = EnvironmentConfig(
        pheromone_diffusion_rate=0.5,
        pheromone_decay_rate=0.2,
        danger_diffusion_rate=0.5,
        danger_decay_rate=0.5,
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
