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
