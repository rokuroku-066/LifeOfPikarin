using System;
using System.Collections.Generic;
using Terrarium.Sim;

namespace Terrarium.UnityView
{
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
                    ColorHue = agent.GroupId >= 0 ? (agent.GroupId % 8) / 8f : 0.08f,
                    State = agent.State
                });
            }

            return snapshots;
        }
    }

    public sealed class AgentSnapshot
    {
        public int Id { get; set; }
        public Vec2 Position { get; set; }
        public Vec2 Velocity { get; set; }
        public float Scale { get; set; }
        public float ColorHue { get; set; }
        public AgentState State { get; set; }
    }
}
