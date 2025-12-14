# Smooth step performance pass (reduce stutter)

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated. Follow `.agent/PLANS.md`.

## Purpose / Big Picture

Reduce frame-time stutter by trimming per-tick allocations and unnecessary loops in the Simulation Core without changing behavior: reuse neighbor passes, skip empty-field diffusion work, and avoid copying agent lists each tick. Maintain determinism, Sim/View separation, spatial-grid locality, and long-run stability.

## Progress

- [x] (2025-12-14 17:05Z) Drafted plan
- [x] (2025-12-14 17:20Z) Implemented loop/alloc reductions in world + environment
- [x] (2025-12-14 17:22Z) Ran `python -m pytest tests/python` (pass on Python 3.9.7)
- [x] (2025-12-14 17:23Z) Reviewed results and updated plan

## Surprises & Discoveries

- Current runtime Python 3.9.7 (not 3.11+). Pytest previously passed on 3.9.7.

## Decision Log

- Decision: Eliminate per-step agent list copy and merge same-group/cluster neighbor counting into a single pass before group membership updates.
  Rationale: Cuts per-tick allocations and duplicate iteration while preserving existing behavior (counts taken before membership changes).
  Date/Author: 2025-12-14 / Codex
- Decision: Short-circuit group-food diffusion when no clan food exists.
  Rationale: Avoids needless dict churn each environment tick, reducing stutter when clan-food feature is unused.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

- Per-tick allocations reduced (no agent list copy; combined neighbor counting). Group-food diffusion now short-circuits when empty, trimming idle work. All tests pass; behavior remains deterministic, with group-food spawn still using post-membership group IDs when they change (recomputed only on change).

## Context and Orientation

- Files: `src/terrarium/world.py` (main per-tick loop), `src/terrarium/environment.py` (field diffusion/decay), `tests/python/test_world.py` (regressions).
- Constraints: no O(N²) (keep spatial grid), deterministic RNG and fixed timestep, Sim/View separation intact, Phase 1 cubes only, long-run stability preserved.

## Plan of Work

1) In `world.step`, stop copying the agent list each tick; iterate directly since births are queued and removals happen after the loop.
2) Merge same-group neighbor counting and close-ally counting into one pass (reuse for reproduction penalty and clan-food spawn) to remove an extra loop.
3) In `environment._diffuse_group_food`, early-return when no clan food is present to avoid unnecessary buffers; keep cap/decay/diffusion behavior otherwise unchanged.
4) Run tests; if stutter persists, profile further hotspots (not in scope for this quick pass).

## Concrete Steps

- Edit `src/terrarium/world.py`: adjust main loop iteration and merge neighbor count + cluster count; keep behavior identical (counts before group changes).
- Edit `src/terrarium/environment.py`: guard `_diffuse_group_food` with empty-field early return.
- Validate with `python -m pytest tests/python`.

## Validation and Acceptance

- All Python tests pass.
- No behavioral changes: group membership logic and clan-food spawning remain deterministic; energy balances unchanged.
- Micro-stutter reduced: per-tick allocations removed, empty-field diffusion skipped (observable as lower GC/CPU in long runs).

## Idempotence and Recovery

- Edits are safe to reapply; early return only bypasses work when no clan food exists.

## Artifacts and Notes

- None yet.
