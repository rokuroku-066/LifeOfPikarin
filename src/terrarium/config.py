from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class SpeciesConfig:
    base_speed: float = 6.0
    max_acceleration: float = 20.0
    vision_radius: float = 3.0
    metabolism_per_second: float = 1.0
    birth_energy_cost: float = 10.0
    reproduction_energy_threshold: float = 10
    adult_age: float = 6.0
    initial_age_min: float = 0.5
    initial_age_max: float = 0.0
    max_age: float = 80.0
    wander_jitter: float = 0.25
    wander_refresh_seconds: float = 0.12
    initial_energy_fraction_of_threshold: float = 1.3
    energy_soft_cap: float = 20.0
    high_energy_metabolism_slope: float = 0.00


@dataclass
class ResourcePatchConfig:
    position: tuple[float, float] = (0.0, 0.0)
    radius: float = 7.0
    resource_per_cell: float = 16.0
    regen_per_second: float = 0.3
    initial_resource: float = 10.0


@dataclass
class EnvironmentConfig:
    food_per_cell: float = 12.0
    food_regen_per_second: float = 2.1
    food_consumption_rate: float = 6.5
    food_diffusion_rate: float = 0.3
    food_decay_rate: float = 0.0
    food_from_death: float = 5.0
    food_regen_noise_amplitude: float = 0.5
    food_regen_noise_interval_seconds: float = 12.0
    food_regen_noise_smooth_seconds: float = 4.0
    resource_patches: List[ResourcePatchConfig] = field(default_factory=list)
    danger_diffusion_rate: float = 2.0
    danger_decay_rate: float = 1.0
    danger_pulse_on_flee: float = 1.0
    pheromone_diffusion_rate: float = 0.3
    pheromone_decay_rate: float = 0.05
    pheromone_deposit_on_birth: float = 4.0
    group_food_max_per_cell: float = 3.0
    group_food_decay_rate: float = 0.25
    group_food_diffusion_rate: float = 0.07


@dataclass
class FeedbackConfig:
    local_density_soft_cap: int = 12
    density_reproduction_penalty: float = 0.65
    stress_drain_per_neighbor: float = 0.03
    disease_probability_per_neighbor: float = 0.0025
    density_reproduction_slope: float = 0.02
    reproduction_base_chance: float = 0.4
    base_death_probability_per_second: float = 0.0012
    age_death_probability_per_second: float = 0.00035
    density_death_probability_per_neighbor_per_second: float = 0.0005
    # Remove global population death pressure; rely on resources + local density
    global_population_pressure_start: int = 10_000
    global_population_pressure_slope: float = 0.0
    global_population_pressure_delay_seconds: float = 4.0
    population_peak_threshold: int = 400
    post_peak_min_groups: int = 5
    post_peak_max_groups: int = 20
    post_peak_group_seed_size: int = 4
    max_groups: int = 20
    group_formation_warmup_seconds: float = 0.0
    group_formation_neighbor_threshold: int = 5
    group_formation_chance: float = 0.07
    group_adoption_neighbor_threshold: int = 1
    group_adoption_chance: float = 0.5
    group_adoption_small_group_bonus: float = 0.4
    group_food_neighbor_threshold: int = 6
    # Disable free group-food spawning (it injects energy and can mask scarcity)
    group_food_spawn_chance: float = 0.0
    group_food_spawn_amount: float = 2.0
    group_split_neighbor_threshold: int = 5
    group_split_chance: float = 0.008
    group_split_size_bonus_per_neighbor: float = 0.01
    group_split_chance_max: float = 0.2
    group_split_size_stress_weight: float = 0.001
    group_split_recruitment_count: int = 3
    group_split_new_group_chance: float = 0.02
    group_split_stress_threshold: float = 0.12
    group_merge_cooldown_seconds: float = 1.0
    group_adoption_guard_min_allies: int = 2
    group_reproduction_penalty_per_ally: float = 0.02
    group_reproduction_min_factor: float = 0.08
    group_birth_seed_chance: float = 0.03
    group_mutation_chance: float = 0.005
    personal_space_radius: float = 1.3
    personal_space_weight: float = 2.6
    group_cohesion_radius: float = 4.0
    group_detach_radius: float = 3.0
    group_detach_close_neighbor_threshold: int = 2
    group_detach_after_seconds: float = 4.5
    group_switch_chance: float = 0.4
    group_detach_new_group_chance: float = 0.01
    group_cohesion_weight: float = 3.2
    ally_cohesion_weight: float = 1.6
    ally_separation_weight: float = 0.6
    other_group_separation_weight: float = 1.8
    other_group_avoid_radius: float = 6.0
    other_group_avoid_weight: float = 0.9
    group_base_attraction_weight: float = 0.55
    group_base_soft_radius: float = 7.0
    group_base_dead_zone: float = 1.2
    min_separation_distance: float = 1.0
    min_separation_weight: float = 3.0
    group_seek_radius: float = 10.0
    group_seek_weight: float = 1.8


@dataclass
class EvolutionClampConfig:
    speed: tuple[float, float] = (0.8, 1.25)
    metabolism: tuple[float, float] = (0.8, 1.25)
    disease_resistance: tuple[float, float] = (0.6, 1.4)
    fertility: tuple[float, float] = (0.7, 1.3)
    sociality: tuple[float, float] = (0.7, 1.3)
    territoriality: tuple[float, float] = (0.7, 1.3)
    loyalty: tuple[float, float] = (0.7, 1.3)
    founder: tuple[float, float] = (0.7, 1.3)
    kin_bias: tuple[float, float] = (0.7, 1.3)


@dataclass
class EvolutionConfig:
    enabled: bool = True
    mutation_strength: float = 0.05
    lineage_mutation_chance: float = 0.01
    speed_mutation_weight: float = 1.0
    metabolism_mutation_weight: float = 0.5
    disease_resistance_mutation_weight: float = 0.5
    fertility_mutation_weight: float = 0.5
    sociality_mutation_weight: float = 0.2
    territoriality_mutation_weight: float = 0.2
    loyalty_mutation_weight: float = 0.2
    founder_mutation_weight: float = 0.2
    kin_bias_mutation_weight: float = 0.2
    clamp: EvolutionClampConfig = field(default_factory=EvolutionClampConfig)


@dataclass
class SimulationConfig:
    time_step: float = 1.0 / 50.0
    environment_tick_interval: float = 6.0
    initial_population: int = 200
    max_population: int = 700
    world_size: float = 100.0
    boundary_margin: float = 10.0
    boundary_avoidance_weight: float = 1.6
    boundary_turn_weight: float = 0.85
    cell_size: float = 5.5
    seed: int = 42
    config_version: str = "v1"
    species: SpeciesConfig = field(default_factory=SpeciesConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)

    @staticmethod
    def from_yaml(path: Path) -> "SimulationConfig":
        data = yaml.safe_load(Path(path).read_text())
        return load_config(data)


@dataclass
class AppConfig:
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    broadcast_interval: int = 2


def load_config(raw: dict) -> SimulationConfig:
    default_clamp = EvolutionClampConfig()
    clamp_raw = raw.get("evolution", {}).get("clamp", {})

    def _pair(value: tuple[float, float] | list[float] | None, default: tuple[float, float]) -> tuple[float, float]:
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return (float(value[0]), float(value[1]))
        return default

    species = SpeciesConfig(**raw.get("species", {}))
    patches = [ResourcePatchConfig(**patch) for patch in raw.get("resource_patches", raw.get("ResourcePatches", []))]
    env_raw = raw.get("environment", {})
    env = EnvironmentConfig(
        resource_patches=patches,
        **{k: v for k, v in env_raw.items() if k != "resource_patches"},
    )
    feedback = FeedbackConfig(**raw.get("feedback", {}))
    evolution_raw = raw.get("evolution", {})
    clamp = EvolutionClampConfig(
        speed=_pair(clamp_raw.get("speed"), default_clamp.speed),
        metabolism=_pair(clamp_raw.get("metabolism"), default_clamp.metabolism),
        disease_resistance=_pair(clamp_raw.get("disease_resistance"), default_clamp.disease_resistance),
        fertility=_pair(clamp_raw.get("fertility"), default_clamp.fertility),
        sociality=_pair(clamp_raw.get("sociality"), default_clamp.sociality),
        territoriality=_pair(clamp_raw.get("territoriality"), default_clamp.territoriality),
        loyalty=_pair(clamp_raw.get("loyalty"), default_clamp.loyalty),
        founder=_pair(clamp_raw.get("founder"), default_clamp.founder),
        kin_bias=_pair(clamp_raw.get("kin_bias"), default_clamp.kin_bias),
    )
    evolution_values = {k: v for k, v in evolution_raw.items() if k != "clamp"}
    evolution = EvolutionConfig(clamp=clamp, **evolution_values)
    sim_values = {
        k: v for k, v in raw.items() if k not in {"species", "environment", "feedback", "resource_patches", "evolution"}
    }
    return SimulationConfig(species=species, environment=env, feedback=feedback, evolution=evolution, **sim_values)
