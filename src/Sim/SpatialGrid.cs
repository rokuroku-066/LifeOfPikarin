namespace Terrarium.Sim;

public sealed class SpatialGrid
{
    public readonly struct GridEntry
    {
        public GridEntry(int id, Vec2 position)
        {
            Id = id;
            Position = position;
        }

        public int Id { get; }
        public Vec2 Position { get; }
    }

    private readonly float _cellSize;
    private readonly Dictionary<(int, int), List<GridEntry>> _cells = new();
    private readonly List<GridEntry> _neighborScratch = new();

    public SpatialGrid(float cellSize)
    {
        _cellSize = cellSize;
    }

    public void Clear()
    {
        foreach (var bucket in _cells.Values)
        {
            bucket.Clear();
        }
    }

    public void Insert(int agentId, Vec2 position)
    {
        var key = CellKey(position);
        if (!_cells.TryGetValue(key, out var list))
        {
            list = new List<GridEntry>();
            _cells[key] = list;
        }
        list.Add(new GridEntry(agentId, position));
    }

    public IReadOnlyList<GridEntry> GetNeighbors(Vec2 position, float radius)
    {
        _neighborScratch.Clear();

        var baseKey = CellKey(position);
        var range = (int)MathF.Ceiling(radius / _cellSize);
        var radiusSq = radius * radius;

        for (var dx = -range; dx <= range; dx++)
        {
            for (var dy = -range; dy <= range; dy++)
            {
                var key = (baseKey.Item1 + dx, baseKey.Item2 + dy);
                if (!_cells.TryGetValue(key, out var list))
                {
                    continue;
                }

                foreach (var entry in list)
                {
                    var offset = entry.Position - position;
                    if (offset.LengthSquared <= radiusSq)
                    {
                        _neighborScratch.Add(entry);
                    }
                }
            }
        }

        return _neighborScratch;
    }

    private (int, int) CellKey(Vec2 position)
    {
        return ((int)MathF.Floor(position.X / _cellSize), (int)MathF.Floor(position.Y / _cellSize));
    }
}
