using Terrarium.Sim;

namespace Terrarium.UnityView;

public sealed class AgentViewMapper
{
    public IReadOnlyList<AgentSnapshot> Map(IReadOnlyList<Agent> agents)
    {
        var snapshots = new List<AgentSnapshot>(agents.Count);
        foreach (var agent in agents)
        {
            if (!agent.Alive)
            {
                continue;
            }

            snapshots.Add(new AgentSnapshot
            {
                Id = agent.Id,
                Position = agent.Position,
                Velocity = agent.Velocity,
                Scale = 1f + MathF.Min(1.5f, agent.Age * 0.05f),
                ColorHue = (agent.GroupId % 8) / 8f,
                State = agent.State
            });
        }

        return snapshots;
    }
}

public sealed record AgentSnapshot
{
    public int Id { get; init; }
    public Vec2 Position { get; init; }
    public Vec2 Velocity { get; init; }
    public float Scale { get; init; }
    public float ColorHue { get; init; }
    public AgentState State { get; init; }
}
