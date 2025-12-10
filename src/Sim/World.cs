using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace Terrarium.Sim
{
    public sealed class World
    {
        private readonly SimulationConfig _config;
        private readonly DeterministicRng _rng;
        private readonly SpatialGrid _grid;
        private readonly EnvironmentGrid _environment;
        private readonly List<Agent> _agents = new();
        private readonly List<Agent> _birthQueue = new();
        private readonly MetricsBuffer _metrics = new();
        private readonly Dictionary<int, int> _idToIndex = new();
        private readonly List<Vec2> _neighborOffsets = new();
        private readonly List<Agent> _neighborAgents = new();
        private readonly HashSet<int> _groupScratch = new();
        private readonly List<(Vec2 Position, float Amount)> _pendingFoodEvents = new();
        private readonly List<(Vec2 Position, float Amount)> _pendingDangerEvents = new();
        private readonly List<(Vec2 Position, int GroupId, float Amount)> _pendingPheromoneEvents = new();
        private int _nextId;

        public World(SimulationConfig config)
        {
            _config = config;
            _rng = new DeterministicRng(config.Seed);
            _grid = new SpatialGrid(config.CellSize);
            _environment = new EnvironmentGrid(config.CellSize, config.Environment);
            BootstrapPopulation();
        }

        public IReadOnlyList<Agent> Agents => _agents;
        public MetricsBuffer Metrics => _metrics;

        public void Reset()
        {
            _agents.Clear();
            _birthQueue.Clear();
            _environment.Reset();
            _grid.Clear();
            _neighborOffsets.Clear();
            _neighborAgents.Clear();
            _groupScratch.Clear();
            _pendingFoodEvents.Clear();
            _pendingDangerEvents.Clear();
            _pendingPheromoneEvents.Clear();
            _rng.Reset();
            _idToIndex.Clear();
            _metrics.Clear();
            _nextId = 0;
            BootstrapPopulation();
        }

        public TickMetrics Step(int tick)
        {
            var sw = Stopwatch.StartNew();
            _pendingFoodEvents.Clear();
            _pendingDangerEvents.Clear();
            _pendingPheromoneEvents.Clear();
            RefreshIndexMap();
            _grid.Clear();
            for (var i = 0; i < _agents.Count; i++)
            {
                _grid.Insert(_agents[i].Id, _agents[i].Position);
            }

            var neighborChecks = 0;
            var births = 0;
            var deaths = 0;

            for (var i = 0; i < _agents.Count; i++)
            {
                var agent = _agents[i];
                if (!agent.Alive)
                {
                    continue;
                }

                var neighbors = _grid.GetNeighbors(agent.Position, _config.Species.VisionRadius);
                CollectNeighborData(agent, neighbors);
                neighborChecks += _neighborAgents.Count;

                var desired = ComputeDesiredVelocity(agent, _neighborAgents, _neighborOffsets, out var sensedDanger);
                var accel = desired - agent.Velocity;
                var accelMag = accel.Length;
                if (accelMag > _config.Species.MaxAcceleration)
                {
                    accel = accel * (_config.Species.MaxAcceleration / accelMag);
                }

                agent.Velocity += accel * _config.TimeStep;
                var speed = agent.Velocity.Length;
                if (speed > _config.Species.BaseSpeed)
                {
                    agent.Velocity = agent.Velocity * (_config.Species.BaseSpeed / speed);
                }

                agent.Position += agent.Velocity * _config.TimeStep;
                agent.Position = Wrap(agent.Position, _config.WorldSize);
                agent.Age += _config.TimeStep;

                ApplyLifeCycle(agent, _neighborAgents.Count, ref births, _pendingFoodEvents, _pendingPheromoneEvents);
                if (agent.State == AgentState.Flee || sensedDanger)
                {
                    _pendingDangerEvents.Add((agent.Position, _config.Environment.DangerPulseOnFlee));
                }

                _agents[i] = agent;
            }

            ApplyFieldEvents();
            _environment.Tick(_config.TimeStep);
            ApplyBirths();
            RemoveDead(ref deaths);

            sw.Stop();
            var snapshot = CreateMetrics(tick, births, deaths, neighborChecks, (float)sw.Elapsed.TotalMilliseconds);
            _metrics.Add(snapshot);
            return snapshot;
        }

        private void BootstrapPopulation()
        {
            for (var i = 0; i < _config.InitialPopulation; i++)
            {
                var pos = new Vec2(_rng.NextRange(0, _config.WorldSize), _rng.NextRange(0, _config.WorldSize));
                var group = i % 4;
                _agents.Add(new Agent
                {
                    Id = _nextId++,
                    Generation = 0,
                    GroupId = group,
                    Position = pos,
                    Velocity = _rng.NextUnitCircle() * _config.Species.BaseSpeed * 0.3f,
                    Energy = _config.Species.ReproductionEnergyThreshold * 0.5f,
                    Age = 0,
                    State = AgentState.Wander,
                    Alive = true,
                    Stress = 0
                });
                _idToIndex[_nextId - 1] = _agents.Count - 1;
            }
        }

    private void CollectNeighborData(Agent agent, IReadOnlyList<SpatialGrid.GridEntry> neighbors)
    {
        _neighborOffsets.Clear();
        _neighborAgents.Clear();

        foreach (var entry in neighbors)
        {
            if (entry.Id == agent.Id)
            {
                continue;
            }

            var other = TryGetAgent(entry.Id);
            if (other is null || !other.Alive)
            {
                continue;
            }

            _neighborOffsets.Add(entry.Position - agent.Position);
            _neighborAgents.Add(other);
        }
    }

    private Vec2 ComputeDesiredVelocity(
        Agent agent,
        IReadOnlyList<Agent> neighbors,
        IReadOnlyList<Vec2> neighborOffsets,
        out bool sensedDanger)
    {
        var desired = new Vec2(0, 0);
        var fleeVector = new Vec2(0, 0);
        sensedDanger = false;

        for (var i = 0; i < neighbors.Count; i++)
        {
            var other = neighbors[i];
            var toOther = neighborOffsets[i];
            if (other.GroupId != agent.GroupId && toOther.LengthSquared < 4f)
            {
                fleeVector -= toOther.Normalized() * _config.Species.BaseSpeed;
                sensedDanger = true;
            }
        }

        var dangerLevel = _environment.SampleDanger(agent.Position);
        if (dangerLevel > 0.1f)
        {
            sensedDanger = true;
            var dangerGradient = DangerGradient(agent.Position);
            if (dangerGradient.LengthSquared < 1e-4f)
            {
                dangerGradient = _rng.NextUnitCircle();
            }
            fleeVector -= dangerGradient.Normalized() * (_config.Species.BaseSpeed * MathF.Min(1f, dangerLevel));
        }

        if (fleeVector.LengthSquared > 0.001f)
        {
            agent.State = AgentState.Flee;
            return fleeVector;
        }

        var foodHere = _environment.SampleFood(agent.Position);
        var foodGradient = FoodGradient(agent.Position);
        var pheromoneGradient = PheromoneGradient(agent.GroupId, agent.Position);
        var dangerGradientAway = DangerGradient(agent.Position);

        var foodBias = foodGradient.LengthSquared > 1e-4f ? foodGradient.Normalized() : new Vec2(0, 0);
        var pheromoneBias = pheromoneGradient.LengthSquared > 1e-4f ? pheromoneGradient.Normalized() : new Vec2(0, 0);
        var dangerBias = dangerGradientAway.LengthSquared > 1e-4f ? dangerGradientAway.Normalized() : new Vec2(0, 0);

        if (agent.Energy < _config.Species.ReproductionEnergyThreshold * 0.6f ||
            foodHere > _config.Environment.FoodPerCell * 0.5f ||
            foodGradient.LengthSquared > 0.01f)
        {
            agent.State = AgentState.SeekingFood;
            desired += foodBias * (_config.Species.BaseSpeed * 0.4f);
            desired += _rng.NextUnitCircle() * (_config.Species.BaseSpeed * 0.25f);
        }
        else if (agent.Energy > _config.Species.ReproductionEnergyThreshold && agent.Age > _config.Species.AdultAge)
        {
            agent.State = AgentState.SeekingMate;
            desired += Cohesion(neighborOffsets) * (_config.Species.BaseSpeed * 0.8f);
            desired += pheromoneBias * (_config.Species.BaseSpeed * 0.25f);
        }
        else
        {
            agent.State = AgentState.Wander;
            desired += _rng.NextUnitCircle() * (_config.Species.BaseSpeed * _config.Species.WanderJitter);
            desired += pheromoneBias * (_config.Species.BaseSpeed * 0.15f);
        }

        desired += Separation(neighborOffsets) * (_config.Species.BaseSpeed * 1.2f);
        desired += Alignment(agent, neighbors) * (_config.Species.BaseSpeed * 0.3f);
        desired -= dangerBias * (_config.Species.BaseSpeed * 0.2f);
        return desired;
    }

    private static Vec2 Separation(IReadOnlyList<Vec2> neighborVectors)
    {
        if (neighborVectors.Count == 0)
        {
            return new Vec2(0, 0);
        }

        var accum = new Vec2(0, 0);
        foreach (var offset in neighborVectors)
        {
            var distSq = MathF.Max(offset.LengthSquared, 0.1f);
            accum -= offset / distSq;
        }
        return accum.Normalized();
    }

    private Vec2 Alignment(Agent agent, IReadOnlyList<Agent> neighbors)
    {
        var accum = new Vec2(0, 0);
        var count = 0;
        foreach (var other in neighbors)
        {
            if (other.GroupId != agent.GroupId)
            {
                continue;
            }

            accum += other.Velocity;
            count++;
        }

        if (count == 0)
        {
            return new Vec2(0, 0);
        }

        return (accum / count).Normalized();
    }

    private static Vec2 Cohesion(IReadOnlyList<Vec2> neighborVectors)
    {
        if (neighborVectors.Count == 0)
        {
            return new Vec2(0, 0);
        }

        var center = new Vec2(0, 0);
        foreach (var offset in neighborVectors)
        {
            center += offset;
        }
        center = center / neighborVectors.Count;
        return center.Normalized();
    }

    private Vec2 FoodGradient(Vec2 position)
    {
        var step = _config.CellSize;
        var right = _environment.PeekFood(position + new Vec2(step, 0));
        var left = _environment.PeekFood(position + new Vec2(-step, 0));
        var up = _environment.PeekFood(position + new Vec2(0, step));
        var down = _environment.PeekFood(position + new Vec2(0, -step));
        return new Vec2(right - left, up - down);
    }

    private Vec2 PheromoneGradient(int groupId, Vec2 position)
    {
        var step = _config.CellSize;
        var right = _environment.SamplePheromone(position + new Vec2(step, 0), groupId);
        var left = _environment.SamplePheromone(position + new Vec2(-step, 0), groupId);
        var up = _environment.SamplePheromone(position + new Vec2(0, step), groupId);
        var down = _environment.SamplePheromone(position + new Vec2(0, -step), groupId);
        return new Vec2(right - left, up - down);
    }

    private Vec2 DangerGradient(Vec2 position)
    {
        var step = _config.CellSize;
        var right = _environment.SampleDanger(position + new Vec2(step, 0));
        var left = _environment.SampleDanger(position + new Vec2(-step, 0));
        var up = _environment.SampleDanger(position + new Vec2(0, step));
        var down = _environment.SampleDanger(position + new Vec2(0, -step));
        return new Vec2(right - left, up - down);
    }

    private void ApplyLifeCycle(
        Agent agent,
        int neighborCount,
        ref int births,
        List<(Vec2 Position, float Amount)> foodEvents,
        List<(Vec2 Position, int GroupId, float Amount)> pheromoneEvents)
    {
        var dt = _config.TimeStep;
        var speedCost = agent.Velocity.Length * 0.05f;
        var metabolism = _config.Species.MetabolismPerSecond * dt + speedCost * dt;
        var stressDrain = neighborCount * _config.Feedback.StressDrainPerNeighbor * dt;
        agent.Energy -= metabolism + stressDrain + agent.Stress * dt;

        if (neighborCount > _config.Feedback.LocalDensitySoftCap)
        {
            agent.Stress += 0.1f * dt;
            if (_rng.NextFloat() < neighborCount * _config.Feedback.DiseaseProbabilityPerNeighbor * dt)
            {
                agent.Alive = false;
                foodEvents.Add((agent.Position, _config.Environment.FoodFromDeath));
                return;
            }
        }
        else
        {
            agent.Stress = MathF.Max(0, agent.Stress - 0.05f * dt);
        }

        var available = _environment.SampleFood(agent.Position);
        if (available > 0)
        {
            var consumed = MathF.Min(available, _config.Environment.FoodConsumptionRate * dt);
            _environment.ConsumeFood(agent.Position, consumed);
            agent.Energy += consumed;
        }

        if (agent.Energy > _config.Species.ReproductionEnergyThreshold &&
            agent.Age > _config.Species.AdultAge &&
            _agents.Count + _birthQueue.Count < _config.MaxPopulation)
        {
            var densityPenalty = neighborCount > _config.Feedback.LocalDensitySoftCap ? _config.Feedback.DensityReproductionPenalty : 1f;
            if (_rng.NextFloat() < 0.2f * densityPenalty)
            {
                var childEnergy = agent.Energy * 0.5f;
                agent.Energy -= childEnergy + _config.Species.BirthEnergyCost;
                var child = new Agent
                {
                    Id = _nextId++,
                    Generation = agent.Generation + 1,
                    GroupId = MutateGroup(agent.GroupId),
                    Position = agent.Position + _rng.NextUnitCircle() * 0.5f,
                    Velocity = agent.Velocity,
                    Energy = childEnergy,
                    Age = 0,
                    State = AgentState.Wander,
                    Alive = true,
                    Stress = 0
                };
                _birthQueue.Add(child);
                births++;
                pheromoneEvents.Add((agent.Position, agent.GroupId, _config.Environment.PheromoneDepositOnBirth));
            }
        }

        if (agent.Energy <= 0 || agent.Age >= _config.Species.MaxAge)
        {
            agent.Alive = false;
            foodEvents.Add((agent.Position, _config.Environment.FoodFromDeath));
        }
    }

    private int MutateGroup(int groupId)
    {
        if (_rng.NextFloat() < 0.05f)
        {
            var delta = _rng.NextInt(3) - 1;
            return Math.Abs(groupId + delta) % 8;
        }
        return groupId;
    }

    private void ApplyFieldEvents()
    {
        for (var i = 0; i < _pendingFoodEvents.Count; i++)
        {
            var evt = _pendingFoodEvents[i];
            _environment.AddFood(evt.Position, evt.Amount);
        }

        for (var i = 0; i < _pendingDangerEvents.Count; i++)
        {
            var evt = _pendingDangerEvents[i];
            _environment.AddDanger(evt.Position, evt.Amount);
        }

        for (var i = 0; i < _pendingPheromoneEvents.Count; i++)
        {
            var evt = _pendingPheromoneEvents[i];
            _environment.AddPheromone(evt.Position, evt.GroupId, evt.Amount);
        }

        _pendingFoodEvents.Clear();
        _pendingDangerEvents.Clear();
        _pendingPheromoneEvents.Clear();
    }

    private void ApplyBirths()
    {
        foreach (var agent in _birthQueue)
        {
            _agents.Add(agent);
            _idToIndex[agent.Id] = _agents.Count - 1;
        }
        _birthQueue.Clear();
    }

    private void RemoveDead(ref int deaths)
    {
        for (var i = _agents.Count - 1; i >= 0; i--)
        {
            if (!_agents[i].Alive)
            {
                _idToIndex.Remove(_agents[i].Id);
                _agents.RemoveAt(i);
                deaths++;
            }
        }
    }

    private static Vec2 Wrap(Vec2 position, float worldSize)
    {
        var x = position.X;
        var y = position.Y;
        if (x < 0) x += worldSize;
        if (x > worldSize) x -= worldSize;
        if (y < 0) y += worldSize;
        if (y > worldSize) y -= worldSize;
        return new Vec2(x, y);
    }

    private TickMetrics CreateMetrics(int tick, int births, int deaths, int neighborChecks, float durationMs)
    {
        var population = _agents.Count;
        float energySum = 0;
        float ageSum = 0;
        _groupScratch.Clear();

        for (var i = 0; i < _agents.Count; i++)
        {
            var agent = _agents[i];
            energySum += agent.Energy;
            ageSum += agent.Age;
            _groupScratch.Add(agent.GroupId);
        }

        var avgEnergy = population == 0 ? 0 : energySum / population;
        var avgAge = population == 0 ? 0 : ageSum / population;
        return new TickMetrics(tick, population, births, deaths, avgEnergy, avgAge, _groupScratch.Count, neighborChecks, durationMs);
    }

    private Agent? TryGetAgent(int id)
    {
        if (_idToIndex.TryGetValue(id, out var index) && index >= 0 && index < _agents.Count)
        {
            return _agents[index];
        }
        return null;
    }

    private void RefreshIndexMap()
    {
        _idToIndex.Clear();
        for (var i = 0; i < _agents.Count; i++)
        {
            _idToIndex[_agents[i].Id] = i;
        }
    }
}
}
