using System.Collections.Generic;
using UnityEngine;
using Terrarium.Sim;

namespace Terrarium.UnityView
{
    public sealed class TerrariumHost : MonoBehaviour
    {
        [SerializeField]
        private SimulationConfigDto _config = SimulationConfigDto.Default();

        [SerializeField]
        private CubeInstancedRenderer? _renderer;

        private readonly AgentViewMapper _viewMapper = new();
        private World? _world;
        private float _accumulator;
        private int _tick;
        private IReadOnlyList<AgentSnapshot> _latestSnapshots = System.Array.Empty<AgentSnapshot>();

        public IReadOnlyList<AgentSnapshot> LatestSnapshots => _latestSnapshots;
        public World? World => _world;

        private void Awake() => InitializeWorld();

        private void OnEnable()
        {
            if (_world == null)
            {
                InitializeWorld();
            }
        }

        private void Update()
        {
            if (_world is null)
            {
                return;
            }

            var step = Mathf.Max(_config.TimeStep, 0.0001f);
            _accumulator += Time.deltaTime;
            while (_accumulator >= step)
            {
                _world.Step(_tick++);
                _accumulator -= step;
            }

            _latestSnapshots = _viewMapper.Map(_world.Agents);
            _renderer?.Render(_latestSnapshots);
        }

        public void RenderWith(CubeInstancedRenderer renderer)
        {
            if (renderer == null)
            {
                return;
            }

            renderer.Render(_latestSnapshots);
        }

        [ContextMenu("Reinitialize World")]
        public void ReinitializeWorld()
        {
            InitializeWorld();
        }

        private void InitializeWorld()
        {
            _tick = 0;
            _accumulator = 0f;
            _world = new World(_config.ToSimConfig());
            _latestSnapshots = System.Array.Empty<AgentSnapshot>();
        }

        [System.Serializable]
        public sealed class SimulationConfigDto
        {
            [Min(0.001f)]
            public float TimeStep = 1f / 30f;
            public int InitialPopulation = 120;
            public int MaxPopulation = 500;
            public float WorldSize = 100f;
            public float CellSize = 2.5f;
            public int Seed = 1337;
            public SpeciesConfigDto Species = new();
            public EnvironmentConfigDto Environment = new();
            public FeedbackConfigDto Feedback = new();

            public SimulationConfig ToSimConfig()
            {
                var config = new SimulationConfig
                {
                    TimeStep = TimeStep,
                    InitialPopulation = InitialPopulation,
                    MaxPopulation = MaxPopulation,
                    WorldSize = WorldSize,
                    CellSize = CellSize,
                    Seed = Seed,
                    Species = Species.ToSimConfig(),
                    Environment = Environment.ToSimConfig(),
                    Feedback = Feedback.ToSimConfig()
                };

                return config;
            }

            public static SimulationConfigDto Default() => new();
        }

        [System.Serializable]
        public sealed class SpeciesConfigDto
        {
            public float BaseSpeed = 6f;
            public float MaxAcceleration = 20f;
            public float VisionRadius = 6f;
            public float MetabolismPerSecond = 0.8f;
            public float BirthEnergyCost = 8f;
            public float ReproductionEnergyThreshold = 15f;
            public float AdultAge = 8f;
            public float MaxAge = 120f;
            public float WanderJitter = 0.45f;

            public SpeciesConfig ToSimConfig()
            {
                return new SpeciesConfig
                {
                    BaseSpeed = BaseSpeed,
                    MaxAcceleration = MaxAcceleration,
                    VisionRadius = VisionRadius,
                    MetabolismPerSecond = MetabolismPerSecond,
                    BirthEnergyCost = BirthEnergyCost,
                    ReproductionEnergyThreshold = ReproductionEnergyThreshold,
                    AdultAge = AdultAge,
                    MaxAge = MaxAge,
                    WanderJitter = WanderJitter
                };
            }
        }

        [System.Serializable]
        public sealed class EnvironmentConfigDto
        {
            public float ResourcePerCell = 10f;
            public float ResourceRegenPerSecond = 0.5f;
            public float ConsumptionRate = 5f;
            public List<ResourcePatchDto> ResourcePatches = new();
            public float HazardDiffusionRate = 0f;
            public float HazardDecayRate = 0f;
            public float PheromoneDiffusionRate = 0f;
            public float PheromoneDecayRate = 0f;

            public EnvironmentConfig ToSimConfig()
            {
                var patches = new List<ResourcePatchConfig>(ResourcePatches.Count);
                for (var i = 0; i < ResourcePatches.Count; i++)
                {
                    patches.Add(ResourcePatches[i].ToSimConfig());
                }

                return new EnvironmentConfig
                {
                    ResourcePerCell = ResourcePerCell,
                    ResourceRegenPerSecond = ResourceRegenPerSecond,
                    ConsumptionRate = ConsumptionRate,
                    ResourcePatches = patches,
                    HazardDiffusionRate = HazardDiffusionRate,
                    HazardDecayRate = HazardDecayRate,
                    PheromoneDiffusionRate = PheromoneDiffusionRate,
                    PheromoneDecayRate = PheromoneDecayRate
                };
            }
        }

        [System.Serializable]
        public sealed class ResourcePatchDto
        {
            public Vector2 Position = Vector2.zero;
            public float Radius = 5f;
            public float ResourcePerCell = 10f;
            public float RegenPerSecond = 0.5f;
            public float InitialResource = 10f;

            public ResourcePatchConfig ToSimConfig()
            {
                return new ResourcePatchConfig
                {
                    Position = new Vec2(Position.x, Position.y),
                    Radius = Radius,
                    ResourcePerCell = ResourcePerCell,
                    RegenPerSecond = RegenPerSecond,
                    InitialResource = InitialResource
                };
            }
        }

        [System.Serializable]
        public sealed class FeedbackConfigDto
        {
            public int LocalDensitySoftCap = 8;
            public float DensityReproductionPenalty = 0.6f;
            public float StressDrainPerNeighbor = 0.05f;
            public float DiseaseProbabilityPerNeighbor = 0.0015f;

            public FeedbackConfig ToSimConfig()
            {
                return new FeedbackConfig
                {
                    LocalDensitySoftCap = LocalDensitySoftCap,
                    DensityReproductionPenalty = DensityReproductionPenalty,
                    StressDrainPerNeighbor = StressDrainPerNeighbor,
                    DiseaseProbabilityPerNeighbor = DiseaseProbabilityPerNeighbor
                };
            }
        }
    }
}
