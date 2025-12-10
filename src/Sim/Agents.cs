using System;
using System.Collections.Generic;

namespace Terrarium.Sim
{
    public enum AgentState
    {
        Idle,
        SeekingFood,
        SeekingMate,
        Flee,
        Wander
    }

    public sealed class Agent
    {
        public int Id { get; set; }
        public int Generation { get; set; }
        public int GroupId { get; set; }
        public Vec2 Position { get; set; }
        public Vec2 Velocity { get; set; }
        public float Energy { get; set; }
        public float Age { get; set; }
        public AgentState State { get; set; }
        public bool Alive { get; set; } = true;
        public float Stress { get; set; }
    }

    public sealed class TickMetrics : IEquatable<TickMetrics>
    {
        public TickMetrics(
            int tick,
            int population,
            int births,
            int deaths,
            float averageEnergy,
            float averageAge,
            int groups,
            int neighborChecks,
            float tickDurationMs)
        {
            Tick = tick;
            Population = population;
            Births = births;
            Deaths = deaths;
            AverageEnergy = averageEnergy;
            AverageAge = averageAge;
            Groups = groups;
            NeighborChecks = neighborChecks;
            TickDurationMs = tickDurationMs;
        }

        public int Tick { get; set; }
        public int Population { get; set; }
        public int Births { get; set; }
        public int Deaths { get; set; }
        public float AverageEnergy { get; set; }
        public float AverageAge { get; set; }
        public int Groups { get; set; }
        public int NeighborChecks { get; set; }
        public float TickDurationMs { get; set; }

        public bool Equals(TickMetrics? other)
        {
            if (other is null)
            {
                return false;
            }

            return Tick == other.Tick &&
                   Population == other.Population &&
                   Births == other.Births &&
                   Deaths == other.Deaths &&
                   MathF.Abs(AverageEnergy - other.AverageEnergy) < 1e-4f &&
                   MathF.Abs(AverageAge - other.AverageAge) < 1e-4f &&
                   Groups == other.Groups &&
                   NeighborChecks == other.NeighborChecks &&
                   MathF.Abs(TickDurationMs - other.TickDurationMs) < 1e-4f;
        }

        public override bool Equals(object? obj)
        {
            return Equals(obj as TickMetrics);
        }

        public override int GetHashCode()
        {
            var hash = new HashCode();
            hash.Add(Tick);
            hash.Add(Population);
            hash.Add(Births);
            hash.Add(Deaths);
            hash.Add(AverageEnergy);
            hash.Add(AverageAge);
            hash.Add(Groups);
            hash.Add(NeighborChecks);
            hash.Add(TickDurationMs);
            return hash.ToHashCode();
        }
    }

    public sealed class MetricsBuffer
    {
        private readonly List<TickMetrics> _entries = new();

        public IReadOnlyList<TickMetrics> Entries => _entries;

        public void Add(TickMetrics metrics)
        {
            _entries.Add(metrics);
        }

        public void Clear()
        {
            _entries.Clear();
        }
    }
}
