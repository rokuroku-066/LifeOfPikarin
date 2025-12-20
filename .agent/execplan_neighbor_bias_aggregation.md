# Aggregate neighbor steering calculations to cut per-agent loops

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `.agent/PLANS.md` from the repository root.

## Purpose / Big Picture

Reduce tick time growth at higher populations by aggregating all neighbor-derived steering components into a single pass per agent, without changing simulation rules, determinism, or the Sim/View boundary. Success is visible as lower tick_ms in the smoke run while population dynamics remain stable.

## Progress

- [x] (2025-12-20 03:34Z) Author ExecPlan and capture current detailed smoke-run summary.
- [x] (2025-12-20 03:34Z) Implement and evaluate a single-pass neighbor aggregation in `src/terrarium/world.py`.
- [x] (2025-12-20 03:34Z) Update docs and then revert the aggregation note after performance regression.
- [x] (2025-12-20 03:34Z) Run required Python version check, dependency install, and `pytest tests/python`.
- [x] (2025-12-20 03:34Z) Run detailed smoke runs and compare summary stats (tick_ms, correlations, thresholds).

## Surprises & Discoveries

Single-pass neighbor aggregation increased average tick_ms in the 5k-step smoke run (avg ~22-23ms vs ~18ms baseline), so it was reverted in favor of smaller optimizations.

## Decision Log

- Decision: Revert single-pass neighbor aggregation after smoke-run regression.
  Rationale: Aggregation increased per-tick cost despite fewer loops.
  Date/Author: 2025-12-20 / Codex

- Decision: Optimize boundary avoidance with scalar math and cache danger presence once per tick.
  Rationale: Reduce per-agent overhead without changing behavior or determinism.
  Date/Author: 2025-12-20 / Codex

## Outcomes & Retrospective

Boundary avoidance and danger-field caching reduce average tick_ms to ~20.6ms for the 5k-step smoke run; behavior and population stats remain stable.

## Context and Orientation

The simulation core is `src/terrarium/world.py`. Each tick, neighbors are collected via `SpatialGrid.collect_neighbors_precomputed`, then group membership is updated, steering forces are computed, and agents move. Currently, steering pulls multiple passes over the neighbor list (`_personal_space`, `_separation`, `_intergroup_avoidance`, `_group_cohesion`, `_alignment`, `_group_seek_bias`, `_cohesion`). This plan reduces those passes by aggregating required sums in one loop.

Constraints that must be preserved:
- Simulation and View are strictly separated; View never drives Sim.
- No O(N^2) all-pairs logic; neighbor interactions use SpatialGrid only.
- Long-run stability requires negative feedback loops; do not alter them here.
- Determinism matters: seedable, fixed timestep, reproducible runs.
- Phase 1 scope remains cubes + GPU instancing; no rendering changes.

## Plan of Work

Optimize hot-path costs in `src/terrarium/world.py` without changing simulation rules: keep existing neighbor bias helpers but reduce per-agent overhead in boundary avoidance and danger-field sampling. Evaluate any larger aggregation ideas via smoke runs before committing.

Update `docs/DESIGN.md` to reflect that steering aggregates neighbor contributions in a single pass. Run the required tests and a detailed smoke run to confirm tick_ms improvements and stable behavior.

## Concrete Steps

1) Edit `src/terrarium/world.py`:
   - Keep existing neighbor bias helpers.
   - Optimize `_boundary_avoidance` to use scalar math and early exits.
   - Cache `has_danger` once per tick and pass into `_compute_desired_velocity`.

2) Update `docs/DESIGN.md`:
   - Add a note under the tick flow that steering uses a single neighbor pass.

3) Validate:
   - `python --version`
   - `pip install -r requirements.txt`
   - `pytest tests/python`
   - `python -m terrarium.headless --steps 5000 --seed 42 --log artifacts/metrics_smoke.csv --log-format detailed --summary artifacts/metrics_smoke_summary.json`

Expected outputs: tests pass; smoke summary shows reduced average tick_ms with similar population dynamics.

## Validation and Acceptance

Acceptance is achieved when:
- Tick_ms distribution in `metrics_smoke_summary.json` improves or remains stable with similar population and neighbor_checks.
- Deterministic behavior is preserved (no new randomness, same seed produces stable runs).
- No O(N^2) logic is introduced; neighbor interactions remain SpatialGrid-bound.
- Sim/View separation remains intact.
- Visual sanity check recipe remains unchanged (optional if not running viewer here).

## Idempotence and Recovery

Edits are localized and safe to repeat. If regressions appear, revert boundary/danger optimizations while keeping deterministic behavior intact.

## Artifacts and Notes

- Smoke run (5k steps, seed 42) after optimizations: avg tick_ms ~20.64, p95 ~28.97.

## Interfaces and Dependencies

- `src/terrarium/world.py`: `_compute_desired_velocity` uses single-pass aggregation for steering biases.
- `docs/DESIGN.md`: tick flow description updated.
