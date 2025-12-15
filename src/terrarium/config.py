from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class SpeciesConfig:
    base_speed: float = 6.0
    max_acceleration: float = 20.0
    vision_radius: float = 4.0
    metabolism_per_second: float = 1.0
    birth_energy_cost: float = 3.0
    reproduction_energy_threshold: float = 12.8
    adult_age: float = 6.0
    initial_age_min: float = 0.5
    initial_age_max: float = 0.0
    max_age: float = 80.0
    wander_jitter: float = 0.25
    wander_refresh_seconds: float = 0.12
    initial_energy_fraction_of_threshold: float = 1.3
    energy_soft_cap: float = 14.0
    high_energy_metabolism_slope: float = 0.08


@dataclass
class ResourcePatchConfig:
    position: tuple[float, float] = (0.0, 0.0)
    radius: float = 7.0
    resource_per_cell: float = 16.0
    regen_per_second: float = 0.3
    initial_resource: float = 10.0


@dataclass
class EnvironmentConfig:
    food_per_cell: float = 9.0
    food_regen_per_second: float = 0.7
    food_consumption_rate: float = 6.0
    food_diffusion_rate: float = 0.1
    food_decay_rate: float = 0.0
    food_from_death: float = 12.0
    food_regen_noise_amplitude: float = 0.9
    food_regen_noise_interval_seconds: float = 30.0
    food_regen_noise_smooth_seconds: float = 10.0
    resource_patches: List[ResourcePatchConfig] = field(default_factory=list)
    danger_diffusion_rate: float = 2.0
    danger_decay_rate: float = 1.0
    danger_pulse_on_flee: float = 1.0
    pheromone_diffusion_rate: float = 0.3
    pheromone_decay_rate: float = 0.05
    pheromone_deposit_on_birth: float = 4.0
    group_food_max_per_cell: float = 6.0
    group_food_decay_rate: float = 0.25
    group_food_diffusion_rate: float = 0.07


@dataclass
class FeedbackConfig:
    local_density_soft_cap: int = 12
    density_reproduction_penalty: float = 0.5
    stress_drain_per_neighbor: float = 0.02
    disease_probability_per_neighbor: float = 0.002
    density_reproduction_slope: float = 0.03
    base_death_probability_per_second: float = 0.0012
    age_death_probability_per_second: float = 0.00035
    density_death_probability_per_neighbor_per_second: float = 0.00025
    global_population_pressure_start: int = 200
    global_population_pressure_slope: float = 0.04
    global_population_pressure_delay_seconds: float = 14.0
    post_warmup_population_cap: int = 0
    population_peak_threshold: int = 400
    post_peak_population_cap: int = 30
    post_peak_min_groups: int = 5
    post_peak_max_groups: int = 10
    post_peak_group_seed_size: int = 4
    group_formation_warmup_seconds: float = 0.0
    group_formation_neighbor_threshold: int = 3
    group_formation_chance: float = 0.07
    group_adoption_neighbor_threshold: int = 1
    group_adoption_chance: float = 0.5
    group_adoption_small_group_bonus: float = 0.4
    group_food_neighbor_threshold: int = 6
    group_food_spawn_chance: float = 0.1
    group_food_spawn_amount: float = 2.0
    group_split_neighbor_threshold: int = 5
    group_split_chance: float = 0.008
    group_split_size_bonus_per_neighbor: float = 0.01
    group_split_chance_max: float = 0.2
    group_split_size_stress_weight: float = 0.001
    group_split_recruitment_count: int = 3
    group_split_new_group_chance: float = 0.05
    group_split_stress_threshold: float = 0.12
    group_merge_cooldown_seconds: float = 1.0
    group_adoption_guard_min_allies: int = 2
    group_reproduction_penalty_per_ally: float = 0.03
    group_reproduction_min_factor: float = 0.08
    group_birth_seed_chance: float = 0.03
    group_mutation_chance: float = 0.005
    personal_space_radius: float = 1.1
    personal_space_weight: float = 2.2
    group_cohesion_radius: float = 4.0
    group_detach_radius: float = 3.0
    group_detach_close_neighbor_threshold: int = 2
    group_detach_after_seconds: float = 4.5
    group_switch_chance: float = 0.4
    group_detach_new_group_chance: float = 0.01
    group_cohesion_weight: float = 3.2
    ally_cohesion_weight: float = 1.6
    ally_separation_weight: float = 0.4
    other_group_separation_weight: float = 1.4
    other_group_avoid_radius: float = 6.0
    other_group_avoid_weight: float = 0.9
    group_base_attraction_weight: float = 0.55
    group_base_soft_radius: float = 7.0
    group_base_dead_zone: float = 1.2
    min_separation_distance: float = 0.7
    min_separation_weight: float = 2.5


@dataclass
class SimulationConfig:
    time_step: float = 1.0 / 50.0
    environment_tick_interval: float = 2.0
    initial_population: int = 260
    max_population: int = 700
    world_size: float = 100.0
    boundary_margin: float = 10.0
    boundary_avoidance_weight: float = 1.6
    boundary_turn_weight: float = 0.85
    cell_size: float = 6.0
    seed: int = 42
    config_version: str = "v1"
    species: SpeciesConfig = field(default_factory=SpeciesConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)

    @staticmethod
    def from_yaml(path: Path) -> "SimulationConfig":
        data = yaml.safe_load(Path(path).read_text())
        return load_config(data)


@dataclass
class AppConfig:
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    broadcast_interval: int = 2


def load_config(raw: dict) -> SimulationConfig:
    species = SpeciesConfig(**raw.get("species", {}))
    patches = [ResourcePatchConfig(**patch) for patch in raw.get("resource_patches", raw.get("ResourcePatches", []))]
    env_raw = raw.get("environment", {})
    env = EnvironmentConfig(
        resource_patches=patches,
        **{k: v for k, v in env_raw.items() if k != "resource_patches"},
    )
    feedback = FeedbackConfig(**raw.get("feedback", {}))
    sim_values = {k: v for k, v in raw.items() if k not in {"species", "environment", "feedback", "resource_patches"}}
    return SimulationConfig(species=species, environment=env, feedback=feedback, **sim_values)
