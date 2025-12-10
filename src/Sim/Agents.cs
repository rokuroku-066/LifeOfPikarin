namespace Terrarium.Sim;

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
    public int Id { get; init; }
    public int Generation { get; init; }
    public int GroupId { get; init; }
    public Vec2 Position { get; set; }
    public Vec2 Velocity { get; set; }
    public float Energy { get; set; }
    public float Age { get; set; }
    public AgentState State { get; set; }
    public bool Alive { get; set; } = true;
    public float Stress { get; set; }
}

public sealed record TickMetrics(int Tick,
    int Population,
    int Births,
    int Deaths,
    float AverageEnergy,
    float AverageAge,
    int Groups,
    int NeighborChecks,
    float TickDurationMs);

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
