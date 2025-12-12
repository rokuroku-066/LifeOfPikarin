from __future__ import annotations

from terrarium.spatial_grid import SpatialGrid
from terrarium.vector import Vec2


def test_neighbor_query_matches_bruteforce():
    grid = SpatialGrid(cell_size=2.5)
    positions = [
        Vec2(0, 0),
        Vec2(1, 1),
        Vec2(3, 0.5),
        Vec2(6, 6),
    ]
    for idx, pos in enumerate(positions):
        grid.insert(idx, pos)

    center = Vec2(1, 1)
    radius = 3.0
    neighbors = grid.get_neighbors(center, radius)
    brute = [idx for idx, pos in enumerate(positions) if (pos - center).length_squared() <= radius * radius]
    found_ids = sorted([entry.id for entry in neighbors])
    assert found_ids == sorted(brute)
