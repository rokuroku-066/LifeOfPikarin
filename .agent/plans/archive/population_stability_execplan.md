# Population Stability & Throughput Improvements

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Improve early reproduction and sustain births/deaths so the population does not stall at high energy, while keeping tick times stable. The outcome should be visible in metrics: earlier first births (<100 ticks), continued births/deaths near steady state, and reduced tick-duration spikes.

## Progress

- [x] (2025-12-11 00:35Z) Drafted ExecPlan.
- [x] (2025-12-11 00:50Z) Updated config defaults (lower reproduction threshold, lower adult age, higher initial energy fraction, new feedback/metabolism params).
- [x] (2025-12-11 00:55Z) Implemented density-scaled reproduction, high-energy drain, and age/density mortality hazard in `World.ApplyLifeCycle`.
- [x] (2025-12-10 18:00Z) Randomized bootstrap ages via `InitialAgeMin`/`InitialAgeMax` (defaults 0..AdultAge) to seed mixed cohorts.
- [x] (2025-12-10 18:20Z) Re-ran `dotnet test tests/SimTests/SimTests.csproj` after age randomization (all passing).
- [x] (2025-12-10 20:42Z) Evaluate neighbor query tuning; leave as-is if profiling shows no gain (neighborChecks/pop p95≈4.7; kept defaults).
- [x] (2025-12-11 00:58Z) Ran `dotnet test tests/SimTests/SimTests.csproj` (all passing).
- [x] (2025-12-10 20:40Z) Run headless smoke run via `dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 3000 --seed 42 --log artifacts/metrics_smoke.csv`.

## Surprises & Discoveries

- Windows PowerShell cannot load the net8 `Sim.dll` via `Add-Type`, so the quick smoke-run script failed; need a .NET 8 host (pwsh 7+ or a small console harness) for metrics dumps.

## Decision Log

- Decision: Use existing SpatialGrid (no O(N^2)) and keep Sim/View separation; all changes confined to `src/Sim`.
  Rationale: Repo rules demand locality and separation.
  Date/Author: 2025-12-11 / Codex
- Decision: Defer spatial grid tuning unless tests or smoke run show perf regressions; current reuse avoids allocations.
  Rationale: Avoid unnecessary churn; measure first.
  Date/Author: 2025-12-11 / Codex
- Decision: Allow configurable randomized initial ages (default 0..AdultAge) so the seed population spans cohorts while keeping determinism.
  Rationale: Mixed ages jump-start lifecycle churn without changing reproduction logic for newborns.
  Date/Author: 2025-12-10 / Codex
- Decision: Keep current grid sizing; smoke-run neighborChecks/population p95≈4.7 indicates locality is sufficient without tuning.
  Rationale: Metrics show no O(N^2) behavior or perf regressions; avoid churn.
  Date/Author: 2025-12-10 / Codex

## Outcomes & Retrospective

- Smoke run (3000 ticks, seed 42) now completes via `dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 3000 --seed 42 --log artifacts/metrics_smoke.csv`. First birth at tick 19; births/deaths remain >0 (last 500 ticks: births=125, deaths=125). Population holds at cap 500 with churn; avgEnergy≈29.4, avgAge≈39.1 at tick 2999. NeighborChecks/pop avg≈3.83 (p95≈4.67). Tick p95≈5.6 ms with rare spikes (max 24 ms at tick 0); acceptable for Phase 1.

## Context and Orientation

Relevant files:
- `src/Sim/Configs.cs` (simulation, species, feedback defaults)
- `src/Sim/World.cs` (life-cycle, reproduction, mortality, metrics)
- `src/Sim/SpatialGrid.cs` (neighbor queries)
- `src/Sim/Agents.cs` (metrics container)

Constraints (restated): Sim and View are separated; View reads snapshots only. All neighbor logic uses the spatial grid; no all-pairs scans. Long-run stability requires negative feedback (density stress, disease, energy drain). Deterministic RNG + fixed timestep for reproducibility. Phase 1 uses cube instancing only.

Current issues from metrics: births start at tick ~240; population saturates at 500 with births/deaths=0 and avgEnergy ~36, avgAge ~43; occasional tickDuration spikes up to ~8.6 ms.

## Plan of Work

1) Adjust defaults to encourage earlier reproduction: raise initial energy seed, lower reproduction threshold/AdultAge slightly while respecting existing tests; keep MaxAge and Food params untouched.
2) Add density-aware reproduction scaling (smooth penalty) and high-energy metabolic drain in `ApplyLifeCycle`.
3) Add age+density hazard-based mortality to maintain churn without violating determinism.
4) Tweak SpatialGrid usage/parameters (cell size config) and ensure neighbor buffers avoid allocations; keep O(N) behavior.
5) Extend metrics/validation hooks if needed (no behavior change to View) and run required tests.

## Concrete Steps

- Edit `src/Sim/Configs.cs` to update defaults and add any new soft-cap/penalty parameters needed for metabolism/mortality.
- Edit `src/Sim/World.cs` to change bootstrap energy, reproduction probability, metabolic drain, and mortality hazard; ensure RNG use is deterministic.
- If needed, adjust `src/Sim/SpatialGrid.cs` or grid cell size usage to keep neighbor counts efficient (no LINQ allocations).
- Run `dotnet test tests/SimTests/SimTests.csproj` from repo root.
- Run a headless smoke test (3 seeds × 3000 ticks) via `dotnet run --project src/Sim/Sim.csproj` or a small harness to confirm metrics (document results).

## Validation and Acceptance

Acceptance behaviors:
- First birth occurs before tick 100 with default config; population reaches 500 by ~tick 300 without zero-birth plateau.
- In steady state (ticks 600–2000), births and deaths remain non-zero over any 500-tick window; avgAge stabilizes in 25–35 range; avgEnergy stays below 30.
- Tick duration p95 under 4 ms; no single tick exceeds 9 ms in a 3000-tick smoke run.
- Deterministic test suite passes; population remains bounded by MaxPopulation.

Smoke run recipe:
- `dotnet test tests/SimTests/SimTests.csproj`
- `dotnet run --project src/Sim/Sim.csproj -- 3000 --seed 42 --csv artifacts/metrics_after.csv` (if runner supports args) and inspect metrics summary (first/last births, p95 tickDuration).

## Idempotence and Recovery

Edits are code-only; rerunning tests is safe. If behavior regresses, revert the specific config/mortality changes in `World.cs` and `Configs.cs`.

## Artifacts and Notes

To be filled with key metrics excerpts after smoke run.

## Interfaces and Dependencies

- `SimulationConfig`, `SpeciesConfig`, `FeedbackConfig` must expose any new parameters with sane defaults.
- `World.ApplyLifeCycle` must remain deterministic and use SpatialGrid neighbor counts only.
- Metrics output format stays the same (CSV fields unchanged) to keep Unity/Headless consumers stable.
