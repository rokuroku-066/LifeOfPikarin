# Remove abrupt population capping while preserving stability

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. See `.agent/PLANS.md` for rules; this plan follows those requirements.

## Purpose / Big Picture

Eliminate the hard population culling logic that drops agent counts suddenly while keeping the terrarium stable and performant. The goal is smooth, feedback-driven population changes that avoid the tick-156 collapse and keep long-run tests meaningful.

## Progress

 - [x] (2025-12-16 02:10Z) Draft plan and restate scope.
 - [x] (2025-12-16 02:25Z) Remove abrupt population cap application from simulation loop and config defaults.
 - [x] (2025-12-16 02:40Z) Adjust tests to reflect continuous controls.
 - [x] (2025-12-16 03:00Z) Validate headless run and full pytest suite.

## Surprises & Discoveries

- Finding a replacement for the hard cap required retuning global population pressure; strong slopes (≥0.25) caused extinction while weaker slopes left runtimes too high. The final settings (start 230, slope 0.2, delay 4s) produce peaks around 440 with post-peak troughs near 90 and average tick times ~16 ms over 1000 ticks.

## Decision Log

- Decision: Remove hard culling instead of retuning caps; rely on continuous feedback (density hazards, resource limits) for stability.
  Rationale: Aligns with user request to avoid sudden population drops and preserves emergent dynamics without forced caps.
  Date/Author: 2025-12-16 / Codex

## Outcomes & Retrospective

Will summarize once validation is complete, comparing stability and test expectations without the cap.

## Context and Orientation

Key files:
- `src/terrarium/world.py` — simulation tick loop, currently calls `_apply_population_cap` after births/deaths.
- `src/terrarium/config.py` — defines feedback parameters including peak thresholds and caps.
- `tests/python/test_long_run_performance.py` — long-run assertions that previously allowed capped behavior.

Repository constraints (must be preserved):
- Strict Sim/View separation: simulation runs on fixed timesteps and is not driven by rendering.
- No O(N²): interactions rely on spatial grid neighborhood queries only.
- Long-run stability via negative feedback (density stress, hazards, resource limits) rather than abrupt caps.
- Deterministic and seedable; Phase 1 visuals use cubes with GPU instancing.

## Plan of Work

Describe, in prose, the sequence of edits and additions.
1) Remove `_apply_population_cap` invocation and implementation from `world.py`, replacing it with smoother feedback if needed.
2) Clean up config defaults by removing unused cap parameters and ensuring remaining feedback settings maintain stability.
3) Update `test_long_run_performance.py` to assert against smooth dynamics (no abrupt fixed cap) and to ensure population continues to evolve.
4) Run deterministic headless simulation (500–5000 ticks) to observe population trajectory without caps; adjust feedback parameters if necessary to avoid runaway growth.
5) Execute `pytest tests/python` to ensure suite passes with new dynamics.

## Concrete Steps

- From repo root, edit `src/terrarium/world.py` to eliminate cap logic and any associated fields/queues.
- Adjust `src/terrarium/config.py` feedback defaults to drop cap fields.
- Update `tests/python/test_long_run_performance.py` expectations to detect freezes or unnatural plateaus.
- Run: `python -m terrarium.headless --steps 500 --seed 42 --log artifacts/metrics_smoke.csv` to gather a smoke trajectory.
- Run: `pytest tests/python/test_long_run_performance.py` then `pytest tests/python`.

Expected log highlights: population should peak then decline gradually without flatlining at a forced cap; groups remain within configured range via organic processes.

## Validation and Acceptance

- Deterministic smoke run (seed=42) completes 500–5000 ticks without sudden clamps; population should not stick to an exact cap value for extended ticks.
- Long-run test should fail if population flatlines at a fixed cap and pass when dynamics remain active and steady.
- Performance sanity: average tick ms remains under the existing threshold; no new O(N²) loops introduced.
- Sim/View separation untouched.

## Idempotence and Recovery

Edits are code/config only; rerunning commands is safe. If dynamics become unstable, revert feedback parameter changes and rerun smoke simulation to retune.

## Artifacts and Notes

Will record notable metrics from smoke run and pytest outputs once executed.

## Interfaces and Dependencies

- `SimulationConfig` should no longer expose unused cap fields; downstream code/tests must be updated accordingly.
- Neighbor interactions remain through spatial grid utilities; no change to interfaces.
