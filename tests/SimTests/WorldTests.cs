using System.IO;
using Terrarium.Sim;
using Xunit;

namespace Terrarium.SimTests
{
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
                var a = CreateComparableMetrics(worldA.Metrics.Entries[i]);
                var b = CreateComparableMetrics(worldB.Metrics.Entries[i]);
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

        [Fact]
        public void HeadlessRunnerWritesMetricsCsv()
        {
            var config = new SimulationConfig { Seed = 7, InitialPopulation = 5, MaxPopulation = 20 };
            var world = new World(config);
            using var buffer = new StringWriter();

            HeadlessRunner.Run(world, 10, buffer, includeHeader: true);

            var lines = buffer.ToString().Trim().Split('\n');
            Assert.Equal(11, lines.Length); // header + 10 ticks
            Assert.Equal("tick,population,births,deaths,avgEnergy,avgAge,groups,neighborChecks,tickDurationMs", lines[0]);
            var fields = lines[1].Split(',');
            Assert.Equal(9, fields.Length);
            Assert.Equal("0", fields[0]);
            Assert.True(int.Parse(fields[1]) > 0);
        }

        [Fact]
        public void ResourcePatchesRegenerateAndCap()
        {
            var envConfig = new EnvironmentConfig
            {
                ResourcePerCell = 10f,
                ResourceRegenPerSecond = 1f,
                ResourcePatches = new[]
                {
                    new ResourcePatchConfig
                    {
                        Position = new Vec2(0, 0),
                        Radius = 1f,
                        ResourcePerCell = 10f,
                        RegenPerSecond = 5f,
                        InitialResource = 2f
                    }
                }
            };

            var grid = new EnvironmentGrid(1f, envConfig);
            grid.Tick(1f); // regen applies without sampling
            var valueAfterRegen = grid.Sample(new Vec2(0, 0));
            Assert.InRange(valueAfterRegen, 6.9f, 7.1f);

            grid.Consume(new Vec2(0, 0), 6f);
            grid.Tick(1f);
            Assert.InRange(grid.Sample(new Vec2(0, 0)), 5.9f, 6.1f);

            grid.Tick(1f);
            Assert.Equal(10f, grid.Sample(new Vec2(0, 0)), 3);
        }

        [Fact]
        public void HazardFieldDecaysAndDiffuses()
        {
            var envConfig = new EnvironmentConfig
            {
                ResourcePerCell = 0f,
                ResourceRegenPerSecond = 0f,
                HazardDiffusionRate = 0.5f,
                HazardDecayRate = 0.1f
            };

            var grid = new EnvironmentGrid(1f, envConfig);
            grid.AddHazard(new Vec2(0, 0), 10f);
            grid.Tick(1f);

            var center = grid.SampleHazard(new Vec2(0, 0));
            var east = grid.SampleHazard(new Vec2(1f, 0));

            Assert.InRange(center, 4.49f, 4.51f);
            Assert.InRange(east, 1.124f, 1.126f);
        }

        private static TickMetrics CreateComparableMetrics(TickMetrics source)
        {
            return new TickMetrics(
                source.Tick,
                source.Population,
                source.Births,
                source.Deaths,
                source.AverageEnergy,
                source.AverageAge,
                source.Groups,
                source.NeighborChecks,
                0);
        }
    }
}
