# ExecPlan: Build simulation and visualization codebase matching docs/DESIGN.md

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: Maintain this plan in accordance with `.agent/PLANS.md` from the repository root.

## Purpose / Big Picture

Deliver a runnable Phase 1 simulation and visualization stack that fulfills the behaviors described in `docs/DESIGN.md`: deterministic, fixed-timestep cube-based agents that move, grow, reproduce, and die while naturally forming multiple colonies under negative feedback controls and spatially local interactions. The resulting code should provide a Unity-friendly Simulation/View separation so that future FBX replacement requires only View-layer swaps. A new contributor should be able to run headless or in-editor simulations, observe population metrics over long durations, and see overhead-camera visuals of grouped cube agents.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here.
- [x] (2025-12-10 02:19Z) Drafted initial ExecPlan covering simulation, view, validation, and stability requirements.
- [x] (2025-12-10 02:35Z) Discovered `dotnet` SDK missing in container; proceeded with manual project scaffolding per plan.
- [x] (2025-12-10 03:05Z) Implemented core Simulation (World, SpatialGrid, EnvironmentGrid, lifecycle, AI/steering heuristics) with deterministic RNG and metrics buffer.
- [x] (2025-12-10 03:20Z) Added Unity-facing AgentViewMapper DTOs and SimTests validating determinism, locality, and bounded populations.
- [x] (2025-12-10 03:55Z) Reviewed DESIGN.md vs. implementation; tightened SpatialGrid to respect vision radius, removed per-tick allocations in neighbor processing, and expanded tests for locality.
- [x] (2025-12-10 04:25Z) Installed dotnet-sdk-8.0, ran `dotnet test`, and aligned deterministic comparisons to ignore wall-clock tick duration noise.
- [x] (2025-12-10 05:00Z) Re-reviewed DESIGN.md/ExecPlan alignment, fixed death metric double-counting with regression coverage, added solution scaffolding for Sim/View/Tests, and reran tests.
- [x] (2025-05-18 12:00Z) Corrected `World.Reset` to rebuild deterministic RNG/environment/grid state and clear transient caches so restarted runs mirror new world construction.
- [x] (2025-12-10 05:25Z) Added headless `SimRunner` console app plus `HeadlessRunner` helper, documented usage, and covered CSV emission via regression tests.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation, with brief evidence. Populate as work progresses.

- Container initially lacked `dotnet` CLI, so solution/project files and tests were authored manually without restore/build until the SDK was installed.
- Stopwatch-based `TickDurationMs` fluctuates across runs; deterministic comparisons should mask this measurement noise.

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: Proceed with manual .csproj and code layout despite missing SDK.
  Rationale: Keep momentum and provide deterministic Sim/View scaffolding aligning with DESIGN.md; unblock reviewers even without local builds.
  Date/Author: 2025-12-10 / Codex

- Decision: Use dictionary-based ID lookup to keep neighbor access O(1) and avoid Find-based O(N²) behavior.
  Rationale: Preserve locality guarantees and performance expectations.
  Date/Author: 2025-12-10 / Codex

- Decision: Exclude `TickDurationMs` from deterministic equality checks while keeping it for performance logging.
  Rationale: Wall-clock measurements vary between runs even with fixed seeds; excluding the field preserves deterministic state validation.
  Date/Author: 2025-12-10 / Codex

- Decision: Count deaths only during removal to avoid double-reporting lifecycle outcomes.
  Rationale: Marking agents dead during lifecycle and also during removal inflated death metrics; removal-time counting matches observed removals.
  Date/Author: 2025-12-10 / Codex

- Decision: Add a solution file that binds Sim, UnityView, and SimTests for easier onboarding and tooling support.
  Rationale: Aligns with ExecPlan concrete steps and reduces friction for contributors opening the workspace.
  Date/Author: 2025-12-10 / Codex

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or completion. Compare the result against the original purpose.

- Current codebase now enforces vision-radius neighbor filtering and reuses scratch buffers to reduce per-tick allocations, improving adherence to performance and O(N²)-avoidance goals.
- Remaining gaps: Unity runtime host/renderer still unimplemented; performance microbenchmarks and Unity visual artifacts should be produced once runtime harness exists.
- Added solution scaffolding, lifecycle metric fixes, and a headless runner; stability feedbacks remain in place, but Unity render loop is still outstanding.

## Context and Orientation

Current repo contains only `docs/DESIGN.md`; no simulation or Unity scaffolding exists yet. The design mandates:
- Strict Simulation/View separation: Simulation Core owns state updates; View reads state and never blocks or mutates Sim.
- No O(N²) logic: neighbor queries must use a SpatialGrid/local neighborhood only.
- Long-run stability via negative feedback: energy metabolism, density stress, disease probability, resource depletion/regeneration, reproduction suppression, and global population caps.
- Determinism and reproducibility: seedable RNG, fixed timestep scheduling, and no non-deterministic sources.
- Phase 1 scope is cube-based GPU instancing with minimal per-agent objects; Phase 2 will swap View to FBX without touching Sim.

Key target structure (can be adjusted if needed):
- `src/Sim/` for engine-agnostic C# simulation core (WorldManager, EntityManager, SpatialGrid, EnvironmentSystem, AISystem, SteeringSystem, LifeCycleSystem, metrics logging, deterministic RNG wrapper).
- `src/Unity/` for Unity integration (MonoBehaviours to host simulation loop, GPU-instanced cube renderer, View data buffers, overhead camera rig, configuration ScriptableObjects, editor utilities).
- `tests/` for simulation unit/integration tests and deterministic regression runs.
- `docs/` already holds design; add runbooks/readmes if needed.

## Plan of Work

Describe, in prose, the sequence of edits and additions with file-level pointers.

1) Bootstrap solution and shared infrastructure
- Create a .NET/Unity-friendly solution layout with projects for `Sim`, `Unity`, and `Tests`. Include deterministic RNG helper, config files, and shared math/utilities (vector structs, bounds, timers).
- Add build scripts or README for both `dotnet` (headless tests) and Unity package/assembly definitions.

2) Implement Simulation Core (engine-agnostic in `src/Sim/`)
- WorldManager: fixed timestep scheduler, seed initialization, orchestrates subsystem updates in deterministic order.
- EntityManager: manages pooled agent data arrays/structs, birth/death queues, ID reuse, global population cap enforcement.
- SpatialGrid: hash grid with fixed cell size, supports insert/update/removal per tick and 3×3 neighborhood queries; avoids allocations and LINQ in hot paths.
- EnvironmentSystem: manages resource patches (spawn/regenerate/deplete), pheromone/nest fields, hazard/density heatmaps; updates per-cell metrics.
- AISystem: utility-based scoring of desires (hunger, reproduction, safety), FSM state transitions with hysteresis, and action selection using local neighbors and environment samples only.
- SteeringSystem: compute Seek/Wander/Separation/Alignment/Cohesion/Avoid forces, weighting by group tag similarity; output desired velocity/heading respecting max speed/acceleration.
- LifeCycleSystem: apply energy metabolism, growth/aging, reproduction checks (including density-based suppression), disease/stress effects, and death handling; enqueue births for EntityManager.
- Metrics/Logging: per-tick counters (population, births/deaths, group counts per tag, average energy/age, neighbor checks, tick time) written to a deterministic log buffer and optionally CSV/JSON.

3) Implement View layer for Phase 1 cubes (`src/Unity/`)
- AgentViewMapper: project Simulation agent data to GPU instancing buffers (position, heading, scale, color from group tag/energy, state ID). Ensure read-only interaction.
- Rendering pipeline: instanced mesh renderer (graphics API abstracted for tests), overhead camera setup, framerate-independent interpolation of transforms between sim ticks.
- Config UI/ScriptableObjects: expose sim parameters (cell size, max population, energy rates, resource spawn, pheromone decay, steering weights, RNG seed) for easy tuning.
- Scene host MonoBehaviour: drives fixed timestep simulation loop independent from render frame rate, forwards simulation output to renderer.

4) Provide headless runners and tests (`tests/`)
- Deterministic smoke test: run N steps with fixed seed and assert identical metrics snapshot/CSV hash across runs.
- Behavior tests: verify SpatialGrid neighbor counts, reproduction suppression when dense, disease probability triggers, energy depletion without resources, and multi-colony emergence signals (distinct tag clusters).
- Performance microbenchmarks: measure tick time for 1k/5k/10k agents; ensure within documented budget on reference hardware or CI.

5) Documentation and runbooks
- Add READMEs for running headless tests (`dotnet test`) and Unity scenes; include seed/config examples and metrics interpretation.
- Provide manual visual validation steps: run Unity scene with overhead camera for extended time, observe colony formation, density-based dispersal, and stable population oscillations.

6) Milestones and incremental deliverables
- Milestone A: Simulation scaffolding + deterministic RNG + SpatialGrid with unit tests.
- Milestone B: LifeCycle/AIS/Steering integrated with metrics logging; headless deterministic smoke test passes.
- Milestone C: Unity View integration with GPU-instanced cubes; visual sanity check instructions ready.
- Milestone D: Performance/stability tuning and final documentation updates.

## Concrete Steps

State exact commands and expected locations; update as work progresses.
- Initialize solution from repository root:
  - dotnet new sln -n Terrarium
  - dotnet new classlib -n Sim -o src/Sim
  - dotnet new classlib -n UnityView -o src/Unity
  - dotnet new xunit -n SimTests -o tests/SimTests
  - dotnet sln add src/Sim/Sim.csproj src/Unity/UnityView.csproj tests/SimTests/SimTests.csproj
- Add package references (for example):
  - In Sim: add System.Numerics, deterministic RNG package or custom implementation.
  - In UnityView: reference Sim project; include Unity assembly definition guidance (documented for Unity import).
  - In SimTests: reference Sim and test helpers.
- Implement subsystems in `src/Sim/` per Plan of Work with accompanying tests in `tests/SimTests`.
- Provide headless runner (console app or test) that loads config JSON/ScriptableObject equivalent and runs fixed-step simulation, writing metrics to `artifacts/metrics.csv`.
- For Unity integration, add instructions for creating a Unity project and copying `src/Sim` as a UPM package or assembly definition along with `src/Unity` scripts and instancing shader/material.

## Validation and Acceptance

Describe deterministic and visual checks the user can run.
- Deterministic smoke run: from repo root, run
    dotnet test tests/SimTests/SimTests.csproj --filter DeterministicSmoke
  Expect identical metrics hashes/log snapshots across repeated runs with the same seed and timestep.
- Spatial locality: tests verify neighbor queries use 3×3 cells only; log neighbor checks count proportional to local density, not global population.
- Long-run stability: headless run for at least 20,000 ticks with seed S logs bounded population (never zero, never exceeding cap), oscillating but stable averages for energy/age, and density-triggered disease/reproduction suppression events.
- Performance sanity: microbenchmark logs average tick time at or below target (document hardware). Example targets: ≤0.5 ms for 1k agents, ≤3 ms for 5k agents on reference CPU; no per-tick allocations observed.
- Visual sanity (Phase 1): in Unity scene, overhead camera shows multiple colonies (distinct tag colors) forming around resource/nest clusters; over time, crowded regions disperse due to penalties, and agents continue moving smoothly via interpolated transforms.
- Explicit separation check: code review ensures View reads Simulation state via DTOs/buffers without mutating core; no waits on animations to progress simulation.
- No O(N²) check: tests and code structure confirm SpatialGrid limits interaction scope; performance counters recorded.

## Idempotence and Recovery

Most steps are repeatable: rerunning dotnet commands regenerates projects; config files can be reloaded. Use Git to checkpoint milestones. If Unity import fails, delete Library/obj directories and retry. Keep seeds/config snapshots so deterministic tests can be rerun. Avoid migrations that mutate data formats without backward-compatible loaders; version configs if formats change.

## Artifacts and Notes

Capture key outputs as implementation proceeds:
- Metrics CSV/JSON samples for deterministic runs and long-run stability tests.
- Performance benchmark logs with hardware specs.
- Screenshots or short clips of Unity overhead view showing multi-colony formation.
Include paths and brief descriptions when added.

## Interfaces and Dependencies

Be prescriptive about final interfaces:
- Simulation data structs: AgentData (position, velocity, heading, energy, age, groupTag, stateId, flags), CellData (resource, pheromone, hazard), Config structs (timestep, energy rates, reproduction thresholds, caps, cell size).
- Subsystem APIs: SpatialGrid (Insert/Update/Remove/GetNeighbors), WorldManager (Step, Reset, LoadConfig), AISystem (EvaluateDesires, SelectAction), SteeringSystem (ComputeSteering), LifeCycleSystem (ApplyMetabolism, HandleReproduction, ApplyStressAndDisease).
- View contracts: read-only snapshot or buffer export from Sim (e.g., NativeArray/ComputeBuffer-ready structs) consumed by instanced renderer; color/scale mapping functions based on groupTag/energy/state.
- External dependencies: System.Numerics for math, potential deterministic RNG library (or custom XorShift/PCG), Unity Graphics API for instancing (MaterialPropertyBlock/Graphics.DrawMeshInstancedIndirect) documented for integration.

Extra acceptance checklist (repo-specific):
- Performance sanity check: specify target agent counts and measured tick times; ensure logs capture tick time and neighbor checks without allocations.
- Long-run stability check: verify negative feedbacks (density stress, disease, resource depletion, reproduction suppression, global cap) keep population bounded and avoid extinction.
- No O(N²) explicit note: SpatialGrid-based neighbor queries only; per-agent loops scan current and adjacent cells.
- Sim/View separation explicit note: Simulation state mutates only inside Sim systems; View receives copies/buffers and never blocks fixed-step progression.
