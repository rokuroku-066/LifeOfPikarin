# Spatial grid and environment hotpath allocation cuts

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. This plan must be maintained per `.agent/PLANS.md`.

## Purpose / Big Picture

Reduce per-tick allocations and redundant work in spatial queries, environment diffusion, and world neighbor processing to keep the simulation deterministic, allocation-light, and stable for long runs. The expected outcome is lower GC pressure and fewer repeated calculations without altering sim/view separation or behavior.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2025-05-10 00:00Z) Drafted plan and gathered current code paths for SpatialGrid, EnvironmentGrid diffusion, and World neighbor handling.
- [x] (2025-05-10 00:35Z) Implemented spatial grid clear/insert tweaks, environment diffusion allocation cuts, and neighbor distance reuse in world processing.
- [x] (2025-05-10 00:38Z) Ran `pytest tests/python` after dependency check.

## Surprises & Discoveries

- Unit tests require backward-compatible `_compute_desired_velocity` signature; added optional neighbor distance parameter instead of changing positional order.

## Decision Log

- Decision: Prioritize allocation removal in spatial grid insert/clear before refactoring world neighbor loops.
  Rationale: Spatial grid changes affect all neighbor queries and offer immediate allocation wins.
  Date/Author: 2025-05-10 Codex

## Outcomes & Retrospective

- Allocation-focused optimizations landed with all simulation tests passing; neighbor distance reuse keeps logic deterministic while trimming repeated length computations.

## Context and Orientation

- Spatial grid neighbor hashing: `src/terrarium/spatial_grid.py` (`insert`, `clear`, `collect_neighbors_precomputed`).
- Environment diffusion and accumulation: `src/terrarium/environment.py` (`_diffuse_group_food`, `_diffuse_field`, `_add_key`).
- World neighbor handling and gradients: `src/terrarium/world.py` (`_compute_desired_velocity`, `_clamp_traits`, neighbor loops).
- Design constraints: Sim and View stay separated; no O(N²) neighbor scans (all neighbor work uses spatial grid); determinism and seed reproducibility; negative feedback loops remain intact; Phase 1 cube rendering only.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1) Spatial grid hotpath cleanups (`src/terrarium/spatial_grid.py`):
   - Replace `setdefault` in `insert` with explicit lookup/append using preallocated empty buckets to avoid per-call list creation.
   - Change `clear` to drop the cell dict instead of iterating all buckets; ensure neighbor buffers reset correctly.
2) Environment diffusion allocation cuts (`src/terrarium/environment.py`):
   - Hoist common neighbor offsets to a shared constant/tuple to avoid recreating per call.
   - Replace `_add_key` list conversion with tuple math and clamp without list allocations.
   - Remove redundant assignments and list creations in `_diffuse_group_food` and `_diffuse_field` while preserving clamping.
3) World gradient and neighbor loop optimizations (`src/terrarium/world.py`):
   - Avoid recomputing danger gradients twice in `_compute_desired_velocity`.
   - Ensure trait clamping is applied only once per agent per tick (reuse clamped traits for downstream calculations).
   - Collapse multiple neighbor passes where distance squared is recomputed; compute `dist_sq` once per neighbor where possible and reuse for group checks/separation inputs.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

1) Edit files per Plan of Work in `/workspace/LifeOfPikarin`.
2) Install dependencies if needed:
   - `python --version`
   - `pip install -r requirements.txt`
3) Run simulation unit tests (mandatory after changes):
   - `pytest tests/python`

## Validation and Acceptance

- Deterministic smoke run: run `pytest tests/python` to ensure simulation logic remains deterministic and stable.
- Performance sanity: confirm neighbor handling now avoids per-call allocations (inspect hot functions) and ensure ticks still report metrics without O(N²) scans; expect stable runtime for existing tests.
- Long-run stability: logic keeps negative feedbacks (stress, density penalties, diffusion decay) unchanged; no neighbor loop expands beyond spatial grid queries.
- Sim/View separation: edits stay within simulation core and do not gate simulation on rendering.

## Idempotence and Recovery

- Code edits are repeatable; rerun tests after changes.
- If changes introduce regressions, revert the modified sections via git checkout on the touched files and reapply with smaller increments.

## Artifacts and Notes

- `pytest tests/python` (2025-05-10): all 33 tests passed after adjustments.

## Interfaces and Dependencies

- SpatialGrid public API (`insert`, `clear`, `collect_neighbors_precomputed`) remains the same signature.
- EnvironmentGrid diffusion helpers keep dictionary-based fields/buffers with clamped keys.
- World behavior/state structures stay compatible with existing Agent/Config dataclasses; no interface changes expected.
