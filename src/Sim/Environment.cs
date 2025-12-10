using System;
using System.Collections.Generic;

namespace Terrarium.Sim;

public sealed class EnvironmentGrid
{
    private readonly float _cellSize;
    private readonly float _defaultMaxResource;
    private readonly float _defaultRegenPerSecond;
    private readonly float _defaultInitialResource;
    private readonly float _hazardDiffusionRate;
    private readonly float _hazardDecayRate;
    private readonly float _pheromoneDiffusionRate;
    private readonly float _pheromoneDecayRate;
    private readonly IReadOnlyList<ResourcePatchConfig> _patches;

    private readonly Dictionary<(int, int), ResourceCell> _resourceCells = new();
    private readonly List<(int, int)> _resourceCellKeys = new();
    private readonly Dictionary<(int, int), float> _hazardField = new();
    private readonly Dictionary<(int, int), float> _hazardBuffer = new();
    private readonly Dictionary<(int, int), float> _pheromoneField = new();
    private readonly Dictionary<(int, int), float> _pheromoneBuffer = new();

    public EnvironmentGrid(float cellSize, EnvironmentConfig config)
    {
        _cellSize = cellSize;
        _defaultMaxResource = config.ResourcePerCell;
        _defaultRegenPerSecond = config.ResourceRegenPerSecond;
        _defaultInitialResource = MathF.Min(config.ResourcePerCell, config.ResourcePerCell * 0.8f);
        _hazardDiffusionRate = config.HazardDiffusionRate;
        _hazardDecayRate = config.HazardDecayRate;
        _pheromoneDiffusionRate = config.PheromoneDiffusionRate;
        _pheromoneDecayRate = config.PheromoneDecayRate;
        _patches = config.ResourcePatches ?? Array.Empty<ResourcePatchConfig>();

        InitializePatches();
    }

    public void Reset()
    {
        _resourceCells.Clear();
        _resourceCellKeys.Clear();
        _hazardField.Clear();
        _hazardBuffer.Clear();
        _pheromoneField.Clear();
        _pheromoneBuffer.Clear();
        InitializePatches();
    }

    public float Sample(Vec2 position)
    {
        var key = CellKey(position);
        if (!_resourceCells.TryGetValue(key, out var cell))
        {
            cell = new ResourceCell
            {
                Value = _defaultInitialResource,
                Max = _defaultMaxResource,
                RegenPerSecond = _defaultRegenPerSecond
            };
            _resourceCells[key] = cell;
        }

        return cell.Value;
    }

    public void Consume(Vec2 position, float amount)
    {
        var key = CellKey(position);
        if (!_resourceCells.TryGetValue(key, out var cell))
        {
            cell = new ResourceCell
            {
                Value = _defaultInitialResource,
                Max = _defaultMaxResource,
                RegenPerSecond = _defaultRegenPerSecond
            };
        }

        cell.Value = MathF.Max(0, cell.Value - amount);
        _resourceCells[key] = cell;
    }

    public void AddHazard(Vec2 position, float amount)
    {
        var key = CellKey(position);
        if (_hazardField.TryGetValue(key, out var value))
        {
            _hazardField[key] = value + amount;
        }
        else
        {
            _hazardField[key] = amount;
        }
    }

    public float SampleHazard(Vec2 position)
    {
        var key = CellKey(position);
        return _hazardField.TryGetValue(key, out var value) ? value : 0f;
    }

    public void AddPheromone(Vec2 position, float amount)
    {
        var key = CellKey(position);
        if (_pheromoneField.TryGetValue(key, out var value))
        {
            _pheromoneField[key] = value + amount;
        }
        else
        {
            _pheromoneField[key] = amount;
        }
    }

    public float SamplePheromone(Vec2 position)
    {
        var key = CellKey(position);
        return _pheromoneField.TryGetValue(key, out var value) ? value : 0f;
    }

    public void Tick(float deltaTime)
    {
        RegenResources(deltaTime);
        if (_hazardDiffusionRate > 0 || _hazardDecayRate > 0)
        {
            DiffuseField(_hazardField, _hazardBuffer, _hazardDiffusionRate, _hazardDecayRate, deltaTime);
        }
        if (_pheromoneDiffusionRate > 0 || _pheromoneDecayRate > 0)
        {
            DiffuseField(_pheromoneField, _pheromoneBuffer, _pheromoneDiffusionRate, _pheromoneDecayRate, deltaTime);
        }
    }

    private void RegenResources(float deltaTime)
    {
        _resourceCellKeys.Clear();
        foreach (var key in _resourceCells.Keys)
        {
            _resourceCellKeys.Add(key);
        }

        for (var i = 0; i < _resourceCellKeys.Count; i++)
        {
            var key = _resourceCellKeys[i];
            var cell = _resourceCells[key];
            cell.Value = MathF.Min(cell.Max, cell.Value + cell.RegenPerSecond * deltaTime);
            _resourceCells[key] = cell;
        }
    }

    private void InitializePatches()
    {
        if (_patches == null || _patches.Count == 0)
        {
            return;
        }

        foreach (var patch in _patches)
        {
            var minX = (int)MathF.Floor((patch.Position.X - patch.Radius) / _cellSize);
            var maxX = (int)MathF.Floor((patch.Position.X + patch.Radius) / _cellSize);
            var minY = (int)MathF.Floor((patch.Position.Y - patch.Radius) / _cellSize);
            var maxY = (int)MathF.Floor((patch.Position.Y + patch.Radius) / _cellSize);

            for (var x = minX; x <= maxX; x++)
            {
                for (var y = minY; y <= maxY; y++)
                {
                    var cellCenter = new Vec2((x + 0.5f) * _cellSize, (y + 0.5f) * _cellSize);
                    if ((cellCenter - patch.Position).Length > patch.Radius)
                    {
                        continue;
                    }

                    var key = (x, y);
                    var value = MathF.Min(patch.ResourcePerCell, patch.InitialResource);
                    var cell = new ResourceCell
                    {
                        Value = value,
                        Max = patch.ResourcePerCell,
                        RegenPerSecond = patch.RegenPerSecond
                    };

                    if (_resourceCells.TryGetValue(key, out var existing))
                    {
                        cell.Value = MathF.Max(existing.Value, cell.Value);
                        cell.Max = MathF.Max(existing.Max, cell.Max);
                        cell.RegenPerSecond = MathF.Max(existing.RegenPerSecond, cell.RegenPerSecond);
                    }

                    _resourceCells[key] = cell;
                }
            }
        }
    }

    private static void DiffuseField(
        Dictionary<(int, int), float> field,
        Dictionary<(int, int), float> buffer,
        float diffusionRate,
        float decayRate,
        float deltaTime)
    {
        buffer.Clear();
        foreach (var kvp in field)
        {
            var value = kvp.Value;
            if (value <= 0)
            {
                continue;
            }

            var decayed = value * MathF.Max(0f, 1f - decayRate * deltaTime);
            var spreadPortion = decayed * MathF.Min(1f, diffusionRate * deltaTime);
            var remain = decayed - spreadPortion;
            var share = spreadPortion * 0.25f;

            Accumulate(buffer, kvp.Key, remain);
            Accumulate(buffer, (kvp.Key.Item1 + 1, kvp.Key.Item2), share);
            Accumulate(buffer, (kvp.Key.Item1 - 1, kvp.Key.Item2), share);
            Accumulate(buffer, (kvp.Key.Item1, kvp.Key.Item2 + 1), share);
            Accumulate(buffer, (kvp.Key.Item1, kvp.Key.Item2 - 1), share);
        }

        field.Clear();
        foreach (var kvp in buffer)
        {
            if (kvp.Value > 1e-4f)
            {
                field[kvp.Key] = kvp.Value;
            }
        }
        buffer.Clear();
    }

    private static void Accumulate(Dictionary<(int, int), float> buffer, (int, int) key, float value)
    {
        if (value <= 0)
        {
            return;
        }

        if (buffer.TryGetValue(key, out var existing))
        {
            buffer[key] = existing + value;
        }
        else
        {
            buffer[key] = value;
        }
    }

    private (int, int) CellKey(Vec2 position)
    {
        return ((int)MathF.Floor(position.X / _cellSize), (int)MathF.Floor(position.Y / _cellSize));
    }

    private struct ResourceCell
    {
        public float Value { get; set; }
        public float Max { get; set; }
        public float RegenPerSecond { get; set; }
    }
}
