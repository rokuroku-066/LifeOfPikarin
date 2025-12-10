using System.Globalization;

namespace Terrarium.Sim;

public static class HeadlessRunner
{
    public static void Run(World world, int steps, TextWriter writer, bool includeHeader = true)
    {
        if (includeHeader)
        {
            writer.WriteLine("tick,population,births,deaths,avgEnergy,avgAge,groups,neighborChecks,tickDurationMs");
        }

        for (var tick = 0; tick < steps; tick++)
        {
            var metrics = world.Step(tick);
            writer.WriteLine(string.Join(",", new[]
            {
                metrics.Tick.ToString(CultureInfo.InvariantCulture),
                metrics.Population.ToString(CultureInfo.InvariantCulture),
                metrics.Births.ToString(CultureInfo.InvariantCulture),
                metrics.Deaths.ToString(CultureInfo.InvariantCulture),
                metrics.AverageEnergy.ToString(CultureInfo.InvariantCulture),
                metrics.AverageAge.ToString(CultureInfo.InvariantCulture),
                metrics.Groups.ToString(CultureInfo.InvariantCulture),
                metrics.NeighborChecks.ToString(CultureInfo.InvariantCulture),
                metrics.TickDurationMs.ToString(CultureInfo.InvariantCulture)
            }));
        }
    }
}
