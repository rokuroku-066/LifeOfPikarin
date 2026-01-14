# World step performance optimizations

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Per repository rules, this plan is maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Improve per-tick performance of the terrarium simulation by removing hot-loop allocations and redundant per-agent computations in `World.step`, group membership updates, overlap resolution, and lifecycle updates. The user-visible effect is faster ticks with identical simulation outcomes, verified by running the required Python tests and a deterministic headless run recipe.

## Progress

- [x] (2025-09-24 02:10Z) Inspect `World.step` and the hot per-agent loops in `src/terrarium/sim/core/world.py`, `src/terrarium/sim/systems/steering.py`, `src/terrarium/sim/systems/groups.py`, and `src/terrarium/sim/systems/lifecycle.py`.
- [x] (2025-09-24 02:28Z) Remove per-tick Vector2 allocations in `_reflect` and `resolve_overlap`, replace position assignment with in-place updates, and reuse scratch `paired_ids`.
- [x] (2025-09-24 02:28Z) Precompute group detach radius and base cell keys in `World.step` and pass them into group/lifecycle helpers.
- [x] (2025-09-24 02:32Z) Update documentation to reflect the new hot-loop strategy and run required Python checks/tests.
- [x] (2025-09-24 02:33Z) Summarize outcomes and verification steps.

## Surprises & Discoveries

In-place position updates mutated a shared `Vector2` used in a group-base test. The test now snapshots the initial coordinates to avoid relying on mutable shared references.

## Decision Log

- Decision: Use in-place updates for position/velocity and return scalar values from `_reflect` to avoid temporary `Vector2` allocations.
  Rationale: This removes per-agent allocations in the hot loop without changing behavior.
  Date/Author: 2025-09-24 / Codex

## Outcomes & Retrospective

`World.step` now updates positions in place, `resolve_overlap` clamps corrections without allocating new `Vector2` instances, and group/lifecycle helpers receive precomputed detachment radii and cell keys. The group base test was updated to avoid relying on shared mutable vectors. Required Python tests pass.

## Context and Orientation

The simulation core lives in `src/terrarium/sim/core/world.py`, where `World.step` advances agents and records `TickMetrics`. Group and lifecycle logic live in `src/terrarium/sim/systems/groups.py` and `src/terrarium/sim/systems/lifecycle.py`, while overlap correction and steering live in `src/terrarium/sim/systems/steering.py`. The overall behavior is described in `docs/DESIGN.md`.

Key hotspots include:
1. `World.step` agent loop and steering integration.
2. Overlap resolution in `steering.resolve_overlap`.
3. Group membership updates in `groups.update_group_membership`.
4. Lifecycle updates in `lifecycle.apply_life_cycle`.

Terms:
- “cell key” refers to the integer grid coordinate used by `EnvironmentGrid` to access per-cell fields.
- “in-place update” means calling `Vector2.update(x, y)` instead of replacing the `Vector2` instance.

## Plan of Work

Edit `src/terrarium/sim/core/world.py` to avoid allocating `Vector2` in `_reflect`, update positions in place, reuse a scratch set for `paired_ids`, and compute group detachment radius and base cell keys once per agent.

Edit `src/terrarium/sim/systems/steering.py` to update `resolve_overlap` in-place using scalar correction values.

Edit `src/terrarium/sim/systems/groups.py` to accept precomputed `detach_radius_sq` and close-neighbor thresholds passed from `World.step`.

Edit `src/terrarium/sim/systems/lifecycle.py` to accept a precomputed base cell key from `World.step`.

Update `docs/DESIGN.md` to mention the in-place hot-loop strategy for positions/overlap correction.

## Concrete Steps

1. Update `World.step` in `src/terrarium/sim/core/world.py` to use in-place position updates, reuse scratch `paired_ids`, and pass precomputed detachment radius/base cell keys to group/lifecycle helpers.
2. Update `_reflect` to return scalars and update caller code accordingly.
3. Update `resolve_overlap` in `src/terrarium/sim/systems/steering.py` to apply corrections in place using scalar clamping.
4. Update `groups.update_group_membership` and `lifecycle.apply_life_cycle` signatures to accept precomputed values.
5. Update `docs/DESIGN.md` with a short note on the in-place hot-loop strategy.
6. Run:
   - `python --version`
   - `pip install -r requirements.txt`
   - `pytest tests/python`

Expected transcript snippet (examples):
    Python 3.11.x
    ...
    ====== 100% ======
    1 passed in ...

## Validation and Acceptance

- Deterministic smoke run: `python -m terrarium.app.headless --steps 200 --seed 42 --summary tests/artifacts/summary.json` should complete without errors and show stable population metrics in the summary JSON.
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
