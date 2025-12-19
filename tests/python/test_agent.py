from __future__ import annotations

from pygame.math import Vector2

from terrarium.agent import Agent, AgentState, AgentTraits
from terrarium.config import EnvironmentConfig, SimulationConfig, SpeciesConfig
from terrarium.world import World


def _make_agent(agent_id: int) -> Agent:
    return Agent(
        id=agent_id,
        generation=0,
        group_id=0,
        position=Vector2(),
        velocity=Vector2(),
        energy=5.0,
        age=0.0,
        state=AgentState.WANDER,
    )


def test_agent_and_traits_use_slots_and_isolate_defaults():
    traits = AgentTraits()
    agent_a = _make_agent(1)
    agent_b = _make_agent(2)

    assert not hasattr(traits, "__dict__")
    assert not hasattr(agent_a, "__dict__")
    assert hasattr(AgentTraits, "__slots__")
    assert hasattr(Agent, "__slots__")

    assert agent_a.traits is not agent_b.traits
    agent_a.wander_dir.x = 1.5
    assert agent_b.wander_dir.x == 0.0


def test_slots_support_snapshot_serialization():
    config = SimulationConfig(
        seed=404,
        time_step=1.0,
        initial_population=2,
        max_population=2,
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=1.0,
            adult_age=0.0,
        ),
    )
    world = World(config)

    assert all(not hasattr(agent, "__dict__") for agent in world.agents)
    snapshot = world.snapshot(0)

    assert snapshot.metrics.population == len(world.agents)
    assert len(snapshot.agents) == len([agent for agent in world.agents if agent.alive])
    assert snapshot.agents[0]["id"] == world.agents[0].id
