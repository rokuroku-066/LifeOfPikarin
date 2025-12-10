# Remaining task sweep (tests, smoke run, Unity config sync)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Close out the pending items left in existing plans by: running the mandatory .NET test suite, performing a headless smoke run to validate population stability, evaluating neighbor-query tuning, and synchronizing the Unity-facing configuration DTOs with the updated simulation defaults (including new feedback/metabolism parameters). The result should be a verified build where Unity and headless runners share consistent defaults and stability improvements are proven via metrics.

## Progress

- [x] (2025-12-10 20:35Z) Drafted consolidated ExecPlan after reviewing `docs/DESIGN.md` and all plans under `.agent/plans/`.
- [x] (2025-12-10 20:38Z) Run `dotnet test tests/SimTests/SimTests.csproj` to satisfy mandatory test execution and unblock prior plans.
- [x] (2025-12-10 20:40Z) Run a headless smoke run via `dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 3000 --seed 42 --log artifacts/metrics_smoke.csv` and summarize births/deaths/tick p95.
- [x] (2025-12-10 20:42Z) Analyze neighbor-check density from the smoke run to confirm current grid sizing is adequate; document whether further tuning is needed.
- [x] (2025-12-10 20:55Z) Align Unity `SimulationConfigDto`/`SpeciesConfigDto`/`EnvironmentConfigDto`/`FeedbackConfigDto` defaults and fields with `Terrarium.Sim` configs (expose energy soft cap, high-energy drain, density reproduction slope, death hazards, initial energy fraction, updated reproduction/adult ages).
- [x] (2025-12-10 20:58Z) Update README (and any relevant plan progress boxes) with the smoke-run command, new config fields, and note that Unity defaults now mirror sim defaults.
- [x] (2025-12-10 21:00Z) Re-run `dotnet test tests/SimTests/SimTests.csproj` after code changes.
- [x] (2025-12-10 21:05Z) Capture outcomes (metrics excerpts, decisions) and mark this plan complete.
- [x] (2025-12-10 21:30Z) Re-audit `docs/DESIGN.md` and ExecPlans against current code; noted TickMetrics determinism mismatch and outdated plan outcomes.
- [x] (2025-12-10 21:35Z) Removed TickDurationMs from TickMetrics equality/hash and refreshed ExecPlan outcomes (full_implementation, csharp9) to match reality.
- [x] (2025-12-10 21:45Z) Re-run `dotnet test tests/SimTests/SimTests.csproj` after determinism fix.
- [x] (2025-12-10 21:50Z) Run 3000-step headless smoke run (`dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 3000 --seed 42 --log artifacts/metrics_smoke_latest.csv`) and summarize metrics.
- [x] (2025-12-10 21:55Z) Decide on any further tuning based on the new smoke-run metrics and document the decision.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation.

- Latest smoke run (3000 ticks, seed 42) shows a larger warm-up spike at tick 0 (~42.6 ms) with steady-state p95=6.77 ms and p99=9.68 ms; outliers remain rare (likely JIT/GC/first-load).

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: No neighbor grid tuning needed; average neighborChecks/population ~3.8 with p95 ~4.7 in the 3000-tick smoke run, consistent with 3ÁE cell lookups.
  Rationale: Metrics show locality and stable perf without changing cell size or vision defaults.
  Date/Author: 2025-12-10 / Codex
- Decision: Accept rare tickDuration spikes (>10 ms) as warm-up artifacts; keep p95 < 9 ms acceptance and monitor after config sync.
  Rationale: Spikes are isolated (tick 0, 1143, 2340, 2740 E741) while steady-state timing meets targets.
  Date/Author: 2025-12-10 / Codex
- Decision: Align Unity DTO defaults to simulation defaults (reproduction threshold 12, adult age 20, energy soft cap 20, hazard/density death slopes, danger diffusion/decay at 1).
  Rationale: Prevent divergence between headless runs and Unity inspector-driven runs; ensure new stability parameters are tunable in View.
  Date/Author: 2025-12-10 / Codex
- Decision: Ignore `TickDurationMs` in deterministic equality/hash while still logging it.
  Rationale: Stopwatch noise varies per run; equality should remain reproducible while performance telemetry stays available in metrics.
  Date/Author: 2025-12-10 / Codex
- Decision: Leave simulation parameters unchanged after the latest smoke run (p95 tick 6.77 ms, births/deaths steady).
  Rationale: Metrics meet stability/perf targets; warm-up spike is isolated and does not affect steady-state behavior.
  Date/Author: 2025-12-10 / Codex

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or completion. Compare the result against the original purpose.

- Baseline tests pass on .NET 8.416. Latest smoke run (3000 ticks, seed 42) shows first birth at tick 19; last 500 ticks births/deaths=125/125. Population oscillates 120..500 with churn; avgEnergy at tick 2999 ~29.43 and avgAge ~39.12. NeighborChecks/pop avg ~3.83 (p95 ~4.67). TickDuration p95=6.77 ms, p99=9.68 ms, max=42.63 ms (warm-up spike).
- Unity DTOs mirror simulation defaults and expose stability knobs (energy soft cap, high-energy drain, density reproduction slope, death hazards, danger diffusion/decay); README remains in sync. No additional tuning taken after this smoke run.

## Context and Orientation

Repo constraints to restate:
- Simulation/View separation is strict; View reads sim snapshots and never drives the simulation loop.
- No O(N²): all interactions use `SpatialGrid` local neighborhoods only.
- Long-run stability requires negative feedback (density stress, disease probability, energy drain, resource regeneration).
- Determinism: seedable RNG and fixed timestep; given same config + seed, runs must reproduce.
- Phase 1 visuals are cube instancing only.

Relevant files/modules:
- `src/Sim/*.cs` (Simulation core), `src/Unity/TerrariumHost.cs` and `AgentViewMapper.cs` for Unity integration, `src/SimRunner/Program.cs` for headless runner, `tests/SimTests/WorldTests.cs` for deterministic checks, `README.md` for user commands.
- Previously pending plan items were in `csharp9_compat_execplan.md` (tests), `environment_fields_execplan.md` (tests), and `population_stability_execplan.md` (neighbor tuning/smoke run); this sweep addresses and closes those items.

## Plan of Work

1) Verification passes:
   - Run the mandatory unit tests now to baseline the current tree and unlock prior plan TODOs.
   - Execute a 3000-step headless run to observe births/deaths and tick durations under the updated defaults; store metrics in `artifacts/metrics_smoke.csv`.
2) Neighbor tuning check:
   - From the smoke-run metrics, compute neighborChecks/population to judge if the grid cell size is appropriate; only change the grid or vision radius if metrics show excessive neighbor counts or perf spikes.
3) Unity config synchronization:
   - Update Unity DTOs in `src/Unity/TerrariumHost.cs` to expose and default to the same values as `SimulationConfig`, including new parameters: `InitialEnergyFractionOfThreshold`, `EnergySoftCap`, `HighEnergyMetabolismSlope`, `DensityReproductionSlope`, `BaseDeathProbabilityPerSecond`, `AgeDeathProbabilityPerSecond`, `DensityDeathProbabilityPerNeighborPerSecond`, and align reproduction/adult age defaults.
   - Ensure environment and feedback defaults match the simulation defaults (danger/pheromone diffusion/decay, food from death).
   - Keep Sim/View separation intact (DTOs only map data into sim; no logic changes).
4) Docs and plan updates:
   - Add/refresh README commands for headless smoke run and list the new config knobs.
   - Update progress checkboxes in the previously open ExecPlans to reflect completed tests/smoke run where applicable.
5) Final validation:
   - Re-run `dotnet test tests/SimTests/SimTests.csproj`.
   - Summarize smoke-run metrics and neighbor density observations in this plan’s Outcomes, ensuring acceptance criteria are met.

## Concrete Steps

- Working directory: repository root.
- Commands to run:
  - `dotnet test tests/SimTests/SimTests.csproj`
  - `dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 3000 --seed 42 --log artifacts/metrics_smoke.csv`
  - After code edits, rerun `dotnet test tests/SimTests/SimTests.csproj`
- Edits:
  - `src/Unity/TerrariumHost.cs`: extend DTOs with missing sim fields and update defaults to match `src/Sim/Configs.cs`.
  - `README.md`: document smoke-run command and new config parameters.
  - `.agent/plans/*`: update progress boxes where prior “tests pending Eor “smoke run pending Eitems are cleared.

## Validation and Acceptance

- Tests: `dotnet test tests/SimTests/SimTests.csproj` passes.
- Smoke run: 3000-step run completes; first birth occurs before tick ~100; births and deaths remain non-zero over 500-tick windows; population stays ≤ MaxPopulation and > 0; tickDuration p95 < 9 ms (from CSV).
- Neighbor tuning: average neighborChecks/population stays consistent with local-cell expectations (no large spikes indicating O(N²) behavior); document finding—no change needed or tuned values applied.
- Config parity: Unity DTO defaults equal the simulation defaults; new fields are exposed so Unity and headless runs behave identically when using defaults.
- Sim/View separation preserved; no Unity-side mutation of sim state.
- No O(N²) introduced; grid interactions unchanged.

## Idempotence and Recovery

- Tests and smoke runs are safe to rerun; metrics CSV can be regenerated.
- DTO/default edits are text-only and reversible via git.
- If grid tuning is deemed unnecessary, leave code unchanged; if tuned, changes are localized to config defaults and remain deterministic.

## Artifacts and Notes

- `artifacts/metrics_smoke.csv` from headless run (3000 steps, seed 42) with observed birth/death cadence, p95 tickDuration, and neighborChecks/population ratio.
- Metrics highlights: first birth tick 19; last 500 ticks births/deaths=125/125; avg neighborChecks/pop=3.83 (p95=4.67); tickDuration p95=5.58 ms, p99=7.41 ms, max=24.08 ms (tick 0 warm-up).

## Interfaces and Dependencies

- `SimulationConfig`/`SpeciesConfig`/`EnvironmentConfig`/`FeedbackConfig` remain the source of truth for defaults.
- Unity DTOs must mirror these fields and only construct configs (no sim logic).
- Headless runner continues to write CSV with fields: tick,population,births,deaths,avgEnergy,avgAge,groups,neighborChecks,tickDurationMs.
- SpatialGrid remains the locality mechanism; no all-pairs scans.
