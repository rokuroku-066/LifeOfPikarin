using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace Terrarium.Sim
{
    public sealed class World
    {
        private const int UngroupedGroupId = -1;

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
        private readonly Dictionary<int, int> _groupCountsScratch = new();
        private readonly List<Agent> _ungroupedNeighbors = new();
        private int _nextId;
        private int _nextGroupId;

        public World(SimulationConfig config)
        {
            _config = config;
            _rng = new DeterministicRng(config.Seed);
            _grid = new SpatialGrid(config.CellSize);
            _environment = new EnvironmentGrid(config.CellSize, config.Environment);
            _nextGroupId = 0;
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
            _nextGroupId = 0;
            BootstrapPopulation();
        }

        public TickMetrics Step(int tick)
        {
            var sw = Stopwatch.StartNew();
            _pendingFoodEvents.Clear();
            _pendingDangerEvents.Clear();
            _pendingPheromoneEvents.Clear();
            var simTime = tick * _config.TimeStep;
            var canFormGroups = simTime >= _config.Feedback.GroupFormationWarmupSeconds;
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

                UpdateGroupMembership(agent, _neighborAgents, canFormGroups);

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

                ApplyLifeCycle(agent, _neighborAgents.Count, ref births, _pendingFoodEvents, _pendingPheromoneEvents, canFormGroups);
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
                _agents.Add(new Agent
                {
                    Id = _nextId++,
                    Generation = 0,
                    GroupId = UngroupedGroupId,
                    Position = pos,
                    Velocity = _rng.NextUnitCircle() * _config.Species.BaseSpeed * 0.3f,
                    Energy = _config.Species.ReproductionEnergyThreshold * _config.Species.InitialEnergyFractionOfThreshold,
                    Age = SampleInitialAge(),
                    State = AgentState.Wander,
                    Alive = true,
                    Stress = 0
                });
                _idToIndex[_nextId - 1] = _agents.Count - 1;
            }
        }

        private float SampleInitialAge()
        {
            var minAge = MathF.Max(0f, _config.Species.InitialAgeMin);
            var defaultMax = MathF.Min(_config.Species.AdultAge, _config.Species.MaxAge * 0.5f);
            var maxAge = _config.Species.InitialAgeMax > 0f
                ? _config.Species.InitialAgeMax
                : defaultMax;
            maxAge = MathF.Max(0f, MathF.Min(maxAge, _config.Species.MaxAge));

            if (maxAge < minAge)
            {
                (minAge, maxAge) = (maxAge, minAge);
            }

            return _rng.NextRange(minAge, maxAge);
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

    private void UpdateGroupMembership(Agent agent, IReadOnlyList<Agent> neighbors, bool canFormGroups)
    {
        var originalGroup = agent.GroupId;
        _groupCountsScratch.Clear();
        _ungroupedNeighbors.Clear();

        var sameGroupNeighbors = 0;
        for (var i = 0; i < neighbors.Count; i++)
        {
            var other = neighbors[i];
            if (other.GroupId == UngroupedGroupId)
            {
                _ungroupedNeighbors.Add(other);
            }

            if (agent.GroupId != UngroupedGroupId && other.GroupId == agent.GroupId)
            {
                sameGroupNeighbors++;
            }

            if (other.GroupId >= 0)
            {
                if (_groupCountsScratch.TryGetValue(other.GroupId, out var count))
                {
                    _groupCountsScratch[other.GroupId] = count + 1;
                }
                else
                {
                    _groupCountsScratch[other.GroupId] = 1;
                }
            }
        }

        var majorityGroup = UngroupedGroupId;
        var majorityCount = 0;
        foreach (var kvp in _groupCountsScratch)
        {
            if (kvp.Value > majorityCount)
            {
                majorityGroup = kvp.Key;
                majorityCount = kvp.Value;
            }
        }

        if (canFormGroups)
        {
            TryFormGroup(agent);
            if (agent.GroupId == originalGroup)
            {
                TryAdoptGroup(agent, majorityGroup, majorityCount);
            }
        }

        TrySplitGroup(agent, sameGroupNeighbors, canFormGroups);

        _groupCountsScratch.Clear();
        _ungroupedNeighbors.Clear();
    }

    private void TryFormGroup(Agent agent)
    {
        if (agent.GroupId != UngroupedGroupId)
        {
            return;
        }

        if (_ungroupedNeighbors.Count < _config.Feedback.GroupFormationNeighborThreshold)
        {
            return;
        }

        if (_rng.NextFloat() >= _config.Feedback.GroupFormationChance)
        {
            return;
        }

        var newGroup = _nextGroupId++;
        AdoptGroup(agent, newGroup);

        var recruits = Math.Min(_ungroupedNeighbors.Count, _config.Feedback.GroupFormationNeighborThreshold + 2);
        for (var i = 0; i < recruits; i++)
        {
            AdoptGroup(_ungroupedNeighbors[i], newGroup);
        }
    }

    private void TryAdoptGroup(Agent agent, int majorityGroup, int majorityCount)
    {
        if (majorityGroup == UngroupedGroupId || agent.GroupId == majorityGroup)
        {
            return;
        }

        if (majorityCount < _config.Feedback.GroupAdoptionNeighborThreshold)
        {
            return;
        }

        if (_rng.NextFloat() < _config.Feedback.GroupAdoptionChance)
        {
            agent.GroupId = majorityGroup;
        }
    }

    private void TrySplitGroup(Agent agent, int sameGroupNeighbors, bool canFormGroups)
    {
        if (agent.GroupId == UngroupedGroupId)
        {
            return;
        }

        if (sameGroupNeighbors < _config.Feedback.GroupSplitNeighborThreshold)
        {
            return;
        }

        if (agent.Stress < _config.Feedback.GroupSplitStressThreshold)
        {
            return;
        }

        if (_rng.NextFloat() < _config.Feedback.GroupSplitChance)
        {
            if (canFormGroups && _rng.NextFloat() < _config.Feedback.GroupSplitNewGroupChance)
            {
                agent.GroupId = _nextGroupId++;
            }
            else
            {
                agent.GroupId = UngroupedGroupId;
            }
        }
    }

    private static void AdoptGroup(Agent agent, int groupId)
    {
        agent.GroupId = groupId;
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
                var groupsDiffer = agent.GroupId != UngroupedGroupId &&
                                   other.GroupId != UngroupedGroupId &&
                                   other.GroupId != agent.GroupId;
                if (groupsDiffer && toOther.LengthSquared < 4f)
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
        var pheromoneGradient = agent.GroupId == UngroupedGroupId
            ? new Vec2(0, 0)
            : PheromoneGradient(agent.GroupId, agent.Position);
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
        if (agent.GroupId == UngroupedGroupId)
        {
            return new Vec2(0, 0);
        }

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
        List<(Vec2 Position, int GroupId, float Amount)> pheromoneEvents,
        bool canCreateGroups)
    {
        var dt = _config.TimeStep;
        var speedCost = agent.Velocity.Length * 0.05f;
        var metabolism = _config.Species.MetabolismPerSecond * dt + speedCost * dt;
        var excessEnergy = MathF.Max(0f, agent.Energy - _config.Species.EnergySoftCap);
        metabolism += excessEnergy * _config.Species.HighEnergyMetabolismSlope * dt;
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
            var densityFactor = 1f;
            if (neighborCount > _config.Feedback.LocalDensitySoftCap)
            {
                var excess = neighborCount - _config.Feedback.LocalDensitySoftCap;
                var drop = excess * _config.Feedback.DensityReproductionSlope;
                densityFactor = MathF.Max(0f, MathF.Min(1f, _config.Feedback.DensityReproductionPenalty - drop));
            }

            var reproductionChance = 0.25f * densityFactor;
            reproductionChance = MathF.Max(0f, MathF.Min(1f, reproductionChance));
            if (_rng.NextFloat() < reproductionChance)
            {
                var childEnergy = agent.Energy * 0.5f;
                agent.Energy -= childEnergy + _config.Species.BirthEnergyCost;
                var childGroup = MutateGroup(agent.GroupId, canCreateGroups);
                if (agent.GroupId == UngroupedGroupId && childGroup != UngroupedGroupId)
                {
                    agent.GroupId = childGroup;
                }
                var child = new Agent
                {
                    Id = _nextId++,
                    Generation = agent.Generation + 1,
                    GroupId = childGroup,
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
                if (childGroup != UngroupedGroupId)
                {
                    pheromoneEvents.Add((agent.Position, childGroup, _config.Environment.PheromoneDepositOnBirth));
                }
            }
        }

        var hazardPerSecond =
            _config.Feedback.BaseDeathProbabilityPerSecond +
            agent.Age * _config.Feedback.AgeDeathProbabilityPerSecond +
            neighborCount * _config.Feedback.DensityDeathProbabilityPerNeighborPerSecond;
        var hazardChance = MathF.Min(1f, hazardPerSecond * dt);
        if (hazardChance > 0f && _rng.NextFloat() < hazardChance)
        {
            agent.Alive = false;
            foodEvents.Add((agent.Position, _config.Environment.FoodFromDeath));
            return;
        }

        if (agent.Energy <= 0 || agent.Age >= _config.Species.MaxAge)
        {
            agent.Alive = false;
            foodEvents.Add((agent.Position, _config.Environment.FoodFromDeath));
        }
    }

    private int MutateGroup(int groupId, bool canCreateGroups)
    {
        if (!canCreateGroups)
        {
            return groupId;
        }

        if (groupId == UngroupedGroupId)
        {
            if (_rng.NextFloat() < _config.Feedback.GroupBirthSeedChance)
            {
                return _nextGroupId++;
            }
            return UngroupedGroupId;
        }

        if (_rng.NextFloat() < _config.Feedback.GroupMutationChance)
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
            if (agent.GroupId != UngroupedGroupId)
            {
                _groupScratch.Add(agent.GroupId);
            }
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
