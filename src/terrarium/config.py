from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class SpeciesConfig:
    base_speed: float = 6.0
    max_acceleration: float = 20.0
    vision_radius: float = 6.0
    metabolism_per_second: float = 0.8
    birth_energy_cost: float = 8.0
    reproduction_energy_threshold: float = 12.0
    adult_age: float = 20.0
    initial_age_min: float = 0.0
    initial_age_max: float = 0.0
    max_age: float = 80.0
    wander_jitter: float = 0.45
    initial_energy_fraction_of_threshold: float = 0.8
    energy_soft_cap: float = 20.0
    high_energy_metabolism_slope: float = 0.015


@dataclass
class ResourcePatchConfig:
    position: tuple[float, float] = (0.0, 0.0)
    radius: float = 5.0
    resource_per_cell: float = 10.0
    regen_per_second: float = 0.5
    initial_resource: float = 10.0


@dataclass
class EnvironmentConfig:
    food_per_cell: float = 10.0
    food_regen_per_second: float = 0.5
    food_consumption_rate: float = 5.0
    food_diffusion_rate: float = 0.0
    food_decay_rate: float = 0.0
    food_from_death: float = 1.0
    resource_patches: List[ResourcePatchConfig] = field(default_factory=list)
    danger_diffusion_rate: float = 1.0
    danger_decay_rate: float = 1.0
    danger_pulse_on_flee: float = 1.0
    pheromone_diffusion_rate: float = 0.0
    pheromone_decay_rate: float = 0.0
    pheromone_deposit_on_birth: float = 4.0


@dataclass
class FeedbackConfig:
    local_density_soft_cap: int = 8
    density_reproduction_penalty: float = 0.6
    stress_drain_per_neighbor: float = 0.05
    disease_probability_per_neighbor: float = 0.002
    density_reproduction_slope: float = 0.04
    base_death_probability_per_second: float = 0.0005
    age_death_probability_per_second: float = 0.00015
    density_death_probability_per_neighbor_per_second: float = 0.0001

    group_formation_warmup_seconds: float = 6.0
    group_formation_neighbor_threshold: int = 3
    group_formation_chance: float = 0.02
    group_adoption_neighbor_threshold: int = 4
    group_adoption_chance: float = 0.003
    group_split_neighbor_threshold: int = 6
    group_split_chance: float = 0.0015
    group_split_new_group_chance: float = 0.5
    group_split_stress_threshold: float = 0.4
    group_birth_seed_chance: float = 0.35
    group_mutation_chance: float = 0.05
    group_cohesion_radius: float = 3.0
    group_detach_close_neighbor_threshold: int = 1
    group_detach_after_seconds: float = 5.0
    group_switch_chance: float = 0.2
    group_cohesion_weight: float = 0.6


@dataclass
class SimulationConfig:
    time_step: float = 1.0 / 30.0
    initial_population: int = 120
    max_population: int = 500
    world_size: float = 100.0
    cell_size: float = 2.5
    seed: int = 1337
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
