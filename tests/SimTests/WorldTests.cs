using Terrarium.Sim;
using Xunit;

namespace Terrarium.SimTests;

public class WorldTests
{
    [Fact]
    public void DeterministicRunsProduceSameMetrics()
    {
        var config = new SimulationConfig { Seed = 42, InitialPopulation = 30, MaxPopulation = 200 };
        var worldA = new World(config);
        var worldB = new World(config);

        for (var i = 0; i < 120; i++)
        {
            worldA.Step(i);
            worldB.Step(i);
        }

        Assert.Equal(worldA.Metrics.Entries.Count, worldB.Metrics.Entries.Count);
        for (var i = 0; i < worldA.Metrics.Entries.Count; i++)
        {
            var a = worldA.Metrics.Entries[i] with { TickDurationMs = 0 };
            var b = worldB.Metrics.Entries[i] with { TickDurationMs = 0 };
            Assert.Equal(a, b);
        }
    }

    [Fact]
    public void SpatialGridLimitsNeighborScope()
    {
        var grid = new SpatialGrid(1f);
        grid.Insert(1, new Vec2(0, 0));
        grid.Insert(2, new Vec2(0.5f, 0.5f));
        grid.Insert(3, new Vec2(10, 10));

        var neighbors = grid.GetNeighbors(new Vec2(0.2f, 0.2f), 1.5f);
        Assert.Contains(neighbors, n => n.Id == 1);
        Assert.Contains(neighbors, n => n.Id == 2);
        Assert.DoesNotContain(neighbors, n => n.Id == 3);
    }

    [Fact]
    public void SpatialGridFiltersByVisionRadius()
    {
        var grid = new SpatialGrid(1f);
        grid.Insert(1, new Vec2(0, 0));
        grid.Insert(2, new Vec2(2.9f, 0));

        var close = grid.GetNeighbors(new Vec2(0, 0), 2.5f);
        Assert.Contains(close, n => n.Id == 1);
        Assert.DoesNotContain(close, n => n.Id == 2);
    }

    [Fact]
    public void PopulationRemainsBoundedWithFeedback()
    {
        var config = new SimulationConfig
        {
            Seed = 123,
            InitialPopulation = 50,
            MaxPopulation = 150,
            Feedback = new FeedbackConfig
            {
                LocalDensitySoftCap = 6,
                DensityReproductionPenalty = 0.3f,
                StressDrainPerNeighbor = 0.1f,
                DiseaseProbabilityPerNeighbor = 0.002f
            }
        };

        var world = new World(config);
        for (var i = 0; i < 500; i++)
        {
            world.Step(i);
        }

        Assert.InRange(world.Agents.Count, 5, config.MaxPopulation);
        var metrics = world.Metrics.Entries[world.Metrics.Entries.Count - 1];
        Assert.True(metrics.Population <= config.MaxPopulation);
    }

    [Fact]
    public void DeathsAreCountedOnceWhenAgentsExpire()
    {
        var config = new SimulationConfig
        {
            TimeStep = 0.1f,
            InitialPopulation = 2,
            MaxPopulation = 10,
            Species = new SpeciesConfig
            {
                BaseSpeed = 0f,
                MaxAcceleration = 0f,
                MaxAge = 0.05f,
                MetabolismPerSecond = 0f,
                ReproductionEnergyThreshold = 100f,
                AdultAge = 999f
            }
        };

        var world = new World(config);
        var metrics = world.Step(0);

        Assert.Equal(0, metrics.Births);
        Assert.Equal(2, metrics.Deaths);
        Assert.Empty(world.Agents);
    }
}
