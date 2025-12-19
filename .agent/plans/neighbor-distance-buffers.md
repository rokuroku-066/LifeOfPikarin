# Neighbor distance buffers in SpatialGrid

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must follow the rules in `.agent/PLANS.md` (repository root). Key constraints to restate: Simulation and Visualization remain separated, neighbor queries must stay O(N) via spatial hashing (no all-pairs), determinism/seeded behavior is required, and Phase 1 visuals stay as cube instancing. Long-run stability relies on existing negative feedback loops and must not be compromised.

## Purpose / Big Picture

Expose squared-distance outputs from `SpatialGrid.collect_neighbors_precomputed` so callers can reuse a shared buffer instead of recomputing distances each frame. Update the `World` neighbor processing to consume the new buffer and ensure distance lists are cleared when no neighbors are found. This reduces per-tick work without changing simulation rules and keeps Sim/View separation intact.

## Progress

- [x] (2024-07-06 00:00Z) Drafted ExecPlan with scope, constraints, and validation strategy.
- [x] (2024-07-06 00:25Z) Implemented grid distance buffer support and wired `_neighbor_dist_sq` through `World.step` usage sites.
- [x] (2024-07-06 00:27Z) Added regression coverage for zero-neighbor clearing and ran `pytest tests/python` successfully.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Reuse the existing neighbor distance list in `World` by having the grid fill it directly, avoiding extra loops.
  Rationale: Keeps allocations zero while eliminating redundant distance calculations per neighbor.
  Date/Author: 2024-07-06 / Codex

## Outcomes & Retrospective

- Grid neighbor queries now fill an optional squared-distance buffer and clear it when no neighbors are found, removing redundant distance recomputation in `World.step` while keeping outputs deterministic.
- Regression test exercises buffer clearing after a previous populated query; full `pytest tests/python` passes.

## Context and Orientation

- Neighbor queries live in `src/terrarium/spatial_grid.py` with `collect_neighbors_precomputed` providing allocation-free buffers.
- The simulation loop uses these buffers in `src/terrarium/world.py` within `World.step`, plus helper methods like `_separation` and `_resolve_overlap` that accept neighbor distance lists.
- Tests for the grid are in `tests/python/test_spatial_grid.py`; full suite runs via `pytest tests/python`.
- Spatial hashing enforces locality (3x3 cell neighborhoods) to avoid O(N²) scans; this change must preserve that.
- Determinism is maintained through precomputed cell offsets/radius squared and deterministic RNG streams; distance buffering must not introduce randomness.
- Long-run stability mechanisms (feedback constraints in `World`) are untouched; modifications must not alter group/interaction rules.

## Plan of Work

1. Extend `SpatialGrid.collect_neighbors_precomputed` to accept an optional `out_dist_sq` list, populate it alongside offsets, and truncate/clear it when neighbors are absent. Ensure ordering matches agents/offsets and avoid extra allocations by updating in place when possible.
2. In `World.step`, pass the shared `_neighbor_dist_sq` buffer into `collect_neighbors_precomputed` and remove the manual distance recomputation loop. Ensure downstream uses (`_update_group_membership`, `_compute_desired_velocity`, `_resolve_overlap`, `_separation`, etc.) receive the populated list and continue to accept provided buffers without fallback recalculation when lengths match.
3. Add a regression test in `tests/python/test_spatial_grid.py` that pre-fills distance/offset lists, performs a zero-neighbor query, and asserts both offsets and distances are cleared, confirming buffer reuse behavior.
4. Run `pytest tests/python` to confirm determinism and stability checks still pass. Document any environment blockers if they arise.

## Concrete Steps

- Edit `src/terrarium/spatial_grid.py` to add the optional distance buffer parameter and write distances during neighbor collection; include clearing/truncation semantics.
- Update `src/terrarium/world.py` neighbor processing to supply the distance buffer and drop redundant distance calculation loops, keeping group cohesion/avoidance logic unchanged.
- Add the new zero-neighbor buffer-clearing test in `tests/python/test_spatial_grid.py` that exercises `collect_neighbors_precomputed` with pre-seeded buffers.
- From repo root, run: `pytest tests/python`
  - Expected: All tests pass; no new allocations or behavior changes beyond buffer reuse.

## Validation and Acceptance

- Functional: Neighbor queries return the same agents/offsets as before; distance buffer aligns element-wise with outputs and is emptied when no neighbors are found.
- Deterministic smoke: Using `pytest tests/python` ensures deterministic unit coverage; no randomness introduced.
- Performance sanity: The change reduces per-tick distance recomputation in `World.step` without adding allocations; spatial hashing still bounds neighbor checks to nearby cells (no O(N²)). Tick-time counters in `World` remain intact.
- Stability: Simulation rules and negative feedback loops are untouched; group behaviors remain seeded/deterministic since only buffering is changed.
- Sim/View separation: All edits stay within simulation logic; no rendering or view timing changes.

## Idempotence and Recovery

- Changes are local to grid neighbor collection and world buffer usage; edits can be reverted by restoring modified files.
- Tests provide quick regression signals; rerunning `pytest tests/python` after adjustments is safe.

## Artifacts and Notes

Pending implementation; will note any logs or metrics if behavior differs.

## Interfaces and Dependencies

- `SpatialGrid.collect_neighbors_precomputed(position, cell_offsets, radius_sq, out_agents, out_offsets, exclude_id=None, out_dist_sq=None)` will populate `out_dist_sq` when provided, keeping order consistent with other buffers.
- `World.step` and helper methods (`_compute_desired_velocity`, `_separation`, `_resolve_overlap`, `_group_seek_bias`, `_personal_space`, `_intergroup_avoidance`) will consume the shared neighbor distance list when supplied, avoiding fallback recalculation when lengths match.
