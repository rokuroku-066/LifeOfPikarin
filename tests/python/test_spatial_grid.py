from __future__ import annotations

from pygame.math import Vector2

from terrarium.spatial_grid import SpatialGrid


def test_neighbor_query_matches_bruteforce():
    grid = SpatialGrid(cell_size=2.5)
    positions = [
        Vector2(0, 0),
        Vector2(1, 1),
        Vector2(3, 0.5),
        Vector2(6, 6),
    ]
    for idx, pos in enumerate(positions):
        grid.insert(idx, pos)

    center = Vector2(1, 1)
    radius = 3.0
    neighbors = grid.get_neighbors(center, radius)
    brute = [idx for idx, pos in enumerate(positions) if (pos - center).length_squared() <= radius * radius]
    found_ids = sorted([entry.id for entry in neighbors])
    assert found_ids == sorted(brute)
