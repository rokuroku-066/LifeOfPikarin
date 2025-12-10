using System;
using System.IO;
using System.Reflection;
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

            var lines = buffer.ToString().Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
            Assert.Equal(11, lines.Length); // header + 10 ticks
            Assert.Equal("tick,population,births,deaths,avgEnergy,avgAge,groups,neighborChecks,tickDurationMs", lines[0]);
            var fields = lines[1].Split(',');
            Assert.Equal(9, fields.Length);
            Assert.Equal("0", fields[0]);
            Assert.True(int.Parse(fields[1]) > 0);
        }

        [Fact]
        public void FoodPatchesRegenerateAndCap()
        {
            var envConfig = new EnvironmentConfig
            {
                FoodPerCell = 10f,
                FoodRegenPerSecond = 1f,
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
            var valueAfterRegen = grid.SampleFood(new Vec2(0, 0));
            Assert.InRange(valueAfterRegen, 6.9f, 7.1f);

            grid.ConsumeFood(new Vec2(0, 0), 6f);
            grid.Tick(1f);
            Assert.InRange(grid.SampleFood(new Vec2(0, 0)), 5.9f, 6.1f);

            grid.Tick(1f);
            Assert.Equal(10f, grid.SampleFood(new Vec2(0, 0)), 3);
        }

        [Fact]
        public void DangerFieldDecaysAndDiffuses()
        {
            var envConfig = new EnvironmentConfig
            {
                FoodPerCell = 0f,
                FoodRegenPerSecond = 0f,
                DangerDiffusionRate = 0.5f,
                DangerDecayRate = 0.1f
            };

            var grid = new EnvironmentGrid(1f, envConfig);
            grid.AddDanger(new Vec2(0, 0), 10f);
            grid.Tick(1f);

            var center = grid.SampleDanger(new Vec2(0, 0));
            var east = grid.SampleDanger(new Vec2(1f, 0));

            Assert.InRange(center, 4.49f, 4.51f);
            Assert.InRange(east, 1.124f, 1.126f);
        }

        [Fact]
        public void PheromoneFieldDiffusesPerGroup()
        {
            var envConfig = new EnvironmentConfig
            {
                FoodPerCell = 0f,
                FoodRegenPerSecond = 0f,
                PheromoneDiffusionRate = 0.5f,
                PheromoneDecayRate = 0.1f
            };

            var grid = new EnvironmentGrid(1f, envConfig);
            grid.AddPheromone(new Vec2(0, 0), groupId: 1, amount: 8f);
            grid.Tick(1f);

            var ownGroupCenter = grid.SamplePheromone(new Vec2(0, 0), 1);
            var otherGroupCenter = grid.SamplePheromone(new Vec2(0, 0), 2);
            var neighbor = grid.SamplePheromone(new Vec2(1f, 0), 1);

            Assert.True(ownGroupCenter > otherGroupCenter);
            Assert.True(neighbor > 0f);
        }

        [Fact]
        public void AgentsFleeFromDangerField()
        {
            var config = new SimulationConfig
            {
                TimeStep = 0.1f,
                InitialPopulation = 1,
                MaxPopulation = 5,
                CellSize = 1f,
                Seed = 9,
                Species = new SpeciesConfig
                {
                    BaseSpeed = 2f,
                    MaxAcceleration = 5f,
                    VisionRadius = 0f,
                    WanderJitter = 0f,
                    MetabolismPerSecond = 0f,
                    BirthEnergyCost = 0f,
                    ReproductionEnergyThreshold = 100f,
                    AdultAge = 999f
                },
                Environment = new EnvironmentConfig
                {
                    FoodPerCell = 0f,
                    FoodRegenPerSecond = 0f,
                    FoodConsumptionRate = 0f,
                    DangerDiffusionRate = 0.2f,
                    DangerDecayRate = 0f,
                    DangerPulseOnFlee = 0f
                }
            };

            var world = new World(config);
            var envField = typeof(World).GetField("_environment", BindingFlags.NonPublic | BindingFlags.Instance)!
                .GetValue(world) as EnvironmentGrid;
            Assert.NotNull(envField);
            envField!.AddDanger(world.Agents[0].Position, 5f);

            world.Step(0);

            Assert.Equal(AgentState.Flee, world.Agents[0].State);
            Assert.True(world.Agents[0].Velocity.Length > 0f);
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
