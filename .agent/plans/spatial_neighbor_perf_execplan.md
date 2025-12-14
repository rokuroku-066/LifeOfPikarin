# Spatial neighbor lookup speedup (large-pop perf)

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated per `.agent/PLANS.md`.

## Purpose / Big Picture

Reduce per-tick CPU cost when the population climbs by eliminating redundant neighbor lookups and vector math while preserving determinism, local interactions (SpatialGrid), and Sim/View separation. The outcome should be smoother tick times for 500-1000 agents without changing behaviors.

## Progress

- [x] (2025-12-14 09:35Z) Drafted plan
- [x] (2025-12-14 09:39Z) Implemented grid neighbor ref/offset path and removed per-tick id map rebuild
- [x] (2025-12-14 09:42Z) Ran tests `python -m pytest tests/python` (pass)
- [x] (2025-12-14 09:44Z) Captured headless timing sample `artifacts/headless_neighbor_perf.csv`

## Surprises & Discoveries

- Running headless locally needs `PYTHONPATH=src` for `python -m terrarium.headless`.

## Decision Log

- Decision: Store agent refs in `SpatialGrid` and add `collect_neighbors(..., exclude_id=...)`; drop `_id_to_index` rebuild each tick.
  Rationale: Avoid id lookup + offset recompute per neighbor, and remove redundant id map construction for performance at high populations.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

- Tests now passing on Python 3.9.7; no behavior regressions detected.
- Headless 600-step sample (seed 42) completed; population stabilized at ~130 with tick durations mostly in the mid-30ms range (log: `artifacts/headless_neighbor_perf.csv`).

## Context and Orientation

- Files: `src/terrarium/spatial_grid.py` (SpatialHash), `src/terrarium/world.py` (per-tick loop using neighbor data), `tests/python/test_spatial_grid.py` (grid regression), `src/terrarium/headless.py` (timing/log run).
- Constraints to uphold: Sim/View one-way flow (View never drives Sim), no O(N^2) all-pairs (SpatialGrid only), determinism/seed + fixed timestep, long-run stability via feedback (density stress, metabolism, birth limits), Phase 1 cubes only.
- Current pain: neighbor collection does extra id->agent lookups and recomputes offsets after the grid already checked distances; cost grows with dense populations.

## Plan of Work

Describe edits in sequence:
1) Extend `SpatialGrid.insert` to accept an optional `agent` reference (keep current API) and record it in `GridEntry`.
2) Add `SpatialGrid.collect_neighbors(position, radius, out_agents, out_offsets, exclude_id)` that filters by radius once and fills provided lists with agent refs + offsets, avoiding per-neighbor id lookups and duplicate vector subtraction. Leave `get_neighbors` unchanged for compatibility/tests.
3) In `world.step`, switch to `collect_neighbors` to populate `_neighbor_agents`/`_neighbor_offsets`, drop the extra id lookup pass. Keep group logic and metrics identical.
4) Add/adjust unit test to cover `collect_neighbors` parity with `get_neighbors` when agents are supplied, preserving existing grid tests.
5) Run full pytest suite; record timing from a headless run (e.g., 600 steps, seed 42) to confirm tick durations stay stable with ~100-500 agents.

## Concrete Steps

- Edit files above following Plan of Work.
- From repo root: `python -m pytest tests/python`
- Optional perf sample: `python -m terrarium.headless --steps 600 --seed 42 --log artifacts/headless_neighbor_perf.csv`

Expected headless log: population remains bounded (< max_population), tick_duration_ms does not grow unbounded; neighbor_checks scales with population but should run faster wall-clock than before (qualitative here).

## Validation and Acceptance

- Deterministic smoke run: `python -m terrarium.headless --steps 600 --seed 42 --log artifacts/headless_neighbor_perf.csv` should complete without errors; log shows population/births/deaths metrics and stable tick_duration_ms.
- Unit tests: `python -m pytest tests/python` must pass.
- No O(N^2): neighbor interactions remain via SpatialGrid; `collect_neighbors` still scans only local buckets.
- Sim/View separation: only Simulation code touched; no changes to rendering or client messages.
- Long-run stability: feedback configs untouched; population bounded by existing mechanisms.

## Idempotence and Recovery

- Changes are additive to SpatialGrid API; existing callers using `get_neighbors` remain valid. Re-running plan is safe: methods are pure Python edits with tests to catch regressions.

## Artifacts and Notes

- Log files (if generated): `artifacts/headless_neighbor_perf.csv` for timing snapshot.

## Interfaces and Dependencies

- New method signature: `SpatialGrid.collect_neighbors(position: Vector2, radius: float, out_agents: List[Agent], out_offsets: List[Vector2], exclude_id: int | None = None) -> None` requiring buckets to store agent references.
- `GridEntry` now holds `agent: Agent | None`; `insert(agent_id, position, agent=None)` keeps backward compatibility.
