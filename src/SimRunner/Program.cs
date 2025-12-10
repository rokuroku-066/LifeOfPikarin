using System.Globalization;
using Terrarium.Sim;

var options = RunnerOptions.Parse(args);
var config = options.ToSimulationConfig();
var world = new World(config);

using var writer = options.OpenWriter();
HeadlessRunner.Run(world, options.Steps, writer, includeHeader: true);

Console.WriteLine($"Ran {options.Steps} ticks | Seed={options.Seed} | Output={options.LogPath}");

internal sealed record RunnerOptions(int Steps, int Seed, string LogPath, int InitialPopulation, int MaxPopulation)
{
    public static RunnerOptions Parse(string[] args)
    {
        var steps = 2000;
        var seed = 1337;
        var logPath = "artifacts/metrics.csv";
        var initialPopulation = 120;
        var maxPopulation = 500;

        for (var i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--steps" when i + 1 < args.Length:
                    steps = int.Parse(args[++i], CultureInfo.InvariantCulture);
                    break;
                case "--seed" when i + 1 < args.Length:
                    seed = int.Parse(args[++i], CultureInfo.InvariantCulture);
                    break;
                case "--log" when i + 1 < args.Length:
                    logPath = args[++i];
                    break;
                case "--initial" when i + 1 < args.Length:
                    initialPopulation = int.Parse(args[++i], CultureInfo.InvariantCulture);
                    break;
                case "--max" when i + 1 < args.Length:
                    maxPopulation = int.Parse(args[++i], CultureInfo.InvariantCulture);
                    break;
            }
        }

        return new RunnerOptions(steps, seed, logPath, initialPopulation, maxPopulation);
    }

    public SimulationConfig ToSimulationConfig()
    {
        return new SimulationConfig
        {
            Seed = Seed,
            InitialPopulation = InitialPopulation,
            MaxPopulation = MaxPopulation
        };
    }

    public StreamWriter OpenWriter()
    {
        var directory = Path.GetDirectoryName(LogPath);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        return new StreamWriter(File.Open(LogPath, FileMode.Create, FileAccess.Write, FileShare.Read));
    }
}
