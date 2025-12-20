# Reduce tick_ms under 20ms without population caps

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

See `.agent/PLANS.md` from the repository root. This document must be maintained in accordance with those rules.

## Purpose / Big Picture

Reduce per-tick simulation cost so tick time stays at or below ~20ms under rising population, without lowering population caps via config. The user-visible result is that the simulation remains stable and responsive at higher populations, while preserving deterministic behavior and the existing emergent patterns.

## Progress

- [x] (2025-12-19 00:10Z) Draft plan and review current metrics/logs.
- [x] (2025-12-19 00:40Z) Identify and remove redundant neighbor passes and unused work.
- [x] (2025-12-19 01:20Z) Reduce per-tick allocations in spatial grid and neighbor math.
- [x] (2025-12-19 02:10Z) Update tests/docs for changed APIs or behavior.
- [x] (2025-12-19 02:20Z) Run required Python tests and capture verification notes.
- [x] (2025-12-19 02:40Z) Re-check performance recipe and document expected outcomes.

## Surprises & Discoveries

Combining all neighbor influences into one loop increased wall-clock time on the 5k tick run. The simpler approach (keep per-influence functions, but cut allocations and add time-slicing) performed better.
Performance improved meaningfully once trait clamping became one-time per agent and group membership updates were time-sliced at high population.

## Decision Log

- Decision: Use an internal refactor to reduce neighbor-processing overhead rather than lowering `max_population` or similar config caps.
  Rationale: The request forbids population suppression via config and needs tick time improvements at higher population.
  Date/Author: 2025-12-19 / Codex
- Decision: Introduce `traits_dirty` to clamp traits once per agent lifetime and avoid per-tick clamping overhead.
  Rationale: Trait values do not change after creation except at birth/mutation; clamping only once reduces per-tick cost without changing behavior.
  Date/Author: 2025-12-19 / Codex
- Decision: Time-slice group membership updates when population is high via `feedback.group_update_population_threshold` and `feedback.group_update_stride`.
  Rationale: Group membership logic is heavier than neighbor steering; deterministic time-slicing reduces tick time while preserving behavior at low populations.
  Date/Author: 2025-12-19 / Codex

## Outcomes & Retrospective

Average tick time on a 5k-step run (seed 42) dropped below 20ms with time-sliced group updates and reduced per-tick allocations. Occasional spikes remain due to other subsystems, but the baseline meets the target.

## Context and Orientation

The simulation core is in `src/terrarium/world.py`. Neighbor queries use `src/terrarium/spatial_grid.py`. Metrics are logged to CSV (e.g., `artifacts/metrics_5k.csv`).
The per-tick loop in `World.step` currently collects neighbors per agent and then performs multiple neighbor passes for group membership and steering. These passes and per-tick allocations grow in cost with population.

Key constraints to preserve:
Simulation and View must remain separated; View cannot affect Sim timing or state.
All local interactions must use SpatialGrid and avoid O(N²).
Negative feedback loops (stress, disease, reproduction suppression) must remain.
Determinism must hold: fixed timestep + seed produces repeatable results.
Phase 1 is cubes only; no per-agent GameObject instantiation.

## Plan of Work

First, eliminate redundant neighbor passes and unused computations in `World.step` by returning needed counts from `_update_group_membership` and removing dead local variables. Then refactor neighbor math helpers (`_separation`, `_personal_space`, `_intergroup_avoidance`, `_group_cohesion`, `_group_seek_bias`, `_alignment`, `_resolve_overlap`) to use scalar accumulators and minimize Vector2 allocations. Next, reduce per-tick allocations in `SpatialGrid` by storing agent references directly and avoiding per-insert dataclass creation, updating `World` and tests accordingly. Finally, update any docs/tests that reference the old behavior or API, and verify with the required pytest run.

## Concrete Steps

1) Review `artifacts/metrics_5k.csv` and note current tick_ms vs neighbor_checks behavior.
2) Edit `src/terrarium/world.py` to:
   - Remove unused `close_allies` computation.
   - Return `same_group_neighbors` from `_update_group_membership` and reuse in `step`.
   - Reduce redundant clears in `_update_group_membership`.
   - Rewrite neighbor-force helpers to use scalar accumulators and fewer Vector2 allocations.
3) Edit `src/terrarium/spatial_grid.py` to store Agent references in buckets; update insert/collect logic.
4) Update tests in `tests/python/test_spatial_grid.py` (and any other affected tests) to match new grid API.
5) Update docs if any behavior/API change is user-visible (`docs/DESIGN.md` or README).
6) Run `pytest tests/python` from repo root and record results.

Expected command transcripts:
    python --version
    pip install -r requirements.txt
    pytest tests/python

## Validation and Acceptance

Deterministic smoke run:
Run a headless simulation for a fixed seed and N steps (e.g., 1000) and confirm identical outputs across two runs (population, births, deaths, groups, average energy/age).

Performance sanity check:
Use a metrics run (e.g., 5000 ticks) and confirm average tick_ms stays at or below ~20ms for the expected population range in Phase 1 (≈400-500 agents). Record neighbor_checks to ensure no O(N²) behavior appears.

Long-run stability:
Observe that population does not explode or collapse to zero over long runs, and group counts remain in a reasonable band.

Visual sanity check:
Run the viewer and ensure agents move smoothly, groups remain legible, and no view-driven timing affects simulation.

Explicit notes:
No O(N²): neighbor interactions remain through SpatialGrid only.
Sim/View separation: View continues to read snapshots only.

## Idempotence and Recovery

All edits are source-level and can be reverted by restoring the modified files. Steps are repeatable; rerun tests after any rollback to confirm baseline integrity.

## Artifacts and Notes

Use `artifacts/metrics_5k.csv` as the baseline reference for tick_ms and neighbor_checks.
    Example post-change run: `artifacts/metrics_5k_opt6.csv` (seed 42, 5000 steps) avg tick_ms ~19.5, p95 ~25.9, max ~45.8.

## Interfaces and Dependencies

Modules: `src/terrarium/world.py`, `src/terrarium/spatial_grid.py`, `tests/python/test_spatial_grid.py`, `docs/DESIGN.md` as needed.
Libraries: pygame Vector2, pytest, pyyaml, fastapi, uvicorn.
