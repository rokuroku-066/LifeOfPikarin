using System;
using System.Collections.Generic;

namespace Terrarium.Sim
{
    public sealed class SimulationConfig
    {
        public float TimeStep { get; set; } = 1f / 30f;
        public int InitialPopulation { get; set; } = 120;
        public int MaxPopulation { get; set; } = 500;
        public float WorldSize { get; set; } = 100f;
        public float CellSize { get; set; } = 2.5f;
        public int Seed { get; set; } = 1337;
        public SpeciesConfig Species { get; set; } = new();
        public EnvironmentConfig Environment { get; set; } = new();
        public FeedbackConfig Feedback { get; set; } = new();
    }

    public sealed class SpeciesConfig
    {
        public float BaseSpeed { get; set; } = 6f;
        public float MaxAcceleration { get; set; } = 20f;
        public float VisionRadius { get; set; } = 6f;
        public float MetabolismPerSecond { get; set; } = 0.8f;
        public float BirthEnergyCost { get; set; } = 8f;
        public float ReproductionEnergyThreshold { get; set; } = 12f;
        public float AdultAge { get; set; } = 20f;
        public float InitialAgeMin { get; set; } = 0f;
        public float InitialAgeMax { get; set; } = 0f;
        public float MaxAge { get; set; } = 80f;
        public float WanderJitter { get; set; } = 0.45f;
        public float InitialEnergyFractionOfThreshold { get; set; } = 0.8f;
        public float EnergySoftCap { get; set; } = 20f;
        public float HighEnergyMetabolismSlope { get; set; } = 0.015f;
    }

    public sealed class EnvironmentConfig
    {
        public float FoodPerCell { get; set; } = 10f;
        public float FoodRegenPerSecond { get; set; } = 0.5f;
        public float FoodConsumptionRate { get; set; } = 5f;
        public float FoodDiffusionRate { get; set; } = 0f;
        public float FoodDecayRate { get; set; } = 0f;
        public float FoodFromDeath { get; set; } = 1f;
        public IReadOnlyList<ResourcePatchConfig> ResourcePatches { get; set; } = Array.Empty<ResourcePatchConfig>();
        public float DangerDiffusionRate { get; set; } = 1f;
        public float DangerDecayRate { get; set; } = 1f;
        public float DangerPulseOnFlee { get; set; } = 1f;
        public float PheromoneDiffusionRate { get; set; } = 0f;
        public float PheromoneDecayRate { get; set; } = 0f;
        public float PheromoneDepositOnBirth { get; set; } = 4f;
    }

    public sealed class ResourcePatchConfig
    {
        public Vec2 Position { get; set; } = new Vec2(0, 0);
        public float Radius { get; set; } = 5f;
        public float ResourcePerCell { get; set; } = 10f;
        public float RegenPerSecond { get; set; } = 0.5f;
        public float InitialResource { get; set; } = 10f;
    }

    public sealed class FeedbackConfig
    {
        public int LocalDensitySoftCap { get; set; } = 8;
        public float DensityReproductionPenalty { get; set; } = 0.6f;
        public float StressDrainPerNeighbor { get; set; } = 0.05f;
        public float DiseaseProbabilityPerNeighbor { get; set; } = 0.002f;
        public float DensityReproductionSlope { get; set; } = 0.04f;
        public float BaseDeathProbabilityPerSecond { get; set; } = 0.0005f;
        public float AgeDeathProbabilityPerSecond { get; set; } = 0.00015f;
        public float DensityDeathProbabilityPerNeighborPerSecond { get; set; } = 0.0001f;

        public float GroupFormationWarmupSeconds { get; set; } = 6f;
        public int GroupFormationNeighborThreshold { get; set; } = 3;
        public float GroupFormationChance { get; set; } = 0.02f;
        public int GroupAdoptionNeighborThreshold { get; set; } = 4;
        public float GroupAdoptionChance { get; set; } = 0.003f;
        public int GroupSplitNeighborThreshold { get; set; } = 6;
        public float GroupSplitChance { get; set; } = 0.0015f;
        public float GroupSplitNewGroupChance { get; set; } = 0.5f;
        public float GroupSplitStressThreshold { get; set; } = 0.4f;
        public float GroupBirthSeedChance { get; set; } = 0.35f;
        public float GroupMutationChance { get; set; } = 0.05f;
    }
}
