from __future__ import annotations

from pygame.math import Vector2
from pytest import approx

from terrarium.agent import Agent, AgentState
from terrarium.config import EnvironmentConfig, FeedbackConfig, SimulationConfig, SpeciesConfig
from terrarium.world import World


def run_steps(config: SimulationConfig, steps: int):
    world = World(config)
    snapshots = []
    for tick in range(steps):
        metrics = world.step(tick)
        snapshots.append((metrics.population, metrics.births, metrics.deaths, round(metrics.average_energy, 4)))
    return snapshots


def test_deterministic_steps():
    config = SimulationConfig(seed=1234, initial_population=50, max_population=120)
    result_a = run_steps(config, 50)
    # recreate config to ensure RNG resets
    config_b = SimulationConfig(seed=1234, initial_population=50, max_population=120)
    result_b = run_steps(config_b, 50)
    assert result_a == result_b


def test_snapshot_contains_metadata_and_agent_signals():
    config = SimulationConfig(
        seed=7,
        time_step=0.5,
        world_size=42.0,
        initial_population=1,
        species=SpeciesConfig(
            base_speed=1.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
    )
    world = World(config)
    world.agents[0].velocity = Vector2(1.0, 0.0)
    world.agents[0].heading = 0.25

    world.step(0)
    snapshot = world.snapshot(1)

    assert snapshot.world.size == approx(42.0)
    assert snapshot.metadata.world_size == approx(42.0)
    assert snapshot.metadata.sim_dt == approx(0.5)
    assert snapshot.metadata.tick_rate == approx(2.0)
    assert snapshot.metadata.seed == 7

    assert snapshot.metrics.population == len(world.agents)
    payload = snapshot.agents[0]
    for key in ["id", "x", "y", "vx", "vy", "group"]:
        assert key in payload
    assert payload["heading"] == approx(world.agents[0].heading)
    assert payload["speed"] == approx(Vector2(payload["vx"], payload["vy"]).length())
    assert payload["behavior_state"]
    assert payload["is_alive"]


def test_heading_persists_when_still():
    config = SimulationConfig(
        seed=9,
        time_step=1.0,
        initial_population=1,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
    )
    world = World(config)
    world.agents[0].heading = 1.23
    world.agents[0].velocity = Vector2()

    world.step(0)
    snapshot = world.snapshot(1)

    assert world.agents[0].heading == approx(1.23)
    assert snapshot.agents[0]["heading"] == approx(1.23)


def test_population_bounds_respected():
    config = SimulationConfig(seed=7, initial_population=20, max_population=25)
    world = World(config)
    for tick in range(200):
        world.step(tick)
        assert len(world.agents) <= config.max_population


def test_disease_death_returns_zero_births():
    config = SimulationConfig(
        seed=99,
        initial_population=1,
        feedback=FeedbackConfig(
            local_density_soft_cap=0,
            disease_probability_per_neighbor=1.0,
        ),
    )
    world = World(config)
    agent = world.agents[0]

    births = world._apply_life_cycle(agent, neighbor_count=100, same_group_neighbors=0, can_create_groups=False)

    assert births == 0
    assert not agent.alive
    assert world._pending_food  # type: ignore[attr-defined]


def test_lonely_agent_switches_to_nearby_majority():
    config = SimulationConfig(
        seed=5,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=2.0,
            group_switch_chance=1.0,
            group_adoption_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=0,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=1,
                generation=0,
                group_id=1,
                position=Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=2,
                generation=0,
                group_id=1,
                position=Vector2(1.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 3
    world._refresh_index_map()

    for tick in range(3):
        world.step(tick)

    assert world.agents[0].group_id == 1
    assert world.agents[0].group_lonely_seconds == 0.0


def test_lonely_agent_does_not_switch_without_threshold_neighbors():
    config = SimulationConfig(
        seed=6,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=10.0,
            group_switch_chance=1.0,
            group_detach_new_group_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=2,
            group_adoption_chance=1.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=10,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=11,
                generation=0,
                group_id=1,
                position=Vector2(1.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=12,
                generation=0,
                group_id=1,
                position=Vector2(20.0, 20.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=13,
                generation=0,
                group_id=1,
                position=Vector2(20.0, 23.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 14
    world._next_group_id = 3
    world._refresh_index_map()

    for tick in range(2):
        world.step(tick)

    assert world.agents[0].group_id == 0
    assert world.agents[0].group_lonely_seconds > 0.0


def test_lonely_agent_switches_when_neighbor_threshold_met():
    config = SimulationConfig(
        seed=8,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=10.0,
            group_switch_chance=1.0,
            group_detach_new_group_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
            group_adoption_chance=1.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=20,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=21,
                generation=0,
                group_id=2,
                position=Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=22,
                generation=0,
                group_id=2,
                position=Vector2(1.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 23
    world._next_group_id = 3
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 2
    assert world.agents[0].group_lonely_seconds == 0.0


def test_small_group_adoption_relaxes_threshold():
    config = SimulationConfig(
        seed=42,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0
        ),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=10.0,
            group_switch_chance=1.0,
            group_detach_new_group_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=2,
            group_adoption_chance=1.0,
            group_adoption_small_group_bonus=1.5,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=30,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=31,
                generation=0,
                group_id=2,
                position=Vector2(0.8, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 32
    world._next_group_id = 3
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 2
    assert world.agents[0].group_lonely_seconds == 0.0


def test_dense_group_spawns_clan_food():
    config = SimulationConfig(
        seed=101,
        time_step=1.0,
        initial_population=0,
        environment=EnvironmentConfig(
            food_per_cell=0.0,
            food_regen_per_second=0.0,
            food_consumption_rate=2.0,
            food_diffusion_rate=0.0,
            food_decay_rate=0.0,
            group_food_max_per_cell=10.0,
            group_food_decay_rate=0.0,
            group_food_diffusion_rate=0.0,
        ),
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=3.0,
            wander_jitter=0.0,
        ),
        feedback=FeedbackConfig(
            group_formation_warmup_seconds=0.0,
            group_cohesion_radius=1.5,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=10.0,
            group_switch_chance=0.0,
            group_cohesion_weight=0.0,
            group_adoption_neighbor_threshold=1,
            group_food_neighbor_threshold=1,
            group_food_spawn_chance=1.0,
            group_food_spawn_amount=4.0,
            stress_drain_per_neighbor=0.0,
            base_death_probability_per_second=0.0,
            age_death_probability_per_second=0.0,
            density_death_probability_per_neighbor_per_second=0.0,
            other_group_avoid_radius=0.0,
            other_group_avoid_weight=0.0,
            ally_separation_weight=0.0,
            other_group_separation_weight=0.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=100,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=1.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=101,
                generation=0,
                group_id=0,
                position=Vector2(0.4, 0.0),
                velocity=Vector2(),
                energy=1.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 102
    world._next_group_id = 1
    world._refresh_index_map()

    world.step(0)

    own_food = world._environment.sample_group_food(Vector2(0.0, 0.0), 0)
    rival_food = world._environment.sample_group_food(Vector2(0.0, 0.0), 1)

    assert own_food == approx(8.0)
    assert rival_food == approx(0.0)


def test_clan_food_only_feeds_owner_group():
    config = SimulationConfig(
        seed=202,
        time_step=1.0,
        initial_population=0,
        environment=EnvironmentConfig(
            food_per_cell=0.0,
            food_regen_per_second=0.0,
            food_consumption_rate=2.0,
            food_diffusion_rate=0.0,
            food_decay_rate=0.0,
            group_food_max_per_cell=10.0,
            group_food_decay_rate=0.0,
            group_food_diffusion_rate=0.0,
        ),
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=3.0,
            wander_jitter=0.0,
        ),
        feedback=FeedbackConfig(
            group_formation_warmup_seconds=0.0,
            group_cohesion_radius=1.5,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=10.0,
            group_switch_chance=0.0,
            group_cohesion_weight=0.0,
            group_adoption_neighbor_threshold=1,
            group_food_neighbor_threshold=1,
            group_food_spawn_chance=1.0,
            group_food_spawn_amount=4.0,
            stress_drain_per_neighbor=0.0,
            base_death_probability_per_second=0.0,
            age_death_probability_per_second=0.0,
            density_death_probability_per_neighbor_per_second=0.0,
            other_group_avoid_radius=0.0,
            other_group_avoid_weight=0.0,
            ally_separation_weight=0.0,
            other_group_separation_weight=0.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=110,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=1.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=111,
                generation=0,
                group_id=0,
                position=Vector2(0.3, 0.0),
                velocity=Vector2(),
                energy=1.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=112,
                generation=0,
                group_id=1,
                position=Vector2(0.15, 0.0),
                velocity=Vector2(),
                energy=1.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 113
    world._next_group_id = 2
    world._refresh_index_map()

    world.step(0)
    world.step(1)

    group0_energy = [a.energy for a in world.agents if a.group_id == 0]
    group1_energy = [a.energy for a in world.agents if a.group_id == 1]

    assert all(val > 1.9 for val in group0_energy)
    assert all(val == approx(1.0) for val in group1_energy)


def test_close_allies_reset_lonely_timer():
    config = SimulationConfig(
        seed=11,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=2.0,
            group_switch_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=10,
                generation=0,
                group_id=2,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
                group_lonely_seconds=1.5,
            ),
            Agent(
                id=11,
                generation=0,
                group_id=2,
                position=Vector2(0.3, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 12
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 2
    assert world.agents[0].group_lonely_seconds == 0.0


def test_lonely_group_spawns_new_group_instead_of_ungrouped():
    config = SimulationConfig(
        seed=17,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=1.0,
            group_switch_chance=0.0,
            group_detach_new_group_chance=1.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.append(
        Agent(
            id=0,
            generation=0,
            group_id=0,
            position=Vector2(0.0, 0.0),
            velocity=Vector2(),
            energy=10.0,
            age=5.0,
            state=AgentState.WANDER,
        )
    )
    world._next_id = 1
    world._next_group_id = 1
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 1


def test_split_recruits_neighbors_and_sets_cooldown():
    config = SimulationConfig(
        seed=101,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=4.0,
            wander_jitter=0.0,
        ),
        feedback=FeedbackConfig(
            group_formation_warmup_seconds=0.0,
            group_split_neighbor_threshold=1,
            group_split_chance=1.0,
            group_split_size_bonus_per_neighbor=0.0,
            group_split_chance_max=1.0,
            group_split_size_stress_weight=0.0,
            group_split_stress_threshold=0.0,
            group_split_new_group_chance=1.0,
            group_split_recruitment_count=2,
            group_merge_cooldown_seconds=2.0,
            group_cohesion_weight=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=500,
                generation=0,
                group_id=5,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
                stress=1.0,
            ),
            Agent(
                id=501,
                generation=0,
                group_id=5,
                position=Vector2(0.4, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=502,
                generation=0,
                group_id=5,
                position=Vector2(-0.4, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 503
    world._next_group_id = 6
    world._refresh_index_map()

    world.step(0)

    new_group = world.agents[0].group_id
    assert new_group >= 0 and new_group != 5
    recruited = [a for a in world.agents[1:] if a.group_id == new_group]
    assert len(recruited) >= 1
    assert world.agents[0].group_cooldown == approx(config.feedback.group_merge_cooldown_seconds)


def test_adoption_guard_respects_local_allies():
    config = SimulationConfig(
        seed=202,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=3.0,
            wander_jitter=0.0,
        ),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=1.0,
            group_switch_chance=1.0,
            group_adoption_neighbor_threshold=1,
            group_adoption_chance=1.0,
            group_adoption_guard_min_allies=2,
            group_merge_cooldown_seconds=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=600,
                generation=0,
                group_id=1,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=601,
                generation=0,
                group_id=1,
                position=Vector2(0.6, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=602,
                generation=0,
                group_id=1,
                position=Vector2(-0.6, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=603,
                generation=0,
                group_id=2,
                position=Vector2(0.0, 1.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=604,
                generation=0,
                group_id=2,
                position=Vector2(0.0, 1.3),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 605
    world._next_group_id = 3
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 1


def test_group_merge_cooldown_blocks_immediate_adoption():
    config = SimulationConfig(
        seed=303,
        time_step=0.5,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=3.0,
            wander_jitter=0.0,
        ),
        feedback=FeedbackConfig(
            group_adoption_neighbor_threshold=1,
            group_adoption_chance=1.0,
            group_adoption_guard_min_allies=0,
            group_merge_cooldown_seconds=1.0,
            group_formation_warmup_seconds=0.0,
            group_cohesion_weight=0.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=700,
                generation=0,
                group_id=1,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
                group_cooldown=0.6,
            ),
            Agent(
                id=701,
                generation=0,
                group_id=2,
                position=Vector2(0.6, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=702,
                generation=0,
                group_id=2,
                position=Vector2(-0.6, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 703
    world._next_group_id = 3
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 1
    assert world.agents[0].group_cooldown == approx(0.1)
    assert world.agents[0].group_lonely_seconds == approx(config.time_step)


def _make_reflective_config(base_speed: float = 50.0) -> SimulationConfig:
    return SimulationConfig(
        time_step=1.0,
        world_size=10.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=base_speed,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
    )


def test_reflective_boundary_flips_velocity_and_position():
    config = _make_reflective_config(base_speed=10.0)
    world = World(config)
    world.agents.append(
        Agent(
            id=0,
            generation=0,
            group_id=-1,
            position=Vector2(9.5, 5.0),
            velocity=Vector2(2.0, 0.0),
            energy=10.0,
            age=1.0,
            state=AgentState.WANDER,
        )
    )
    world._next_id = 1
    world._refresh_index_map()

    world.step(0)

    agent = world.agents[0]
    assert 0.0 <= agent.position.x <= config.world_size
    assert 0.0 <= agent.position.y <= config.world_size
    assert agent.position.x == approx(8.5)
    assert agent.position.y == approx(5.0)
    assert agent.velocity.x == approx(-2.0)
    assert agent.velocity.y == approx(0.0)


def test_reflective_boundary_handles_multiple_crossings_in_one_tick():
    config = _make_reflective_config()
    world = World(config)
    world.agents.append(
        Agent(
            id=5,
            generation=0,
            group_id=-1,
            position=Vector2(5.0, 5.0),
            velocity=Vector2(35.0, -35.0),
            energy=10.0,
            age=1.0,
            state=AgentState.WANDER,
        )
    )
    world._next_id = 6
    world._refresh_index_map()

    world.step(0)

    agent = world.agents[0]
    assert 0.0 <= agent.position.x <= config.world_size
    assert 0.0 <= agent.position.y <= config.world_size
    assert agent.position.x == approx(0.0)
    assert agent.position.y == approx(10.0)
    assert agent.velocity.x == approx(-35.0)
    assert agent.velocity.y == approx(35.0)


def test_detach_radius_separate_from_cohesion():
    config = SimulationConfig(
        seed=21,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=4.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=2.0,
            group_detach_radius=4.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=1.0,
            group_switch_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=20,
                generation=0,
                group_id=3,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=21,
                generation=0,
                group_id=3,
                position=Vector2(3.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 22
    world._refresh_index_map()

    world.step(0)
    world.step(1)

    assert world.agents[0].group_id == 3
    assert world.agents[0].group_lonely_seconds == 0.0


def test_boundary_avoidance_pushes_agents_inward():
    config = SimulationConfig(
        seed=3,
        time_step=0.5,
    world_size=10.0,
    boundary_margin=2.0,
    boundary_avoidance_weight=1.0,
    boundary_turn_weight=1.0,
    initial_population=0,
    max_population=1,
    environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
    species=SpeciesConfig(
        base_speed=4.0,
            max_acceleration=10.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=1.0,
            adult_age=0.0,
        ),
        feedback=FeedbackConfig(
            local_density_soft_cap=0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
        ),
    )
    world = World(config)
    world.agents.append(
        Agent(
            id=30,
            generation=0,
            group_id=-1,
            position=Vector2(0.2, 5.0),
            velocity=Vector2(),
            energy=5.0,
            age=1.0,
            state=AgentState.WANDER,
        )
    )
    world._next_id = 31
    world._refresh_index_map()

    world.step(0)

    agent = world.agents[0]
    assert agent.velocity.x > 0.0
    assert abs(agent.velocity.y) < agent.velocity.x * 0.2  # 進行方向が内側寄り
    assert agent.position.x > 0.2
    assert abs(agent.position.y - 5.0) < 0.2  # 壁離れに集中し縦方向に流れにくい


def test_personal_space_pushes_when_too_close():
    config = SimulationConfig(
        seed=42,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=1.0, max_acceleration=10.0, metabolism_per_second=0.0, vision_radius=2.0, wander_jitter=0.0),
        feedback=FeedbackConfig(
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
            personal_space_radius=1.0,
            personal_space_weight=2.0,
            group_split_neighbor_threshold=10,
            group_split_chance=0.0,
            group_mutation_chance=0.0,
        ),
        boundary_margin=0.0,
    )
    world = World(config)
    agent = Agent(
        id=1,
        generation=0,
        group_id=-1,
        position=Vector2(0.0, 0.0),
        velocity=Vector2(),
        energy=5.0,
        age=1.0,
        state=AgentState.WANDER,
    )
    other = Agent(
        id=2,
        generation=0,
        group_id=-1,
        position=Vector2(0.2, 0.0),
        velocity=Vector2(),
        energy=5.0,
        age=1.0,
        state=AgentState.WANDER,
    )
    desired, sensed = world._compute_desired_velocity(agent, [other], [Vector2(0.2, 0.0)])
    assert desired.x < 0.0  # 押し返される
    # ほぼ一直線の押し返しになることを確認（y成分が小さい）
    assert abs(desired.y) < abs(desired.x) * 0.25
    assert not sensed


def test_other_group_separation_weight_pushes_harder_than_allies():
    config = SimulationConfig(
        seed=13,
        time_step=1.0,
        initial_population=0,
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=4.0, wander_jitter=0.0),
        feedback=FeedbackConfig(
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
            ally_separation_weight=0.2,
            other_group_separation_weight=1.4,
            other_group_avoid_radius=0.0,
            other_group_avoid_weight=0.0,
        ),
    )
    world = World(config)
    agent = Agent(
        id=100,
        generation=0,
        group_id=7,
        position=Vector2(0.0, 0.0),
        velocity=Vector2(),
        energy=5.0,
        age=5.0,
        state=AgentState.WANDER,
    )
    ally = Agent(
        id=101,
        generation=0,
        group_id=7,
        position=Vector2(1.0, 0.0),
        velocity=Vector2(),
        energy=5.0,
        age=5.0,
        state=AgentState.WANDER,
    )
    rival = Agent(
        id=102,
        generation=0,
        group_id=3,
        position=Vector2(-1.0, 0.0),
        velocity=Vector2(),
        energy=5.0,
        age=5.0,
        state=AgentState.WANDER,
    )
    separation = world._separation(agent, [ally, rival], [Vector2(1.0, 0.0), Vector2(-1.0, 0.0)])

    assert separation.x > 0.9  # 強い他グループ押し出しで右向き
    assert abs(separation.y) < 1e-6


def test_intergroup_avoidance_applies_without_triggering_flee():
    config = SimulationConfig(
        seed=23,
        time_step=1.0,
        initial_population=0,
        boundary_margin=0.0,
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
        species=SpeciesConfig(
            base_speed=2.0,
            max_acceleration=10.0,
            metabolism_per_second=0.0,
            vision_radius=6.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=12.0,
            adult_age=0.0,
        ),
        feedback=FeedbackConfig(
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
            ally_separation_weight=0.0,
            other_group_separation_weight=0.0,
            other_group_avoid_radius=6.0,
            other_group_avoid_weight=1.0,
        ),
    )
    world = World(config)
    agent = Agent(
        id=200,
        generation=0,
        group_id=1,
        position=Vector2(0.0, 0.0),
        velocity=Vector2(),
        energy=8.0,
        age=5.0,
        state=AgentState.WANDER,
    )
    rival = Agent(
        id=201,
        generation=0,
        group_id=2,
        position=Vector2(3.0, 0.0),
        velocity=Vector2(),
        energy=8.0,
        age=5.0,
        state=AgentState.WANDER,
    )

    desired, sensed = world._compute_desired_velocity(agent, [rival], [Vector2(3.0, 0.0)])

    assert desired.x < 0.0  # 異グループから離れる
    assert abs(desired.y) < 1e-6
    assert agent.state == AgentState.WANDER
    assert not sensed


def test_ally_cohesion_weight_scales_pull():
    base_feedback = dict(
        group_cohesion_weight=1.0,
        group_formation_warmup_seconds=0.0,
        group_adoption_neighbor_threshold=1,
        ally_separation_weight=0.0,
        other_group_separation_weight=0.0,
        other_group_avoid_weight=0.0,
        other_group_avoid_radius=0.0,
    )
    shared_env = EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0)
    species = SpeciesConfig(
        base_speed=1.0,
        max_acceleration=10.0,
        metabolism_per_second=0.0,
        vision_radius=4.0,
        wander_jitter=0.0,
        reproduction_energy_threshold=12.0,
        adult_age=0.0,
    )
    config_low = SimulationConfig(
        seed=31,
        time_step=1.0,
        initial_population=0,
        boundary_margin=0.0,
        environment=shared_env,
        species=species,
        feedback=FeedbackConfig(ally_cohesion_weight=1.0, **base_feedback),
    )
    config_high = SimulationConfig(
        seed=32,
        time_step=1.0,
        initial_population=0,
        boundary_margin=0.0,
        environment=shared_env,
        species=species,
        feedback=FeedbackConfig(ally_cohesion_weight=2.0, **base_feedback),
    )

    def compute_desired(cfg):
        world = World(cfg)
        agent = Agent(
            id=300,
            generation=0,
            group_id=5,
            position=Vector2(0.0, 0.0),
            velocity=Vector2(),
            energy=15.0,
            age=25.0,
            state=AgentState.WANDER,
        )
        ally = Agent(
            id=301,
            generation=0,
            group_id=5,
            position=Vector2(1.0, 0.0),
            velocity=Vector2(),
            energy=15.0,
            age=25.0,
            state=AgentState.WANDER,
        )
        desired, _ = world._compute_desired_velocity(agent, [ally], [Vector2(1.0, 0.0)])
        return desired

    desired_low = compute_desired(config_low)
    desired_high = compute_desired(config_high)

    assert desired_high.x > desired_low.x
    assert desired_high.y == approx(desired_low.y)


def test_group_split_probability_scales_with_local_size():
    config = SimulationConfig(
        seed=23,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=4.0,
            wander_jitter=0.0,
        ),
        feedback=FeedbackConfig(
            group_formation_warmup_seconds=0.0,
            group_split_neighbor_threshold=1,
            group_split_chance=0.0,
            group_split_size_bonus_per_neighbor=1.0,
            group_split_chance_max=1.0,
            group_split_size_stress_weight=1.0,
            group_split_stress_threshold=0.5,
            group_split_new_group_chance=1.0,
            group_cohesion_weight=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=400,
                generation=0,
                group_id=0,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=401,
                generation=0,
                group_id=0,
                position=Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=402,
                generation=0,
                group_id=0,
                position=Vector2(-0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=5.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 403
    world._next_group_id = 1
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id not in (world._UNGROUPED, 0)
