namespace Terrarium.Sim;

public sealed class EnvironmentGrid
{
    private readonly float _cellSize;
    private readonly float _maxResource;
    private readonly float _regenPerSecond;
    private readonly Dictionary<(int, int), float> _cells = new();

    public EnvironmentGrid(float cellSize, float initialResource, float regenPerSecond)
    {
        _cellSize = cellSize;
        _maxResource = initialResource;
        _regenPerSecond = regenPerSecond;
    }

    public void Reset()
    {
        _cells.Clear();
    }

    public float Sample(Vec2 position)
    {
        var key = CellKey(position);
        if (_cells.TryGetValue(key, out var value))
        {
            return value;
        }

        _cells[key] = _maxResource * 0.8f;
        return _cells[key];
    }

    public void Consume(Vec2 position, float amount)
    {
        var key = CellKey(position);
        var value = Sample(position);
        value = MathF.Max(0, value - amount);
        _cells[key] = value;
    }

    public void Regen(float deltaTime)
    {
        var keys = _cells.Keys.ToArray();
        foreach (var key in keys)
        {
            var value = _cells[key];
            value = MathF.Min(_maxResource, value + _regenPerSecond * deltaTime);
            _cells[key] = value;
        }
    }

    private (int, int) CellKey(Vec2 position)
    {
        return ((int)MathF.Floor(position.X / _cellSize), (int)MathF.Floor(position.Y / _cellSize));
    }
}
