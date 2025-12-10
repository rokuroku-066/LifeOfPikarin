using System;

namespace Terrarium.Sim;

public sealed record SimulationConfig
{
    public float TimeStep { get; init; } = 1f / 30f;
    public int InitialPopulation { get; init; } = 120;
    public int MaxPopulation { get; init; } = 500;
    public float WorldSize { get; init; } = 100f;
    public float CellSize { get; init; } = 2.5f;
    public int Seed { get; init; } = 1337;
    public SpeciesConfig Species { get; init; } = new();
    public EnvironmentConfig Environment { get; init; } = new();
    public FeedbackConfig Feedback { get; init; } = new();
}

public sealed record SpeciesConfig
{
    public float BaseSpeed { get; init; } = 6f;
    public float MaxAcceleration { get; init; } = 20f;
    public float VisionRadius { get; init; } = 6f;
    public float MetabolismPerSecond { get; init; } = 0.8f;
    public float BirthEnergyCost { get; init; } = 8f;
    public float ReproductionEnergyThreshold { get; init; } = 15f;
    public float AdultAge { get; init; } = 8f;
    public float MaxAge { get; init; } = 120f;
    public float WanderJitter { get; init; } = 0.45f;
}

public sealed record EnvironmentConfig
{
    public float ResourcePerCell { get; init; } = 10f;
    public float ResourceRegenPerSecond { get; init; } = 0.5f;
    public float ConsumptionRate { get; init; } = 5f;
    public IReadOnlyList<ResourcePatchConfig> ResourcePatches { get; init; } = Array.Empty<ResourcePatchConfig>();
    public float HazardDiffusionRate { get; init; } = 0f;
    public float HazardDecayRate { get; init; } = 0f;
    public float PheromoneDiffusionRate { get; init; } = 0f;
    public float PheromoneDecayRate { get; init; } = 0f;
}

public sealed record ResourcePatchConfig
{
    public Vec2 Position { get; init; } = new(0, 0);
    public float Radius { get; init; } = 5f;
    public float ResourcePerCell { get; init; } = 10f;
    public float RegenPerSecond { get; init; } = 0.5f;
    public float InitialResource { get; init; } = 10f;
}

public sealed record FeedbackConfig
{
    public int LocalDensitySoftCap { get; init; } = 8;
    public float DensityReproductionPenalty { get; init; } = 0.6f;
    public float StressDrainPerNeighbor { get; init; } = 0.05f;
    public float DiseaseProbabilityPerNeighbor { get; init; } = 0.0015f;
}
