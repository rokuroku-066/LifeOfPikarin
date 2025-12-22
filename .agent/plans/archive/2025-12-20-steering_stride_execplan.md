# Time-sliced steering updates and conditional bias evaluation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `.agent/PLANS.md` from the repository root.

## Purpose / Big Picture

Keep tick time near the 20ms target at higher populations by (1) time-slicing steering updates and (2) skipping bias computations when they are irrelevant (weights or traits zero). The goal is to reduce per-agent neighbor work while preserving determinism and the Sim/View boundary.

## Progress

- [x] (2025-12-20 03:45Z) Author ExecPlan and capture current smoke summary baseline.
- [x] (2025-12-20 03:45Z) Add steering update stride config and agent state to reuse desired vectors.
- [x] (2025-12-20 03:45Z) Gate bias computations by weights/traits to skip unnecessary loops.
- [x] (2025-12-20 03:45Z) Update docs for new config and steering time-slicing.
- [x] (2025-12-20 03:45Z) Add tests covering steering stride behavior.
- [x] (2025-12-20 03:45Z) Run Python version check, dependency install, and `pytest tests/python`.
- [x] (2025-12-20 03:45Z) Run a detailed smoke run and compare summary stats.

## Surprises & Discoveries

Steering stride reduces per-tick cost substantially (avg tick_ms ~13.9 for 5k steps) but increases population peaks (max ~609 vs ~531 baseline), so stability should be monitored.

## Decision Log

- Decision: Reuse last desired vector on skipped steering ticks to avoid recomputing neighbor biases.
  Rationale: Preserves deterministic movement continuity without stalling simulation steps.
  Date/Author: 2025-12-20 / Codex

## Outcomes & Retrospective

Steering time-slicing plus bias gating brought the 5k smoke run average to ~13.9ms (p95 ~16.4). Population and neighbor checks shifted, indicating behavioral impact that may need tuning.

## Context and Orientation

Steering is computed in `src/terrarium/world.py` by `_compute_desired_velocity` using multiple neighbor-derived biases. All neighbor interactions already use `SpatialGrid`; we must keep that restriction and not introduce O(N^2) scans. The headless smoke run is used to evaluate tick time.

Constraints that must be preserved:
- Simulation and View are strictly separated; View never drives Sim.
- No O(N^2) all-pairs logic; neighbor interactions use SpatialGrid only.
- Long-run stability requires negative feedback loops; do not alter them here.
- Determinism matters: seedable, fixed timestep, reproducible runs.
- Phase 1 scope remains cubes + GPU instancing; no rendering changes.

## Plan of Work

1) Add new feedback config fields for steering time-slicing.
2) Add per-agent cached desired vectors and sensed danger state.
3) Update `World.step` to compute steering only for a stride-selected subset at high population, and reuse cached desired vectors otherwise.
4) Gate steering bias helpers so they only run when their weights or traits make them meaningful.
5) Update docs and add tests to cover steering stride reuse.
6) Run required tests and a detailed smoke run.

## Concrete Steps

1) Edit `src/terrarium/config.py` to add:
   - `steering_update_population_threshold`
   - `steering_update_stride`

2) Edit `src/terrarium/agent.py` to add cached steering state:
   - `last_desired: Vector2`
   - `last_sensed_danger: bool`

3) Edit `src/terrarium/world.py`:
   - Initialize `last_desired` for bootstrap and newborn agents.
   - Compute steering stride per tick and reuse cached desired vectors on skipped ticks.
   - Skip bias helpers when weights/traits are zero.

4) Update docs in `docs/DESIGN.md` and `README.md` to mention steering stride config and conditional bias evaluation.

5) Add tests in `tests/python/test_world.py` to verify steering stride reuse.

6) Validate:
   - `python --version`
   - `pip install -r requirements.txt`
   - `pytest tests/python`
   - `python -m terrarium.headless --steps 5000 --seed 42 --log artifacts/metrics_smoke.csv --log-format detailed --summary artifacts/metrics_smoke_summary.json`

## Validation and Acceptance

Acceptance is achieved when:
- Tick_ms distribution in `metrics_smoke_summary.json` improves or remains stable with similar population and neighbor_checks.
- Deterministic behavior is preserved (same seed produces stable outputs).
- No O(N^2) logic is introduced; neighbor interactions remain SpatialGrid-bound.
- Sim/View separation remains intact.

## Idempotence and Recovery

Edits are localized and safe to repeat. If regressions appear, disable steering time-slicing by setting stride to 1 or reverting cached desired reuse.

## Artifacts and Notes

- Smoke run (5k steps, seed 42): avg tick_ms ~13.93, p95 ~16.40, max pop ~609.

## Interfaces and Dependencies

- `src/terrarium/world.py`: steering stride and bias gating.
- `src/terrarium/config.py`: new feedback config fields.
- `src/terrarium/agent.py`: cached desired vectors.
- `tests/python/test_world.py`: stride behavior test.
- `docs/DESIGN.md`, `README.md`: updated behavior notes.
