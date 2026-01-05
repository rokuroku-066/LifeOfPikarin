from __future__ import annotations

from dataclasses import fields as dataclass_fields

from pygame.math import Vector2
from pytest import approx

from terrarium.sim.core.agent import Agent, AgentState, AgentTraits
from terrarium.sim.core.config import (
    AppearanceConfig,
    EnvironmentConfig,
    EvolutionClampConfig,
    EvolutionConfig,
    FeedbackConfig,
    load_config,
    SimulationConfig,
    SpeciesConfig,
)
from terrarium.sim.core.environment import FoodCell
from terrarium.sim.core.rng import DeterministicRng
from terrarium.sim.core.world import World, _APPEARANCE_RNG_SALT, _TRAIT_RNG_SALT, _derive_stream_seed
from terrarium.sim.systems import fields as fields_system, lifecycle, steering
from terrarium.sim.utils.math2d import _clamp_value


def run_steps(config: SimulationConfig, steps: int):
    world = World(config)
    snapshots = []
    for tick in range(steps):
        metrics = world.step(tick)
        snapshots.append((metrics.population, metrics.births, metrics.deaths, round(metrics.average_energy, 4)))
    return snapshots


def make_static_config(seed: int = 1) -> SimulationConfig:
    config = SimulationConfig(
        seed=seed,
        time_step=1.0,
        initial_population=0,
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=1.0,
            adult_age=0.0,
            initial_age_min=1.0,
            initial_age_max=1.0,
        ),
    )
    feedback = config.feedback
    feedback.reproduction_base_chance = 0.0
    feedback.base_death_probability_per_second = 0.0
    feedback.age_death_probability_per_second = 0.0
    feedback.density_death_probability_per_neighbor_per_second = 0.0
    feedback.disease_probability_per_neighbor = 0.0
    feedback.stress_drain_per_neighbor = 0.0
    feedback.group_switch_chance = 0.0
    feedback.group_detach_new_group_chance = 0.0
    feedback.group_formation_chance = 0.0
    feedback.group_split_chance = 0.0
    feedback.group_split_new_group_chance = 0.0
    feedback.group_birth_seed_chance = 0.0
    feedback.group_mutation_chance = 0.0
    feedback.group_cohesion_weight = 0.0
    feedback.group_cohesion_radius = 0.0
    feedback.group_adoption_chance = 0.0
    feedback.group_adoption_small_group_bonus = 0.0
    feedback.group_adoption_guard_min_allies = 0
    feedback.group_adoption_neighbor_threshold = 0
    feedback.group_split_recruitment_count = 0
    feedback.group_seek_weight = 0.0
    feedback.group_seek_radius = 0.0
    feedback.other_group_avoid_weight = 0.0
    feedback.other_group_avoid_radius = 0.0
    feedback.min_separation_weight = 0.0
    feedback.personal_space_weight = 0.0
    feedback.ally_cohesion_weight = 0.0
    feedback.ally_separation_weight = 0.0
    feedback.other_group_separation_weight = 0.0
    feedback.group_base_attraction_weight = 0.0
    feedback.group_detach_after_seconds = 1000.0
    feedback.group_detach_close_neighbor_threshold = 0
    return config


def test_deterministic_steps():
    config = SimulationConfig(seed=1234, initial_population=50, max_population=120)
    result_a = run_steps(config, 50)
    # recreate config to ensure RNG resets
    config_b = SimulationConfig(seed=1234, initial_population=50, max_population=120)
    result_b = run_steps(config_b, 50)
    assert result_a == result_b


def test_feedback_config_excludes_removed_pressure_fields():
    names = {f.name for f in dataclass_fields(FeedbackConfig)}
    assert "global_population_pressure_start" not in names
    assert "global_population_pressure_slope" not in names
    assert "global_population_pressure_delay_seconds" not in names
    assert "group_food_spawn_chance" not in names
    assert "group_food_spawn_amount" not in names
    assert "group_food_neighbor_threshold" not in names
    assert "post_peak_min_groups" not in names
    assert "post_peak_max_groups" not in names
    assert "max_groups" not in names
    assert "post_peak_group_seed_size" not in names


def test_environment_config_excludes_group_food_fields():
    names = {f.name for f in dataclass_fields(EnvironmentConfig)}
    assert "group_food_max_per_cell" not in names
    assert "group_food_decay_rate" not in names
    assert "group_food_diffusion_rate" not in names


def test_load_config_ignores_removed_group_food_fields():
    config = load_config(
        {
            "environment": {
                "group_food_max_per_cell": 9.9,
                "group_food_decay_rate": 0.5,
                "group_food_diffusion_rate": 0.1,
            }
        }
    )
    env = config.environment
    assert not hasattr(env, "group_food_max_per_cell")
    assert env.food_per_cell == EnvironmentConfig().food_per_cell


def test_load_config_ignores_removed_group_cap_fields():
    config = load_config(
        {"feedback": {"post_peak_min_groups": 3, "post_peak_max_groups": 9, "max_groups": 12, "post_peak_group_seed_size": 5}}
    )
    feedback = config.feedback
    assert not hasattr(feedback, "max_groups")
    assert feedback.population_peak_threshold == FeedbackConfig().population_peak_threshold


def test_world_does_not_queue_group_food_spawns():
    config = SimulationConfig(seed=2025, initial_population=0)
    world = World(config)

    assert not hasattr(world, "_pending_group_food")
    assert not hasattr(world, "_maybe_spawn_group_food")


def test_deterministic_steps_with_evolution_enabled():
    evolution = EvolutionConfig(enabled=True, mutation_strength=0.03, lineage_mutation_chance=0.05)
    config = SimulationConfig(seed=2024, initial_population=40, max_population=120, evolution=evolution)
    result_a = run_steps(config, 40)
    config_b = SimulationConfig(
        seed=2024,
        initial_population=40,
        max_population=120,
        evolution=EvolutionConfig(**evolution.__dict__),
    )
    result_b = run_steps(config_b, 40)
    assert result_a == result_b


def test_bootstrap_traits_use_trait_rng_stream():
    clamp = EvolutionClampConfig(
        speed=(0.6, 1.4),
        metabolism=(0.7, 1.3),
        disease_resistance=(0.5, 1.5),
        fertility=(0.8, 1.2),
        sociality=(0.4, 1.0),
        territoriality=(0.9, 1.1),
        loyalty=(0.2, 0.8),
        founder=(0.3, 1.7),
        kin_bias=(0.1, 0.9),
    )
    config = SimulationConfig(
        seed=707,
        initial_population=3,
        evolution=EvolutionConfig(enabled=False, clamp=clamp),
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
    )
    world = World(config)
    trait_rng = DeterministicRng(_derive_stream_seed(config.seed, _TRAIT_RNG_SALT))

    for agent in world.agents:
        expected = AgentTraits(
            speed=trait_rng.next_range(*clamp.speed),
            metabolism=trait_rng.next_range(*clamp.metabolism),
            disease_resistance=trait_rng.next_range(*clamp.disease_resistance),
            fertility=trait_rng.next_range(*clamp.fertility),
            sociality=trait_rng.next_range(*clamp.sociality),
            territoriality=trait_rng.next_range(*clamp.territoriality),
            loyalty=trait_rng.next_range(*clamp.loyalty),
            founder=trait_rng.next_range(*clamp.founder),
            kin_bias=trait_rng.next_range(*clamp.kin_bias),
        )
        traits = agent.traits
        assert traits.speed == approx(expected.speed)
        assert traits.metabolism == approx(expected.metabolism)
        assert traits.disease_resistance == approx(expected.disease_resistance)
        assert traits.fertility == approx(expected.fertility)
        assert traits.sociality == approx(expected.sociality)
        assert traits.territoriality == approx(expected.territoriality)
        assert traits.loyalty == approx(expected.loyalty)
        assert traits.founder == approx(expected.founder)
        assert traits.kin_bias == approx(expected.kin_bias)


def test_traits_respect_clamp_after_births():
    evolution = EvolutionConfig(
        enabled=True,
        mutation_strength=0.2,
        lineage_mutation_chance=0.2,
        clamp=EvolutionClampConfig(
            speed=(0.9, 1.1),
            metabolism=(0.85, 1.2),
            disease_resistance=(0.7, 1.4),
            fertility=(0.6, 1.3),
        ),
    )
    config = SimulationConfig(
        seed=3030,
        initial_population=12,
        max_population=40,
        evolution=evolution,
        species=SpeciesConfig(
            base_speed=4.0,
            max_acceleration=10.0,
            metabolism_per_second=0.2,
            reproduction_energy_threshold=6.0,
            adult_age=1.0,
            initial_energy_fraction_of_threshold=2.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
        environment=EnvironmentConfig(food_per_cell=9.0, food_regen_per_second=1.0),
    )
    world = World(config)
    for tick in range(60):
        world.step(tick)
    clamp = evolution.clamp
    for agent in world.agents:
        assert clamp.speed[0] <= agent.traits.speed <= clamp.speed[1]
        assert clamp.metabolism[0] <= agent.traits.metabolism <= clamp.metabolism[1]
        assert clamp.disease_resistance[0] <= agent.traits.disease_resistance <= clamp.disease_resistance[1]
        assert clamp.fertility[0] <= agent.traits.fertility <= clamp.fertility[1]
        assert clamp.sociality[0] <= agent.traits.sociality <= clamp.sociality[1]
        assert clamp.territoriality[0] <= agent.traits.territoriality <= clamp.territoriality[1]
        assert clamp.loyalty[0] <= agent.traits.loyalty <= clamp.loyalty[1]
        assert clamp.founder[0] <= agent.traits.founder <= clamp.founder[1]
        assert clamp.kin_bias[0] <= agent.traits.kin_bias <= clamp.kin_bias[1]


def test_step_clamps_traits_at_entry():
    clamp = EvolutionClampConfig(
        speed=(0.8, 1.1),
        metabolism=(0.7, 1.0),
        disease_resistance=(0.6, 0.95),
        fertility=(0.5, 0.9),
        sociality=(0.4, 0.9),
        territoriality=(0.3, 0.9),
        loyalty=(0.2, 0.9),
        founder=(0.1, 0.8),
        kin_bias=(0.45, 0.75),
    )
    config = SimulationConfig(
        seed=6060,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
        evolution=EvolutionConfig(enabled=False, clamp=clamp),
        feedback=FeedbackConfig(
            reproduction_base_chance=0.0,
            base_death_probability_per_second=0.0,
            age_death_probability_per_second=0.0,
            density_death_probability_per_neighbor_per_second=0.0,
            group_split_chance=0.0,
        ),
    )
    world = World(config)
    world.agents.append(
        Agent(
            id=0,
            generation=0,
            group_id=World._UNGROUPED,
            position=Vector2(0.0, 0.0),
            velocity=Vector2(),
            energy=10.0,
            age=5.0,
            state=AgentState.WANDER,
            traits=AgentTraits(
                speed=1.5,
                metabolism=1.3,
                disease_resistance=1.2,
                fertility=1.4,
                sociality=1.5,
                territoriality=1.6,
                loyalty=1.7,
                founder=1.8,
                kin_bias=1.9,
            ),
        )
    )
    world._next_id = 1
    world._refresh_index_map()

    world.step(0)

    traits = world.agents[0].traits
    assert clamp.speed[0] <= traits.speed <= clamp.speed[1]
    assert clamp.metabolism[0] <= traits.metabolism <= clamp.metabolism[1]
    assert clamp.disease_resistance[0] <= traits.disease_resistance <= clamp.disease_resistance[1]
    assert clamp.fertility[0] <= traits.fertility <= clamp.fertility[1]
    assert clamp.sociality[0] <= traits.sociality <= clamp.sociality[1]
    assert clamp.territoriality[0] <= traits.territoriality <= clamp.territoriality[1]
    assert clamp.loyalty[0] <= traits.loyalty <= clamp.loyalty[1]
    assert clamp.founder[0] <= traits.founder <= clamp.founder[1]
    assert clamp.kin_bias[0] <= traits.kin_bias <= clamp.kin_bias[1]


def test_food_regen_noise_is_deterministic_and_bounded():
    environment = EnvironmentConfig(
        food_per_cell=0.0,
        food_regen_per_second=0.0,
        food_consumption_rate=0.0,
        food_regen_noise_amplitude=0.25,
        food_regen_noise_interval_seconds=2.0,
        food_regen_noise_smooth_seconds=0.0,
    )
    config = SimulationConfig(
        seed=4242,
        time_step=1.0,
        environment_tick_interval=0.0,
        initial_population=0,
        environment=environment,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
    )

    def run_regen_multipliers(cfg: SimulationConfig, steps: int) -> list[float]:
        world = World(cfg)
        multipliers: list[float] = []
        for tick in range(steps):
            world.step(tick)
            multipliers.append(world._environment.food_regen_multiplier)  # type: ignore[attr-defined]
        return multipliers

    multipliers_a = run_regen_multipliers(config, 20)
    config_b = SimulationConfig(**{**config.__dict__})
    multipliers_b = run_regen_multipliers(config_b, 20)

    assert multipliers_a == multipliers_b
    assert len({round(m, 6) for m in multipliers_a}) > 1
    assert all(0.75 <= m <= 1.25 for m in multipliers_a)


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
    for key in [
        "id",
        "x",
        "y",
        "vx",
        "vy",
        "group",
        "lineage_id",
        "generation",
        "trait_speed",
        "appearance_h",
        "appearance_s",
        "appearance_l",
    ]:
        assert key in payload
    assert payload["heading"] == approx(world.agents[0].heading)
    assert payload["speed"] == approx(Vector2(payload["vx"], payload["vy"]).length())
    assert payload["behavior_state"]
    assert payload["is_alive"]


def test_appearance_inheritance_is_deterministic_and_mutates():
    appearance = AppearanceConfig(
        base_h=50.0,
        base_s=1.0,
        base_l=0.83,
        mutation_chance=1.0,
        mutation_delta_h=12.0,
        mutation_delta_s=0.1,
        mutation_delta_l=0.1,
    )
    feedback = FeedbackConfig(
        reproduction_base_chance=1.0,
        base_death_probability_per_second=0.0,
        age_death_probability_per_second=0.0,
        density_death_probability_per_neighbor_per_second=0.0,
        disease_probability_per_neighbor=0.0,
        stress_drain_per_neighbor=0.0,
        group_switch_chance=0.0,
        group_detach_new_group_chance=0.0,
        group_formation_chance=0.0,
        group_split_chance=0.0,
        group_split_new_group_chance=0.0,
        group_birth_seed_chance=0.0,
        group_mutation_chance=0.0,
    )
    config = SimulationConfig(
        seed=21,
        time_step=1.0,
        initial_population=10,
        max_population=11,
        appearance=appearance,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=1.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=1.0,
            adult_age=0.0,
        ),
        feedback=feedback,
        evolution=EvolutionConfig(enabled=False),
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
    )
    world = World(config)
    parent = world.agents[0]
    mate = world.agents[1]
    parent.appearance_h = 350.0
    mate.appearance_h = 10.0

    births = lifecycle.apply_life_cycle(
        world,
        parent,
        neighbor_count=0,
        same_group_neighbors=0,
        can_create_groups=False,
        neighbors=[mate],
        neighbor_dist_sq=[0.01],
        paired_ids=set(),
        base_cell_key=world._cell_key(parent.position),
    )
    assert births == 1
    world._apply_births()

    assert len(world.agents) == 11
    child = next(agent for agent in world.agents if agent.id != parent.id and agent.generation == 1)
    assert parent.appearance_h == 350.0
    assert parent.appearance_s == appearance.base_s
    assert parent.appearance_l == appearance.base_l

    appearance_rng = DeterministicRng(_derive_stream_seed(config.seed, _APPEARANCE_RNG_SALT))
    appearance_rng.next_float()
    expected_h = (0.0 + appearance_rng.next_range(-appearance.mutation_delta_h, appearance.mutation_delta_h)) % 360
    expected_s = _clamp_value(
        appearance.base_s + appearance_rng.next_range(-appearance.mutation_delta_s, appearance.mutation_delta_s),
        0.0,
        1.0,
    )
    expected_l = _clamp_value(
        appearance.base_l + appearance_rng.next_range(-appearance.mutation_delta_l, appearance.mutation_delta_l),
        0.0,
        1.0,
    )
    assert child.appearance_h == approx(expected_h)
    assert child.appearance_s == approx(expected_s)
    assert child.appearance_l == approx(expected_l)

    config_b = SimulationConfig(**{**config.__dict__})
    world_b = World(config_b)
    parent_b = world_b.agents[0]
    mate_b = world_b.agents[1]
    parent_b.appearance_h = 350.0
    mate_b.appearance_h = 10.0
    births_b = lifecycle.apply_life_cycle(
        world_b,
        parent_b,
        neighbor_count=0,
        same_group_neighbors=0,
        can_create_groups=False,
        neighbors=[mate_b],
        neighbor_dist_sq=[0.01],
        paired_ids=set(),
        base_cell_key=world_b._cell_key(parent_b.position),
    )
    assert births_b == 1
    world_b._apply_births()
    child_b = next(agent for agent in world_b.agents if agent.id != world_b.agents[0].id and agent.generation == 1)
    assert child.appearance_h == approx(child_b.appearance_h)
    assert child.appearance_s == approx(child_b.appearance_s)
    assert child.appearance_l == approx(child_b.appearance_l)


def test_appearance_group_bias_clamps_hue_delta():
    appearance = AppearanceConfig(
        base_h=50.0,
        base_s=1.0,
        base_l=0.83,
        mutation_chance=1.0,
        mutation_delta_h=3.0,
        bias_h_group_deg=4.0,
        mutation_delta_s=0.0,
        mutation_delta_l=0.0,
    )
    feedback = FeedbackConfig(
        reproduction_base_chance=0.0,
        base_death_probability_per_second=0.0,
        age_death_probability_per_second=0.0,
        density_death_probability_per_neighbor_per_second=0.0,
        disease_probability_per_neighbor=0.0,
        stress_drain_per_neighbor=0.0,
        group_switch_chance=0.0,
        group_detach_new_group_chance=0.0,
        group_formation_chance=0.0,
        group_split_chance=0.0,
        group_split_new_group_chance=0.0,
        group_birth_seed_chance=0.0,
        group_mutation_chance=0.0,
    )
    config = SimulationConfig(
        seed=33,
        time_step=1.0,
        initial_population=1,
        max_population=1,
        appearance=appearance,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=1.0,
            adult_age=0.0,
        ),
        feedback=feedback,
        evolution=EvolutionConfig(enabled=False),
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
    )
    world = World(config)
    parent = world.agents[0]
    parent.group_id = 5
    parent.appearance_h = 10.0

    hue, saturation, lightness = world._inherit_appearance(parent)

    appearance_rng = DeterministicRng(_derive_stream_seed(config.seed, _APPEARANCE_RNG_SALT))
    appearance_rng.next_float()
    hue_delta = appearance_rng.next_range(-appearance.mutation_delta_h, appearance.mutation_delta_h)
    hashed = (int(parent.group_id) * 0x9E3779B1) & 0xFFFFFFFF
    sign = 1.0 if (hashed & 1) == 0 else -1.0
    hue_delta = _clamp_value(
        hue_delta + appearance.bias_h_group_deg * sign,
        -appearance.mutation_delta_h,
        appearance.mutation_delta_h,
    )
    expected_h = (parent.appearance_h + hue_delta) % 360
    expected_s = _clamp_value(
        parent.appearance_s + appearance_rng.next_range(-appearance.mutation_delta_s, appearance.mutation_delta_s),
        0.0,
        1.0,
    )
    expected_l = _clamp_value(
        parent.appearance_l + appearance_rng.next_range(-appearance.mutation_delta_l, appearance.mutation_delta_l),
        0.0,
        1.0,
    )

    assert hue == approx(expected_h)
    assert saturation == approx(expected_s)
    assert lightness == approx(expected_l)


def test_pair_appearance_bias_uses_child_group():
    appearance = AppearanceConfig(
        base_h=50.0,
        base_s=1.0,
        base_l=0.83,
        mutation_chance=1.0,
        mutation_delta_h=6.0,
        bias_h_group_deg=2.5,
        mutation_delta_s=0.0,
        mutation_delta_l=0.0,
    )
    config = SimulationConfig(
        seed=91,
        time_step=1.0,
        initial_population=2,
        max_population=2,
        appearance=appearance,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=1.0,
            adult_age=0.0,
        ),
        feedback=FeedbackConfig(
            reproduction_base_chance=0.0,
            base_death_probability_per_second=0.0,
            age_death_probability_per_second=0.0,
            density_death_probability_per_neighbor_per_second=0.0,
            disease_probability_per_neighbor=0.0,
            stress_drain_per_neighbor=0.0,
            group_switch_chance=0.0,
            group_detach_new_group_chance=0.0,
            group_formation_chance=0.0,
            group_split_chance=0.0,
            group_split_new_group_chance=0.0,
            group_birth_seed_chance=0.0,
            group_mutation_chance=0.0,
        ),
        evolution=EvolutionConfig(enabled=False),
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
    )
    world = World(config)
    first = world.agents[0]
    second = world.agents[1]
    first.group_id = 2
    second.group_id = 3
    first.appearance_h = 350.0
    second.appearance_h = 10.0
    first.appearance_s = appearance.base_s
    first.appearance_l = appearance.base_l
    second.appearance_s = appearance.base_s
    second.appearance_l = appearance.base_l

    hue, saturation, lightness = world._inherit_appearance_pair_with_group(first, second, bias_group_id=3)

    appearance_rng = DeterministicRng(_derive_stream_seed(config.seed, _APPEARANCE_RNG_SALT))
    appearance_rng.next_float()
    base_hue = world._circular_mean_deg(first.appearance_h, second.appearance_h)
    hue_delta = appearance_rng.next_range(-appearance.mutation_delta_h, appearance.mutation_delta_h)
    hashed = (int(3) * 0x9E3779B1) & 0xFFFFFFFF
    sign = 1.0 if (hashed & 1) == 0 else -1.0
    hue_delta = _clamp_value(
        hue_delta + appearance.bias_h_group_deg * sign,
        -appearance.mutation_delta_h,
        appearance.mutation_delta_h,
    )
    expected_h = (base_hue + hue_delta) % 360
    expected_s = _clamp_value(
        appearance.base_s + appearance_rng.next_range(-appearance.mutation_delta_s, appearance.mutation_delta_s),
        0.0,
        1.0,
    )
    expected_l = _clamp_value(
        appearance.base_l + appearance_rng.next_range(-appearance.mutation_delta_l, appearance.mutation_delta_l),
        0.0,
        1.0,
    )

    assert hue == approx(expected_h)
    assert saturation == approx(expected_s)
    assert lightness == approx(expected_l)


def test_pair_reproduction_requires_mate():
    feedback = FeedbackConfig(
        reproduction_base_chance=1.0,
        base_death_probability_per_second=0.0,
        age_death_probability_per_second=0.0,
        density_death_probability_per_neighbor_per_second=0.0,
        disease_probability_per_neighbor=0.0,
        stress_drain_per_neighbor=0.0,
        group_switch_chance=0.0,
        group_detach_new_group_chance=0.0,
        group_formation_chance=0.0,
        group_split_chance=0.0,
        group_split_new_group_chance=0.0,
        group_birth_seed_chance=0.0,
        group_mutation_chance=0.0,
    )
    config = SimulationConfig(
        seed=11,
        time_step=1.0,
        initial_population=10,
        max_population=11,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=1.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=1.0,
            adult_age=0.0,
        ),
        feedback=feedback,
        evolution=EvolutionConfig(enabled=False),
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
    )
    world = World(config)
    parent = world.agents[0]
    parent.energy = 5.0
    parent.age = 1.0

    births = lifecycle.apply_life_cycle(
        world,
        parent,
        neighbor_count=0,
        same_group_neighbors=0,
        can_create_groups=False,
        neighbors=[],
        neighbor_dist_sq=[],
        paired_ids=set(),
        base_cell_key=world._cell_key(parent.position),
    )

    assert births == 0
    assert len(world._birth_queue) == 0


def test_pair_lineage_inheritance_is_deterministic():
    evolution = EvolutionConfig(enabled=True, lineage_mutation_chance=0.0)
    config = SimulationConfig(seed=17, initial_population=0, evolution=evolution)
    world = World(config)
    first = Agent(
        id=0,
        generation=0,
        group_id=-1,
        position=Vector2(),
        velocity=Vector2(),
        energy=1.0,
        age=1.0,
        state=AgentState.WANDER,
        lineage_id=3,
    )
    second = Agent(
        id=1,
        generation=0,
        group_id=-1,
        position=Vector2(),
        velocity=Vector2(),
        energy=1.0,
        age=1.0,
        state=AgentState.WANDER,
        lineage_id=9,
    )

    expected_rng = DeterministicRng(config.seed)
    expected_lineage = first.lineage_id if expected_rng.next_float() < 0.5 else second.lineage_id

    assert world._inherit_lineage_pair(first, second) == expected_lineage


def test_tick_metrics_accumulates_zero_population():
    world = World(make_static_config(seed=31))

    metrics = world.step(0)
    snapshot = world.snapshot(1)

    assert metrics.population == 0
    assert metrics.average_energy == approx(0.0)
    assert metrics.average_age == approx(0.0)
    assert metrics.groups == 0
    assert metrics.ungrouped == 0
    assert snapshot.metrics.population == metrics.population
    assert snapshot.metrics.groups == metrics.groups
    assert snapshot.metrics.ungrouped == metrics.ungrouped


def test_tick_metrics_accumulates_grouped_population_once():
    config = make_static_config(seed=77)
    world = World(config)
    world.agents.extend(
        [
            Agent(
                id=0,
                generation=0,
                group_id=2,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=6.0,
                age=2.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=1,
                generation=0,
                group_id=2,
                position=Vector2(1.0, 0.0),
                velocity=Vector2(),
                energy=8.0,
                age=4.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 2
    world._refresh_index_map()

    metrics = world.step(0)
    world._metrics = None
    world._population_stats_dirty = False

    def fail_recalc():
        raise AssertionError("Population stats should be reused for snapshot when cache is fresh")

    world._recalculate_population_stats = fail_recalc  # type: ignore[assignment]
    snapshot = world.snapshot(1)

    assert metrics.population == 2
    assert metrics.births == 0
    assert metrics.deaths == 0
    assert metrics.groups == 1
    assert metrics.ungrouped == 0
    assert metrics.average_energy == approx(7.0)
    assert metrics.average_age == approx(4.0)
    assert snapshot.metrics.population == metrics.population
    assert snapshot.metrics.groups == metrics.groups
    assert snapshot.metrics.average_energy == approx(metrics.average_energy)


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

    births = lifecycle.apply_life_cycle(
        world,
        agent,
        neighbor_count=100,
        same_group_neighbors=0,
        can_create_groups=False,
        base_cell_key=world._cell_key(agent.position),
    )

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
            group_adoption_chance=0.3,
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


def test_gradients_match_neighbor_cells():
    config = SimulationConfig(
        seed=1,
        time_step=1.0,
        world_size=3.0,
        cell_size=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
        ),
        environment=EnvironmentConfig(
            food_per_cell=20.0,
            food_regen_per_second=0.0,
            food_consumption_rate=0.0,
            food_diffusion_rate=0.0,
            food_decay_rate=0.0,
            danger_diffusion_rate=0.0,
            danger_decay_rate=0.0,
            pheromone_diffusion_rate=0.0,
            pheromone_decay_rate=0.0,
        ),
    )
    world = World(config)
    env = world._environment  # type: ignore[attr-defined]

    env._food_cells = {  # type: ignore[attr-defined]
        (2, 1): FoodCell(5.0, 20.0, 0.0),
        (0, 1): FoodCell(1.0, 20.0, 0.0),
        (1, 2): FoodCell(7.0, 20.0, 0.0),
        (1, 0): FoodCell(3.0, 20.0, 0.0),
    }
    env._danger_field = {  # type: ignore[attr-defined]
        (2, 1): 9.0,
        (0, 1): 2.0,
        (1, 2): 4.0,
        (1, 0): 1.0,
    }
    env._pheromone_field = {  # type: ignore[attr-defined]
        (2, 1, 4): 6.0,
        (0, 1, 4): 2.0,
        (1, 2, 4): 8.0,
        (1, 0, 4): 3.0,
    }

    pos = Vector2(1.25, 1.25)
    assert tuple(fields_system.food_gradient(world, pos)) == approx((4.0, 4.0))  # right-left, up-down
    assert tuple(fields_system.danger_gradient(world, pos)) == approx((7.0, 3.0))
    assert tuple(fields_system.pheromone_gradient(world, 4, pos)) == approx((4.0, 5.0))

    # Boundary clamping preserves previous behavior (left/down clamp to edge cell)
    env._food_cells.update(
        {
            (1, 0): FoodCell(12.0, 20.0, 0.0),
            (0, 0): FoodCell(4.0, 20.0, 0.0),
            (0, 1): FoodCell(12.0, 20.0, 0.0),
        }
    )
    env._danger_field.update({(1, 0): 6.5, (0, 0): 3.0, (0, 1): 6.5})
    env._pheromone_field.update({(1, 0, 4): 9.0, (0, 0, 4): 3.0, (0, 1, 4): 9.0})

    edge_pos = Vector2(0.05, 0.05)
    assert tuple(fields_system.food_gradient(world, edge_pos)) == approx((8.0, 8.0))
    assert tuple(fields_system.danger_gradient(world, edge_pos)) == approx((3.5, 3.5))
    assert tuple(fields_system.pheromone_gradient(world, 4, edge_pos)) == approx((6.0, 6.0))


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


def test_loyalty_suppresses_switching_to_majority():
    config = SimulationConfig(
        seed=0,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0, wander_jitter=0.0
        ),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=10.0,
            group_switch_chance=1.0,
            group_detach_new_group_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
            group_adoption_chance=0.3,
            group_adoption_small_group_bonus=0.0,
            group_adoption_guard_min_allies=1,
            reproduction_base_chance=0.0,
            base_death_probability_per_second=0.0,
            age_death_probability_per_second=0.0,
            density_death_probability_per_neighbor_per_second=0.0,
            group_split_chance=0.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=300,
                generation=0,
                group_id=1,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
                traits=AgentTraits(sociality=1.3, loyalty=1.0),
            ),
            Agent(
                id=301,
                generation=0,
                group_id=2,
                position=Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=302,
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
    for agent in world.agents:
        agent.wander_dir = Vector2(1.0, 0.0)
        agent.wander_time = 1.0
    world._next_id = 303
    world._next_group_id = 3
    world._refresh_index_map()
    world._rng = DeterministicRng(config.seed)
    world._rng.next_float = lambda: 0.0  # type: ignore[assignment]

    world.step(0)
    assert world.agents[0].group_id == 2

    loyal_world = World(config)
    loyal_world.agents.clear()
    loyal_world.agents.extend(
        [
            Agent(
                id=400,
                generation=0,
                group_id=1,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
                traits=AgentTraits(sociality=1.3, loyalty=5.0),
            ),
            Agent(
                id=401,
                generation=0,
                group_id=2,
                position=Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=402,
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
    for agent in loyal_world.agents:
        agent.wander_dir = Vector2(1.0, 0.0)
        agent.wander_time = 1.0
    loyal_world._next_id = 403
    loyal_world._next_group_id = 3
    loyal_world._refresh_index_map()
    loyal_world._rng = DeterministicRng(config.seed)
    loyal_world._rng.next_float = lambda: 0.5  # type: ignore[assignment]

    loyal_world.step(0)
    assert loyal_world.agents[0].group_id == 1


def test_kin_bias_prefers_lineage_majority():
    config = SimulationConfig(
        seed=44,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(
            base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0, wander_jitter=0.0
        ),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=10.0,
            group_switch_chance=0.0,
            group_detach_new_group_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
            group_adoption_chance=1.0,
            group_adoption_small_group_bonus=0.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.extend(
        [
            Agent(
                id=100,
                generation=0,
                group_id=-1,
                position=Vector2(0.0, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
                lineage_id=7,
                traits=AgentTraits(kin_bias=1.3),
            ),
            Agent(
                id=101,
                generation=0,
                group_id=2,
                position=Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
                lineage_id=7,
            ),
            Agent(
                id=102,
                generation=0,
                group_id=3,
                position=Vector2(0.5, 0.5),
                velocity=Vector2(),
                energy=10.0,
                age=10.0,
                state=AgentState.WANDER,
                lineage_id=8,
            ),
        ]
    )
    world._next_id = 103
    world._next_group_id = 4
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 2


def test_loyalty_extends_detach_timer():
    config = SimulationConfig(
        seed=55,
        time_step=1.0,
        initial_population=0,
        species=SpeciesConfig(base_speed=0.0, max_acceleration=0.0, metabolism_per_second=0.0, vision_radius=3.0),
        feedback=FeedbackConfig(
            group_cohesion_radius=1.0,
            group_detach_close_neighbor_threshold=1,
            group_detach_after_seconds=1.0,
            group_switch_chance=0.0,
            group_detach_new_group_chance=0.0,
            group_cohesion_weight=0.0,
            group_formation_warmup_seconds=0.0,
            group_adoption_neighbor_threshold=1,
        ),
    )
    world = World(config)
    world.agents.clear()
    world.agents.append(
        Agent(
            id=200,
            generation=0,
            group_id=0,
            position=Vector2(0.0, 0.0),
            velocity=Vector2(),
            energy=10.0,
            age=10.0,
            state=AgentState.WANDER,
            traits=AgentTraits(loyalty=1.3),
        )
    )
    world._next_id = 201
    world._next_group_id = 1
    world._refresh_index_map()

    world.step(0)

    assert world.agents[0].group_id == 0
    assert world.agents[0].group_lonely_seconds == approx(1.0)


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
    speed_cap = world._trait_speed_limit(agent.traits)
    desired = steering.compute_desired_velocity(world, agent, [other], [Vector2(0.2, 0.0)], speed_cap)
    assert desired.x < 0.0  # 押し返される
    # ほぼ一直線の押し返しになることを確認（y成分が小さい）
    assert abs(desired.y) < abs(desired.x) * 0.25


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
    separation = steering.separation(
        world, agent, [ally, rival], [Vector2(1.0, 0.0), Vector2(-1.0, 0.0)]
    )

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

    speed_cap = world._trait_speed_limit(agent.traits)
    desired = steering.compute_desired_velocity(world, agent, [rival], [Vector2(3.0, 0.0)], speed_cap)

    assert desired.x < 0.0  # 異グループから離れる
    assert abs(desired.y) < 1e-6
    assert agent.state == AgentState.WANDER


def test_flee_blends_ally_cohesion_and_alignment():
    config = SimulationConfig(
        seed=27,
        time_step=1.0,
        world_size=3.0,
        cell_size=1.0,
        initial_population=0,
        boundary_margin=0.0,
        environment=EnvironmentConfig(
            food_per_cell=0.0,
            food_regen_per_second=0.0,
            food_consumption_rate=0.0,
            danger_diffusion_rate=0.0,
            danger_decay_rate=0.0,
        ),
        species=SpeciesConfig(
            base_speed=1.0,
            max_acceleration=10.0,
            metabolism_per_second=0.0,
            vision_radius=4.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=12.0,
            adult_age=0.0,
        ),
        feedback=FeedbackConfig(
            group_cohesion_radius=4.0,
            group_cohesion_weight=0.0,
            ally_cohesion_weight=0.0,
            ally_separation_weight=0.0,
            other_group_separation_weight=0.0,
            min_separation_weight=0.0,
            other_group_avoid_weight=0.0,
        ),
    )
    world = World(config)
    env = world._environment  # type: ignore[attr-defined]
    env._danger_field = {  # type: ignore[attr-defined]
        (1, 1): 1.0,
        (2, 1): 2.0,
        (0, 1): 0.0,
    }

    def compute_desired(neighbors, neighbor_offsets):
        agent = Agent(
            id=210,
            generation=0,
            group_id=1,
            position=Vector2(1.5, 1.5),
            velocity=Vector2(),
            energy=8.0,
            age=5.0,
            state=AgentState.WANDER,
        )
        speed_cap = world._trait_speed_limit(agent.traits)
        desired = steering.compute_desired_velocity(
            world, agent, neighbors, neighbor_offsets, speed_cap
        )
        return desired, agent.state

    desired_solo, solo_state = compute_desired([], [])
    ally = Agent(
        id=211,
        generation=0,
        group_id=1,
        position=Vector2(2.5, 1.5),
        velocity=Vector2(1.0, 0.0),
        energy=8.0,
        age=5.0,
        state=AgentState.WANDER,
    )
    desired_with_ally, ally_state = compute_desired([ally], [Vector2(1.0, 0.0)])

    assert solo_state == AgentState.FLEE
    assert ally_state == AgentState.FLEE
    assert desired_solo.x < 0.0
    assert desired_with_ally.x < 0.0
    assert desired_with_ally.x > desired_solo.x
    assert abs(desired_with_ally.y) < 1e-6


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
        speed_cap = world._trait_speed_limit(agent.traits)
        desired = steering.compute_desired_velocity(world, agent, [ally], [Vector2(1.0, 0.0)], speed_cap)
        return desired

    desired_low = compute_desired(config_low)
    desired_high = compute_desired(config_high)

    assert desired_high.x > desired_low.x
    assert desired_high.y == approx(desired_low.y)


def test_group_base_registered_on_group_formation_point():
    config = SimulationConfig(
        seed=11,
        time_step=1.0,
        initial_population=0,
        boundary_margin=0.0,
        environment=EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0),
        species=SpeciesConfig(
            base_speed=0.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=4.0,
            wander_jitter=0.0,
        ),
        feedback=FeedbackConfig(
            group_formation_warmup_seconds=0.0,
            group_formation_neighbor_threshold=1,
            group_formation_chance=1.0,
            group_cohesion_weight=0.0,
            personal_space_weight=0.0,
            other_group_avoid_weight=0.0,
        ),
    )
    world = World(config)
    world.agents.clear()
    origin = Vector2(1.0, 1.0)
    origin_x = origin.x
    origin_y = origin.y
    world.agents.extend(
        [
            Agent(
                id=0,
                generation=0,
                group_id=world._UNGROUPED,  # type: ignore[attr-defined]
                position=origin,
                velocity=Vector2(),
                energy=10.0,
                age=0.0,
                state=AgentState.WANDER,
            ),
            Agent(
                id=1,
                generation=0,
                group_id=world._UNGROUPED,  # type: ignore[attr-defined]
                position=origin + Vector2(0.5, 0.0),
                velocity=Vector2(),
                energy=10.0,
                age=0.0,
                state=AgentState.WANDER,
            ),
        ]
    )
    world._next_id = 2  # type: ignore[attr-defined]
    world._next_group_id = 0  # type: ignore[attr-defined]
    world._refresh_index_map()  # type: ignore[attr-defined]

    world.step(0)

    assert world.agents[0].group_id == 0
    base = world._group_bases[0]  # type: ignore[attr-defined]
    assert base.x == approx(origin_x)
    assert base.y == approx(origin_y)


def test_group_base_attraction_pulls_toward_base():
    shared_env = EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0)
    config = SimulationConfig(
        seed=13,
        time_step=1.0,
        initial_population=0,
        boundary_margin=0.0,
        environment=shared_env,
        species=SpeciesConfig(
            base_speed=1.0,
            max_acceleration=0.0,
            metabolism_per_second=0.0,
            vision_radius=0.0,
            wander_jitter=0.0,
            reproduction_energy_threshold=10.0,
            adult_age=1000.0,
        ),
        feedback=FeedbackConfig(
            group_formation_warmup_seconds=0.0,
            group_base_attraction_weight=1.0,
            group_base_soft_radius=0.0,
            group_base_dead_zone=0.0,
            group_cohesion_weight=0.0,
            ally_cohesion_weight=0.0,
            ally_separation_weight=0.0,
            other_group_separation_weight=0.0,
            other_group_avoid_weight=0.0,
            personal_space_weight=0.0,
            min_separation_weight=0.0,
        ),
    )
    world = World(config)
    world._group_bases[0] = Vector2(0.0, 0.0)  # type: ignore[attr-defined]
    agent = Agent(
        id=10,
        generation=0,
        group_id=0,
        position=Vector2(5.0, 0.0),
        velocity=Vector2(),
        energy=8.0,
        age=0.0,
        state=AgentState.WANDER,
    )

    speed_cap = world._trait_speed_limit(agent.traits)
    desired = steering.compute_desired_velocity(world, agent, [], [], speed_cap)

    assert desired.x < 0.0
    assert abs(desired.y) < 1e-6


def test_min_separation_term_activates_when_too_close():
    shared_env = EnvironmentConfig(food_per_cell=0.0, food_regen_per_second=0.0, food_consumption_rate=0.0)
    species = SpeciesConfig(
        base_speed=1.0,
        max_acceleration=0.0,
        metabolism_per_second=0.0,
        vision_radius=0.0,
        wander_jitter=0.0,
    )
    config_off = SimulationConfig(
        seed=21,
        time_step=1.0,
        initial_population=0,
        environment=shared_env,
        species=species,
        feedback=FeedbackConfig(
            ally_separation_weight=0.0,
            other_group_separation_weight=0.0,
            min_separation_distance=1.0,
            min_separation_weight=0.0,
        ),
    )
    config_on = SimulationConfig(
        seed=22,
        time_step=1.0,
        initial_population=0,
        environment=shared_env,
        species=species,
        feedback=FeedbackConfig(
            ally_separation_weight=0.0,
            other_group_separation_weight=0.0,
            min_separation_distance=1.0,
            min_separation_weight=5.0,
        ),
    )

    def compute_sep(cfg: SimulationConfig):
        world = World(cfg)
        agent = Agent(
            id=0,
            generation=0,
            group_id=0,
            position=Vector2(),
            velocity=Vector2(),
            energy=10.0,
            age=0.0,
            state=AgentState.WANDER,
        )
        neighbor = Agent(
            id=1,
            generation=0,
            group_id=0,
            position=Vector2(0.2, 0.0),
            velocity=Vector2(),
            energy=10.0,
            age=0.0,
            state=AgentState.WANDER,
        )
        return steering.separation(world, agent, [neighbor], [Vector2(0.2, 0.0)])

    sep_off = compute_sep(config_off)
    sep_on = compute_sep(config_on)

    assert sep_off.length_squared() < 1e-12
    assert sep_on.x < 0.0


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


def test_steering_stride_reuses_last_desired():
    config = make_static_config(seed=7)
    config.initial_population = 2
    config.species.base_speed = 2.0
    config.species.max_acceleration = 6.0
    config.species.vision_radius = 3.0
    config.species.wander_jitter = 0.6
    config.feedback.steering_update_population_threshold = 0
    config.feedback.steering_update_stride = 2
    world = World(config)
    world.step(0)
    agent0 = world.agents[0]
    last0 = (agent0.last_desired.x, agent0.last_desired.y)
    world.step(1)
    agent0_next = world.agents[0]
    assert agent0_next.last_desired.x == approx(last0[0])
    assert agent0_next.last_desired.y == approx(last0[1])
