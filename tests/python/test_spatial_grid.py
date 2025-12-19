from __future__ import annotations

from pygame.math import Vector2

from terrarium.agent import Agent, AgentState
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


def test_collect_neighbors_returns_agents_and_offsets():
    grid = SpatialGrid(cell_size=2.5)
    agent_positions = [
        Vector2(0, 0),
        Vector2(1, 1),
        Vector2(3, 0.5),
        Vector2(6, 6),
    ]
    agents = []
    for idx, pos in enumerate(agent_positions):
        agent = Agent(
            id=idx,
            generation=0,
            group_id=-1,
            position=pos,
            velocity=Vector2(),
            energy=10.0,
            age=0.0,
            state=AgentState.IDLE,
        )
        agents.append(agent)
        grid.insert(agent.id, agent.position, agent)

    center = Vector2(1, 1)
    radius = 3.0
    out_agents: list[Agent] = []
    out_offsets: list[Vector2] = []

    grid.collect_neighbors(center, radius, out_agents, out_offsets, exclude_id=agents[1].id)

    brute = [
        a.id
        for a in agents
        if a.id != agents[1].id and (a.position - center).length_squared() <= radius * radius
    ]
    assert sorted(a.id for a in out_agents) == sorted(brute)
    assert len(out_agents) == len(out_offsets)
    for agent, offset in zip(out_agents, out_offsets):
        assert (agent.position - center) == offset


def test_collect_neighbors_precomputed_clears_distance_buffer():
    grid = SpatialGrid(cell_size=2.0)
    radius = 1.6
    cell_offsets = grid.build_neighbor_cell_offsets(radius)
    agent = Agent(
        id=0,
        generation=0,
        group_id=-1,
        position=Vector2(0.0, 0.0),
        velocity=Vector2(),
        energy=10.0,
        age=0.0,
        state=AgentState.IDLE,
    )
    grid.insert(agent.id, agent.position, agent)

    out_agents: list[Agent] = []
    out_offsets: list[Vector2] = [Vector2(5, 5)]
    out_dist_sq: list[float] = [42.0]

    grid.collect_neighbors_precomputed(
        Vector2(0.5, 0.0),
        cell_offsets,
        radius * radius,
        out_agents,
        out_offsets,
        out_dist_sq=out_dist_sq,
    )

    assert len(out_agents) == 1
    assert len(out_offsets) == 1
    assert len(out_dist_sq) == 1
    assert out_dist_sq[0] == out_offsets[0].length_squared()

    grid.collect_neighbors_precomputed(
        Vector2(10.0, 10.0),
        cell_offsets,
        radius * radius,
        out_agents,
        out_offsets,
        out_dist_sq=out_dist_sq,
    )

    assert out_agents == []
    assert out_offsets == []
    assert out_dist_sq == []
