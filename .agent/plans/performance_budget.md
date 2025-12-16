# Restore long-run performance budget compliance

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: maintain this plan per `.agent/PLANS.md` rules.

## Purpose / Big Picture

Ensure the long-run performance test `test_long_run_population_groups_and_performance` meets the 25ms average tick budget while preserving simulation correctness. The outcome should be a reproducible run where tick metrics reflect true runtimes and stay within budget without masking regressions.

## Progress

- [x] (2025-12-15 09:45Z) Drafted ExecPlan outlining goals and constraints.
- [x] (2025-12-15 09:50Z) Reviewed performance test expectations in `tests/python/test_long_run_performance.py` and inspected current simulation hot paths in `src/terrarium/world.py` and `src/terrarium/spatial_grid.py` to identify optimization targets.
- [x] (2025-12-15 09:47Z) Ran baseline `pytest tests/python/test_long_run_performance.py::test_long_run_population_groups_and_performance --run-config-tests` (passed in ~113s; average tick budget satisfied but runtime margin seems tight).
- [x] (2025-12-15 09:48Z) Precomputed neighbor cell offsets for vision radius to reduce per-agent grid traversal overhead; reran performance test (passed in ~118s, similar timing to baseline).
- [x] (2025-12-15 09:50Z) Run full `pytest tests/python` to confirm broader correctness after optimization (suite passed; long-run test skipped by marker).

## Surprises & Discoveries

- Baseline long-run performance test already passes but takes ~113s; rerun after optimization stayed around ~118s, so performance is stable but not faster.

## Decision Log

- Decision: Precompute spatial grid cell offsets for neighbor collection instead of rebuilding ranges each call to cut per-agent overhead.
  Rationale: Vision radius is constant from config; reusing offset lists avoids per-agent range allocation and repeated radius math while keeping behavior unchanged.
  Date/Author: 2025-12-15 / assistant

## Outcomes & Retrospective

- Implemented neighbor cell offset precomputation for vision lookups and validated determinism via `pytest` runs. Long-run performance test continues to pass (average tick budget ≤25ms) and overall suite passes.

## Context and Orientation

- Simulation core and performance-critical loop live in `src/terrarium/world.py`, with supporting data structures in `src/terrarium/spatial_grid.py` and environment helpers in `src/terrarium/environment.py`.
- Configuration defaults affecting population and sensing are in `src/terrarium/config.py`.
- Long-run performance expectations are enforced by `tests/python/test_long_run_performance.py`, specifically `test_long_run_population_groups_and_performance` which monitors tick duration metrics and grouping behavior.
- Constraints: maintain strict Sim/View separation, avoid O(N^2) scans by using the spatial grid for neighbor queries, keep determinism with seeded randomness, and preserve long-run stability via existing feedback mechanisms.

## Plan of Work

1. Profile current performance test expectations and gather baseline metrics from `test_long_run_population_groups_and_performance`, inspecting how `tick_duration_ms` is averaged and what configuration it uses.
2. Audit per-tick work in `src/terrarium/world.py` to identify allocations or redundant computations in the main step loop (movement desire calculation, neighbor queries, group updates) that can be optimized without changing simulation rules.
3. Optimize hot paths (e.g., reuse buffers, reduce repeated math, simplify environment/food sampling) and adjust configuration defaults only if they keep behavior aligned with design goals.
4. Re-run `pytest tests/python/test_long_run_performance.py::test_long_run_population_groups_and_performance --run-config-tests` to validate improvements and iterate until the average tick duration satisfies the 25ms budget.
5. Once passing, run the full `pytest tests/python` suite to confirm broader correctness.

## Concrete Steps

- Read `tests/python/test_long_run_performance.py` to understand performance thresholds and metrics computation.
- Inspect `src/terrarium/world.py` main loop for per-agent operations and identify optimization opportunities (buffer reuse, precomputed constants, avoiding redundant neighbor scans).
- Modify code to reduce per-tick overhead while respecting determinism and stability constraints; adjust `src/terrarium/config.py` only if necessary and consistent with design.
- Execute `pytest tests/python/test_long_run_performance.py::test_long_run_population_groups_and_performance --run-config-tests` from repo root after each optimization pass, recording results here.
- Execute `pytest tests/python` once performance test passes.

Expected command transcript examples:
  - `pytest tests/python/test_long_run_performance.py::test_long_run_population_groups_and_performance --run-config-tests`
  - `pytest tests/python`

## Validation and Acceptance

Acceptance criteria:
- `test_long_run_population_groups_and_performance` passes with average tick duration at or below 25ms using real tick metrics (no clamping), demonstrating performance budget compliance.
- Full `pytest tests/python` suite passes.
- No O(N^2) logic introduced; neighbor interactions rely on spatial grid queries only.
- Simulation remains deterministic given fixed seed and timestep configuration.
- Long-run stability preserved: population and group metrics behave sensibly without runaway growth or collapse.
- Sim/View separation maintained: only simulation core is modified.

Performance sanity check: expect average tick duration ≤25ms for the configured run; monitor `tick_duration_ms` metrics logged in the test.
Long-run stability check: population counts and group metrics remain bounded and consistent across runs.
No O(N^2) note: all neighbor-related work must use spatial grid neighborhoods.
Sim/View separation note: ensure changes stay within simulation modules and do not couple to rendering.

## Idempotence and Recovery

Edits are standard code changes; rerunning the specified pytest commands is safe. Git can revert any file via `git checkout -- <file>` if needed.

## Artifacts and Notes

- Key files: `src/terrarium/world.py`, `src/terrarium/spatial_grid.py`, `src/terrarium/environment.py`, `src/terrarium/config.py`, and `tests/python/test_long_run_performance.py`.
- Capture timing measurements from test output in progress updates.

## Interfaces and Dependencies

- Use existing spatial grid neighbor query APIs without expanding scope.
- Respect configuration loading in `src/terrarium/config.py` and avoid introducing non-deterministic sources.
- Python 3.11+ with dependencies installed via `pip install -r requirements.txt`.
