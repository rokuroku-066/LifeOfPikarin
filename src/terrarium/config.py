from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class SpeciesConfig:
    base_speed: float = 5.3
    max_acceleration: float = 18.0
    vision_radius: float = 2.9
    metabolism_per_second: float = 0.9
    birth_energy_cost: float = 1.0
    reproduction_energy_threshold: float = 14.0
    adult_age: float = 18.0
    initial_age_min: float = 0.0
    initial_age_max: float = 0.0
    max_age: float = 90.0
    wander_jitter: float = 0.2
    wander_refresh_seconds: float = 0.14
    initial_energy_fraction_of_threshold: float = 0.95
    energy_soft_cap: float = 16.0
    high_energy_metabolism_slope: float = 0.05


@dataclass
class ResourcePatchConfig:
    position: tuple[float, float] = (0.0, 0.0)
    radius: float = 7.0
    resource_per_cell: float = 16.0
    regen_per_second: float = 0.3
    initial_resource: float = 10.0


@dataclass
class EnvironmentConfig:
    food_per_cell: float = 8.5
    food_regen_per_second: float = 0.7
    food_consumption_rate: float = 5.5
    food_diffusion_rate: float = 0.08
    food_decay_rate: float = 0.0
    food_from_death: float = 9.0
    food_regen_noise_amplitude: float = 0.5
    food_regen_noise_interval_seconds: float = 24.0
    food_regen_noise_smooth_seconds: float = 8.0
    resource_patches: List[ResourcePatchConfig] = field(default_factory=list)
    pheromone_diffusion_rate: float = 0.28
    pheromone_decay_rate: float = 0.045
    pheromone_deposit_on_birth: float = 3.0


@dataclass
class FeedbackConfig:
    local_density_soft_cap: int = 13
    density_reproduction_penalty: float = 0.45
    stress_drain_per_neighbor: float = 0.01
    disease_probability_per_neighbor: float = 0.001
    density_reproduction_slope: float = 0.02
    base_death_probability_per_second: float = 0.001
    age_death_probability_per_second: float = 0.0002
    density_death_probability_per_neighbor_per_second: float = 0.00012
    group_formation_warmup_seconds: float = 0.0
    group_formation_neighbor_threshold: int = 4
    group_formation_chance: float = 0.03
    group_adoption_neighbor_threshold: int = 2
    group_adoption_chance: float = 0.25
    group_adoption_small_group_bonus: float = 0.04
    group_split_neighbor_threshold: int = 9
    group_split_chance: float = 0.0015
    group_split_size_bonus_per_neighbor: float = 0.0035
    group_split_chance_max: float = 0.03
    group_split_size_stress_weight: float = 0.0009
    group_split_recruitment_count: int = 3
    group_split_new_group_chance: float = 0.06
    group_split_stress_threshold: float = 0.115
    group_merge_cooldown_seconds: float = 1.5
    group_adoption_guard_min_allies: int = 3
    group_reproduction_penalty_per_ally: float = 0.03
    group_reproduction_min_factor: float = 0.12
    group_birth_seed_chance: float = 0.03
    group_mutation_chance: float = 0.003
    max_groups: int = 10
    personal_space_radius: float = 1.0
    personal_space_weight: float = 2.2
    group_cohesion_radius: float = 5.2
    group_detach_radius: float = 2.7
    group_detach_close_neighbor_threshold: int = 2
    group_detach_after_seconds: float = 4.5
    group_switch_chance: float = 0.35
    group_detach_new_group_chance: float = 0.03
    group_cohesion_weight: float = 2.8
    ally_cohesion_weight: float = 1.3
    ally_separation_weight: float = 0.45
    other_group_separation_weight: float = 1.4
    other_group_avoid_radius: float = 7.0
    other_group_avoid_weight: float = 1.0
    group_base_attraction_weight: float = 0.55
    group_base_soft_radius: float = 8.0
    group_base_dead_zone: float = 1.2
    min_separation_distance: float = 0.7
    min_separation_weight: float = 2.1


@dataclass
class SimulationConfig:
    time_step: float = 1.0 / 50.0
    environment_tick_interval: float = 0.36
    initial_population: int = 260
    max_population: int = 400
    world_size: float = 110.0
    boundary_margin: float = 10.0
    boundary_avoidance_weight: float = 1.6
    boundary_turn_weight: float = 0.85
    cell_size: float = 5.5
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
