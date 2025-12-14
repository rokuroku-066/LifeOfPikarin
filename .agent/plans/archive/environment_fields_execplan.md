# Environment resource patches and fields

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Implement explicit environment resource patches with configurable spawn positions and regeneration, plus optional hazard and pheromone scalar fields that diffuse and decay over time. Expose controls in EnvironmentConfig and update World stepping to tick regeneration/decay regardless of sampling so long-run simulations remain stable and deterministic. Unit tests should confirm regeneration, consumption, and hazard decay behaviors.

## Progress

- [x] (2024-05-26 00:10Z) Drafted ExecPlan and surveyed existing EnvironmentGrid/World/tests structure.
- [x] (2024-05-26 00:45Z) Extend EnvironmentConfig with resource patch, hazard, and pheromone parameters.
- [x] (2024-05-26 01:15Z) Refactor EnvironmentGrid to manage patches plus hazard/pheromone fields with regeneration/diffusion/decay tick.
- [x] (2024-05-26 01:25Z) Update World to initialize EnvironmentGrid from config and tick environment systems each step.
- [x] (2024-05-26 01:35Z) Add unit tests for resource regeneration/consumption and hazard decay.
- [x] (2024-05-26 01:45Z) Run test suite and summarize results (blocked: dotnet SDK not installed in container).
- [x] (2025-12-10 20:38Z) Run `dotnet test tests/SimTests/SimTests.csproj` on Windows (.NET 8.416); all tests passing.
- [x] (2024-05-26 02:00Z) Review outcomes and finalize documentation in this plan.

## Surprises & Discoveries

- None observed during implementation; environment refactor compiled conceptually without unexpected constraints.
- Initial work was blocked on `dotnet test` due to missing SDK; later verified on Windows with .NET 8.416 (tests pass).
- Added a small follow-up to avoid per-tick allocations when regenerating resources by reusing a preallocated key list.

## Decision Log

- Decision: Model hazard/pheromone diffusion by decaying concentration then spreading a configurable fraction equally to the four orthogonal neighbors while retaining the remainder.
  Rationale: Keeps computation local and deterministic without O(N²) interactions, matching design constraints.
  Date/Author: 2024-05-26 / assistant
- Decision: Represent resource cells with per-cell caps and regen rates, initialized via optional patches that preseed cells so regeneration occurs even without sampling.
  Rationale: Satisfies requirement for explicit patches and independent regeneration while keeping dictionary-backed storage lightweight.
  Date/Author: 2024-05-26 / assistant

## Outcomes & Retrospective

- Implemented configurable resource patches plus hazard/pheromone fields with diffusion and decay hooks in EnvironmentGrid and World.
- Added unit tests for regeneration and hazard behavior; now validated on Windows (.NET 8.416) with `dotnet test tests/SimTests/SimTests.csproj` passing.

## Context and Orientation

- Relevant files: `src/Sim/Environment.cs` (EnvironmentGrid implementation), `src/Sim/World.cs` (simulation step and environment usage), `src/Sim/Configs.cs` (EnvironmentConfig fields), `tests/SimTests/WorldTests.cs` (unit tests).
- Simulation and visualization must remain separated; World steps deterministic simulation independent of rendering.
- Neighbor interactions use `SpatialGrid` to avoid O(N²) scans; maintain this approach.
- Long-run stability relies on resource regeneration, feedback penalties, and deterministic RNG seeded via config.

## Plan of Work

Describe, in prose, the sequence of edits and additions.
1. Expand EnvironmentConfig with parameters for resource patches (spawn rate/positions), regeneration caps independent of sampling, hazard and pheromone field controls (enabled flag, diffusion rate, decay rate).
2. Redesign EnvironmentGrid to:
   - Initialize resource patches at specified coordinates with configurable spawn radius/amounts.
   - Track resource values per cell with caps and deterministic regeneration per tick regardless of sampling.
   - Maintain optional hazard and pheromone scalar fields on the same grid, applying diffusion/decay each tick.
   - Provide sampling/consumption APIs used by agents, plus tick method to update regeneration and fields.
3. Update World construction and Step to pass new config data, initialize patches, and tick environment each timestep before/after agent actions as appropriate.
4. Implement unit tests covering: resource regeneration without sampling, consumption reducing values, hazard decay/diffusion over ticks. Use deterministic config and inspect EnvironmentGrid state via public APIs.
5. Run `dotnet test tests/SimTests/SimTests.csproj` and capture results.

## Concrete Steps

- Edit `src/Sim/Configs.cs` to add new EnvironmentConfig properties with defaults and any helper records for patch definitions.
- Modify `src/Sim/Environment.cs` to implement new EnvironmentGrid behavior, including constructors taking patch definitions, tick method for regeneration/diffusion/decay, and APIs for hazard/pheromone interaction.
- Update `src/Sim/World.cs` to use new EnvironmentGrid constructor parameters, call environment tick each step, and adjust sampling/consumption calls if signatures change.
- Extend `tests/SimTests/WorldTests.cs` with focused tests for regeneration, consumption, and hazard decay/diffusion.
- Run `dotnet test tests/SimTests/SimTests.csproj` from repo root.

## Validation and Acceptance

- Deterministic smoke run: instantiate World with seeded SimulationConfig and run several ticks ensuring population metrics remain deterministic (existing test covers this).
- Resource regeneration: test should verify that a cell with partial resource regenerates up to cap even if not sampled again, and consumption reduces value accordingly.
- Hazard decay/diffusion: test hazard field initialized at a cell decays and diffuses to neighbors per diffusion/decay rates over ticks.
- Performance: changes should avoid per-tick allocations in tight loops and keep grid dictionary reuse; expect Phase 1 to handle hundreds of agents with millisecond tick times.
- Long-run stability: resources capped and regenerated deterministically; hazard decay prevents runaway accumulation; no O(N²) loops introduced.
- Sim/View separation: changes confined to simulation core; no rendering dependencies added.

## Idempotence and Recovery

- Edits are plain text; git commit provides rollback. Running tests is safe to repeat.
- EnvironmentGrid reset methods should allow repeated simulation runs without stale state.

## Artifacts and Notes

(Include key logs or snippets if helpful as work proceeds.)

## Interfaces and Dependencies

- EnvironmentGrid should expose methods like `Sample`, `Consume`, `AddHazard`, `SampleHazard`, `Tick` (or equivalent) operating on grid coordinates.
- EnvironmentConfig should include structures for resource patch definitions and field parameters with deterministic defaults.
