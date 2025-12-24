# World step performance optimizations

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Per repository rules, this plan is maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Improve the per-tick performance of the terrarium simulation by reducing redundant work, cutting temporary allocations, and batching environment field updates while preserving deterministic simulation behavior. The user-visible effect is faster ticks with identical simulation outcomes, verified by running the existing Python tests and a deterministic headless run recipe.

## Progress

- [x] (2025-09-19 01:38Z) Inspect current `World.step` hot paths, pending field queues, and metrics storage in `src/terrarium/world.py` and `src/terrarium/environment.py`.
- [x] (2025-09-19 01:38Z) Implement hot-loop optimizations (duplicate checks, neighbor count reuse, scalar integration, squared distance comparisons, in-place normalizations) and batch field updates by cell key.
- [x] (2025-09-19 01:38Z) Update metrics storage to bounded history and apply `@dataclass(slots=True)` to metrics/snapshot types; adjust docs/tests as needed.
- [x] (2025-09-19 01:38Z) Run required Python version check, install deps, and execute `pytest tests/python`.
- [x] (2025-09-19 01:38Z) Summarize outcomes and verification steps.

## Surprises & Discoveries

In-place position updates mutated shared `Vector2` instances in tests. The position update was switched back to assignment to preserve prior semantics while keeping scalar integration for performance.

## Decision Log

- Decision: Store metrics in a bounded `collections.deque` to prevent unbounded memory growth.
  Rationale: Long-running simulation sessions should not accumulate unlimited metric history.
  Date/Author: 2025-09-19 / Codex

## Outcomes & Retrospective

`World.step` now reuses neighbor counts, avoids redundant danger checks, and reduces temporary vector allocations by using scalar integration and in-place normalization where safe. Environment field updates are batched per cell, and only the latest metrics sample is stored to prevent accumulation. All required Python tests pass.

## Context and Orientation

The simulation core lives in `src/terrarium/world.py`, where `World.step` advances agents and records `TickMetrics`. Environment fields (food, danger, pheromone) are managed by `src/terrarium/environment.py`. The WebSocket snapshot schema and metrics expectations are documented in `docs/snapshot.md`, and overall behavior is described in `docs/DESIGN.md`.

Key hotspots include:
1. `World.step` agent loop and steering integration.
2. Environment sampling and gradient calculations in `_compute_desired_velocity`.
3. Pending field event queues (`_pending_food`, `_pending_danger`, `_pending_pheromone`) applied in `_apply_field_events`.

Terms:
- “cell key” refers to the integer grid coordinate used by `EnvironmentGrid` to access per-cell fields.
- “in-place normalization” uses `Vector2.normalize_ip()` to avoid allocating new vectors.

## Plan of Work

Edit `src/terrarium/world.py` to remove duplicate `has_danger` lookups, reuse neighbor count in the hot loop, move integration math to scalar paths, and use in-place normalization for gradient vectors. Replace list-based pending field queues with dictionaries keyed by cell (and group for pheromones) to aggregate updates. Introduce helper functions to reuse a precomputed environment cell key for sampling and gradients.

Edit `src/terrarium/environment.py` to accept tuple-based pheromone updates so batched cell-key aggregation can be applied without extra coordinate conversion.

Edit `docs/DESIGN.md` and/or `docs/snapshot.md` to document the bounded metrics history behavior.

Adjust tests in `tests/python/test_world.py` if required for the metrics container change.

## Concrete Steps

1. Update `World.step` in `src/terrarium/world.py` with scalar integration and cached neighbor counts; reuse environment cell keys and aggregate pending field updates by cell key.
2. Update `EnvironmentGrid.add_pheromone` in `src/terrarium/environment.py` to accept either `Vector2` or a precomputed cell key tuple.
3. Update `TickMetrics`/`Snapshot*` dataclasses to use `slots=True` and store metrics in a bounded `deque`.
4. Update docs and tests to align with the new metrics storage.
5. Run:
   - `python --version`
   - `pip install -r requirements.txt`
   - `pytest tests/python`

Expected transcript snippet (examples):
    Python 3.11.x
    ...
    ====== 100% ======
    1 passed in ...

## Validation and Acceptance

- Deterministic smoke run: `python -m terrarium.headless --steps 200 --seed 42 --summary tests/artifacts/summary.json` should complete without errors and show stable population metrics in the summary JSON.
- Performance sanity check: confirm tick duration remains reasonable with default population (200 agents) by observing `tick_duration_ms` in metrics output; no evidence of per-tick regressions versus baseline.
- Long-run stability: population metrics should not monotonically explode or collapse during the short smoke run; stress and reproduction factors remain unchanged.
- No O(N²): neighbor interactions continue to use `SpatialGrid.collect_neighbors_precomputed` in `World.step`.
- Sim/View separation: only the simulation writes state; snapshots are read-only for the viewer.

## Idempotence and Recovery

Edits are limited to deterministic code paths and documentation; reapplying changes is safe. If issues arise, revert the touched files via git and rerun tests.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

The following must exist and remain compatible:
- `World.step` in `src/terrarium/world.py`.
- `EnvironmentGrid` APIs in `src/terrarium/environment.py` (food/danger/pheromone sampling and mutation).
- `TickMetrics` and snapshot dataclasses for JSON serialization in `src/terrarium/server.py`.
- Python tests under `tests/python/`.
