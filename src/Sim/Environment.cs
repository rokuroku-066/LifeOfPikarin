using System;
using System.Collections.Generic;

namespace Terrarium.Sim
{
    public sealed class EnvironmentGrid
    {
        private const float Epsilon = 1e-4f;

        private readonly float _cellSize;
        private readonly float _defaultMaxFood;
        private readonly float _defaultFoodRegenPerSecond;
        private readonly float _defaultInitialFood;
        private readonly float _foodDiffusionRate;
        private readonly float _foodDecayRate;
        private readonly float _pheromoneDiffusionRate;
        private readonly float _pheromoneDecayRate;
        private readonly float _dangerDiffusionRate;
        private readonly float _dangerDecayRate;
        private readonly IReadOnlyList<ResourcePatchConfig> _patches;

        private readonly Dictionary<(int, int), FoodCell> _foodCells = new();
        private readonly List<(int, int)> _foodCellKeys = new();
        private readonly Dictionary<(int, int), float> _foodBuffer = new();
        private readonly Dictionary<(int, int), float> _dangerField = new();
        private readonly Dictionary<(int, int), float> _dangerBuffer = new();
        private readonly Dictionary<(int, int, int), float> _pheromoneField = new();
        private readonly Dictionary<(int, int, int), float> _pheromoneBuffer = new();

        public EnvironmentGrid(float cellSize, EnvironmentConfig config)
        {
            _cellSize = cellSize;
            _defaultMaxFood = config.FoodPerCell;
            _defaultFoodRegenPerSecond = config.FoodRegenPerSecond;
            _defaultInitialFood = MathF.Min(config.FoodPerCell, config.FoodPerCell * 0.8f);
            _foodDiffusionRate = config.FoodDiffusionRate;
            _foodDecayRate = config.FoodDecayRate;
            _pheromoneDiffusionRate = config.PheromoneDiffusionRate;
            _pheromoneDecayRate = config.PheromoneDecayRate;
            _dangerDiffusionRate = config.DangerDiffusionRate;
            _dangerDecayRate = config.DangerDecayRate;
            _patches = config.ResourcePatches ?? Array.Empty<ResourcePatchConfig>();

            InitializePatches();
        }

        public void Reset()
        {
            _foodCells.Clear();
            _foodCellKeys.Clear();
            _foodBuffer.Clear();
            _dangerField.Clear();
            _dangerBuffer.Clear();
            _pheromoneField.Clear();
            _pheromoneBuffer.Clear();
            InitializePatches();
        }

        public float SampleFood(Vec2 position)
        {
            var key = CellKey(position);
            var cell = GetOrCreateFoodCell(key);
            _foodCells[key] = cell;
            return cell.Value;
        }

        public float PeekFood(Vec2 position)
        {
            var key = CellKey(position);
            return _foodCells.TryGetValue(key, out var cell) ? cell.Value : 0f;
        }

        public void ConsumeFood(Vec2 position, float amount)
        {
            var key = CellKey(position);
            var cell = GetOrCreateFoodCell(key);
            cell.Value = MathF.Max(0, cell.Value - amount);
            _foodCells[key] = cell;
        }

        public void AddFood(Vec2 position, float amount)
        {
            if (amount <= 0)
            {
                return;
            }

            var key = CellKey(position);
            var cell = GetOrCreateFoodCell(key, initialValue: 0f);
            cell.Value = MathF.Min(cell.Max, cell.Value + amount);
            _foodCells[key] = cell;
        }

        public float SampleDanger(Vec2 position)
        {
            var key = CellKey(position);
            return _dangerField.TryGetValue(key, out var value) ? value : 0f;
        }

        public void AddDanger(Vec2 position, float amount)
        {
            var key = CellKey(position);
            Accumulate(_dangerField, key, amount);
        }

        public float SamplePheromone(Vec2 position, int groupId)
        {
            var key = CellKey(position);
            var fieldKey = (key.Item1, key.Item2, groupId);
            return _pheromoneField.TryGetValue(fieldKey, out var value) ? value : 0f;
        }

        public void AddPheromone(Vec2 position, int groupId, float amount)
        {
            var key = CellKey(position);
            var fieldKey = (key.Item1, key.Item2, groupId);
            Accumulate(_pheromoneField, fieldKey, amount);
        }

        public void Tick(float deltaTime)
        {
            RegenFood(deltaTime);
            DiffuseFood(deltaTime);
            if (_dangerDiffusionRate > 0 || _dangerDecayRate > 0)
            {
                DiffuseField(_dangerField, _dangerBuffer, _dangerDiffusionRate, _dangerDecayRate, deltaTime);
            }
            if (_pheromoneDiffusionRate > 0 || _pheromoneDecayRate > 0)
            {
                DiffuseField(_pheromoneField, _pheromoneBuffer, _pheromoneDiffusionRate, _pheromoneDecayRate, deltaTime);
            }
        }

        private void RegenFood(float deltaTime)
        {
            _foodCellKeys.Clear();
            foreach (var key in _foodCells.Keys)
            {
                _foodCellKeys.Add(key);
            }

            for (var i = 0; i < _foodCellKeys.Count; i++)
            {
                var key = _foodCellKeys[i];
                var cell = _foodCells[key];
                cell.Value = MathF.Min(cell.Max, cell.Value + cell.RegenPerSecond * deltaTime);
                _foodCells[key] = cell;
            }
        }

        private void DiffuseFood(float deltaTime)
        {
            if (_foodDiffusionRate <= 0 && _foodDecayRate <= 0)
            {
                return;
            }

            _foodBuffer.Clear();
            _foodCellKeys.Clear();
            foreach (var key in _foodCells.Keys)
            {
                _foodCellKeys.Add(key);
            }

            for (var i = 0; i < _foodCellKeys.Count; i++)
            {
                var key = _foodCellKeys[i];
                var cell = _foodCells[key];
                if (cell.Value <= 0)
                {
                    continue;
                }

                var decayed = cell.Value * MathF.Max(0f, 1f - _foodDecayRate * deltaTime);
                var spreadPortion = decayed * MathF.Min(1f, _foodDiffusionRate * deltaTime);
                var remain = decayed - spreadPortion;
                var share = spreadPortion * 0.25f;

                Accumulate(_foodBuffer, key, remain);
                Accumulate(_foodBuffer, (key.Item1 + 1, key.Item2), share);
                Accumulate(_foodBuffer, (key.Item1 - 1, key.Item2), share);
                Accumulate(_foodBuffer, (key.Item1, key.Item2 + 1), share);
                Accumulate(_foodBuffer, (key.Item1, key.Item2 - 1), share);
            }

            foreach (var kvp in _foodBuffer)
            {
                if (kvp.Value <= Epsilon)
                {
                    continue;
                }

                var cell = GetOrCreateFoodCell(kvp.Key, createIfMissing: true, initialValue: 0f);
                cell.Value = MathF.Min(cell.Max, kvp.Value);
                _foodCells[kvp.Key] = cell;
            }

            for (var i = 0; i < _foodCellKeys.Count; i++)
            {
                var key = _foodCellKeys[i];
                var hasValue = _foodBuffer.TryGetValue(key, out var value);
                if ((hasValue && value > Epsilon) || _foodCells[key].RegenPerSecond > 0f)
                {
                    if (!hasValue || value <= Epsilon)
                    {
                        var cell = _foodCells[key];
                        cell.Value = 0f;
                        _foodCells[key] = cell;
                    }

                    continue;
                }

                _foodCells.Remove(key);
            }

            _foodBuffer.Clear();
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
                        var cell = new FoodCell
                        {
                            Value = value,
                            Max = patch.ResourcePerCell,
                            RegenPerSecond = patch.RegenPerSecond
                        };

                        if (_foodCells.TryGetValue(key, out var existing))
                        {
                            cell.Value = MathF.Max(existing.Value, cell.Value);
                            cell.Max = MathF.Max(existing.Max, cell.Max);
                            cell.RegenPerSecond = MathF.Max(existing.RegenPerSecond, cell.RegenPerSecond);
                        }

                        _foodCells[key] = cell;
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
                if (kvp.Value > Epsilon)
                {
                    field[kvp.Key] = kvp.Value;
                }
            }
            buffer.Clear();
        }

        private static void DiffuseField(
            Dictionary<(int, int, int), float> field,
            Dictionary<(int, int, int), float> buffer,
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

                var key = kvp.Key;
                Accumulate(buffer, key, remain);
                Accumulate(buffer, (key.Item1 + 1, key.Item2, key.Item3), share);
                Accumulate(buffer, (key.Item1 - 1, key.Item2, key.Item3), share);
                Accumulate(buffer, (key.Item1, key.Item2 + 1, key.Item3), share);
                Accumulate(buffer, (key.Item1, key.Item2 - 1, key.Item3), share);
            }

            field.Clear();
            foreach (var kvp in buffer)
            {
                if (kvp.Value > Epsilon)
                {
                    field[kvp.Key] = kvp.Value;
                }
            }
            buffer.Clear();
        }

        private FoodCell GetOrCreateFoodCell((int, int) key, bool createIfMissing = true, float? initialValue = null)
        {
            if (_foodCells.TryGetValue(key, out var cell))
            {
                return cell;
            }

            if (!createIfMissing)
            {
                return default;
            }

            cell = new FoodCell
            {
                Value = initialValue ?? _defaultInitialFood,
                Max = _defaultMaxFood,
                RegenPerSecond = _defaultFoodRegenPerSecond
            };
            return cell;
        }

        private (int, int) CellKey(Vec2 position)
        {
            return ((int)MathF.Floor(position.X / _cellSize), (int)MathF.Floor(position.Y / _cellSize));
        }

        private static void Accumulate<TKey>(Dictionary<TKey, float> buffer, TKey key, float value) where TKey : notnull
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

        private struct FoodCell
        {
            public float Value { get; set; }
            public float Max { get; set; }
            public float RegenPerSecond { get; set; }
        }
    }
}
