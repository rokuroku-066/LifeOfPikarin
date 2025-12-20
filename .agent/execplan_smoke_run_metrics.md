# Enhance headless smoke run logging & summary for detailed analysis

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `.agent/PLANS.md` from the repository root.

## Purpose / Big Picture

Improve the headless smoke run so it emits richer per-tick metrics and an optional summary file, enabling deeper analysis of tick time versus population density without changing simulation rules. The result should be observable as new CSV columns and a machine-readable summary, while the simulation remains deterministic and the view remains read-only.

## Progress

- [x] (2025-12-20 01:15Z) Author ExecPlan and capture current headless logging behavior.
- [x] (2025-12-20 01:15Z) Implement detailed per-tick metrics in `src/terrarium/headless.py` with an explicit log format option.
- [x] (2025-12-20 01:15Z) Add optional summary output for quick inspection of tick time scaling.
- [x] (2025-12-20 01:15Z) Update docs to reflect new logging options and columns.
- [x] (2025-12-20 01:15Z) Add/adjust tests for the new log format behavior.
- [x] (2025-12-20 01:16Z) Run required Python version check, dependency install, and `pytest tests/python`.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Provide a `--log-format` option with a detailed default and a basic compatibility mode.
  Rationale: Enables richer analysis without blocking older tooling that expects the legacy column set.
  Date/Author: 2025-12-20 / Codex

- Decision: Compute detailed metrics in the headless runner after each tick, not inside the simulation core.
  Rationale: Keeps Sim/View separation intact and avoids adding per-tick overhead to the core simulation loops.
  Date/Author: 2025-12-20 / Codex

## Outcomes & Retrospective

Headless smoke runs now support detailed CSV logging plus optional JSON summaries for tick-time analysis, with tests added and passing.

## Context and Orientation

The headless smoke run lives in `src/terrarium/headless.py` and currently writes a small CSV based on `terrarium.world.TickMetrics`. The simulation core is in `src/terrarium/world.py`, which must remain deterministic and independent of rendering. The smoke run is the primary tool for long-run performance and stability checks.

Key constraints that must be preserved:
- Simulation and View are strictly separated; View never drives Sim.
- No O(N^2) all-pairs logic; neighbor interactions use the SpatialGrid.
- Long-run stability depends on negative feedback loops; do not alter them here.
- Determinism matters: seedable, fixed timestep, reproducible runs.
- Phase 1 scope remains cubes + GPU instancing; no rendering changes.

## Plan of Work

Update `src/terrarium/headless.py` to support a detailed log format with additional per-tick columns derived from existing state (population ratios, neighbor checks per agent, group and cell occupancy summaries, and stride usage). Add an optional summary output (JSON) that reports percentiles and correlations for tick time versus population/neighbor checks. Keep all derived computations outside the simulation core to avoid affecting determinism or tick timing.

Add tests under `tests/python/` to verify the new CSV headers and that derived ratio columns are computed correctly. Update `README.md` to document the new log format and summary output.

## Concrete Steps

1) Implement detailed logging and summary support.
   - Edit `src/terrarium/headless.py`.
   - Add helper functions for derived metrics and summary stats.
   - Add CLI flags: `--log-format` and `--summary` (plus `--summary-window` if needed).

2) Update tests.
   - Add `tests/python/test_headless.py` (or update existing tests) to verify CSV headers and deterministic output.

3) Update docs.
   - Adjust `README.md` to list the new columns and CLI flags.

4) Run required validation commands from repo root.
   - `python --version`
   - `pip install -r requirements.txt`
   - `pytest tests/python`

Expected outputs: tests pass, and the smoke run produces a CSV with the new header when `--log-format detailed` is used.

## Validation and Acceptance

Acceptance is achieved when:
- Running `python -m terrarium.headless --steps 5000 --seed 42 --log artifacts/metrics_smoke.csv --log-format detailed` writes a CSV containing the additional analysis columns.
- Optional summary output (when requested) includes percentile tick time stats and correlations.
- Deterministic logs still match for identical seeds when `--deterministic-log` is used.
- Visual sanity check recipe is documented: run the viewer via `uvicorn terrarium.server:app --reload --port 8000` and observe smooth, stable agent motion from the overhead camera.

Repo-specific checks:
- Performance sanity: confirm tick time stays within target ranges for typical populations, using the detailed CSV and summary statistics.
- Long-run stability: verify births/deaths and population remain bounded over long runs; confirm negative feedback metrics (stress/ungrouped ratio) remain plausible.
- No O(N^2): confirm detailed metrics are computed with O(N) per tick (single-pass aggregation), and neighbor interactions remain spatial-grid bound.
- Sim/View separation: confirm headless logging does not alter simulation or rendering code paths.

## Idempotence and Recovery

Edits are idempotent and can be repeated; rerunning the smoke run overwrites the specified CSV. If issues arise, fall back to `--log-format basic` to reproduce the legacy output.

## Artifacts and Notes

- Tests: `pytest tests/python` (52 passed).

## Interfaces and Dependencies

- `src/terrarium/headless.py`: `run_headless(...)` signature extended to accept log format and summary output options.
- CLI interface: `python -m terrarium.headless` gains `--log-format` and `--summary` flags.
- Tests: new/updated test under `tests/python/` to validate CSV output.
- Documentation: `README.md` updated to reflect new smoke run options.
