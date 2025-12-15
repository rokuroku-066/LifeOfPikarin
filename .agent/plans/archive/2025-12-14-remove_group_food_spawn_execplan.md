# Remove group-food spawning knobs and mechanic

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated. Follow `.agent/PLANS.md`.

## Purpose / Big Picture

Remove the group-food spawning configuration knobs (neighbor threshold, spawn chance, spawn amount), and remove the simulation mechanic that used them (dense same-group clusters spawning group-only food). This simplifies the Simulation Core and avoids carrying around dead/rarely-used mechanics while keeping determinism, Sim/View separation, and spatial-local interactions intact.

User-visible outcome: there is no longer any “group-only ration/clan food” spawning behavior, and the config surface no longer exposes those keys. The Python unit test suite continues to pass.

## Progress

- [x] (2025-12-14 17:03Z) Audit current usages (config, world logic, tests, docs).
- [x] (2025-12-14 17:06Z) Remove config fields and all code paths that depend on them.
- [x] (2025-12-14 17:08Z) Remove/update tests and docs that describe the mechanic.
- [x] (2025-12-14 17:10Z) Run `pytest tests/python` and confirm green.
- [x] (2025-12-14 17:11Z) Confirm repo has no remaining references to the removed keys.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Remove the entire “group-only food” system rather than leaving an inert field behind.
  Rationale: With the spawning knobs removed there is otherwise no production path for group food, leaving unused code and config behind; removing the mechanic end-to-end is clearer and reduces maintenance surface.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

- Removed the group-food spawning knobs and the entire group-only food system (env field + world event queue + consumption path). Updated design/docs and removed the old ExecPlan that described the mechanic. `pytest tests/python` passes on Python 3.11.9.

## Context and Orientation

Relevant code paths before this change:

- `src/terrarium/config.py`: `FeedbackConfig` contained three group-only food spawning fields; `EnvironmentConfig` contained the group-only food field parameters.
- `src/terrarium/world.py`: per-agent loop spawned and queued group-only food events; `_apply_life_cycle` consumed group-only food first; `_tick_environment` pruned the per-group field; `_apply_field_events` applied pending food-field events.
- `src/terrarium/environment.py`: stored a per-group food field keyed by `(cell_x, cell_y, group_id)` with decay/diffusion/cap and pruning.
- `tests/python/test_world.py`: contained tests for spawn + exclusivity behavior.
- `docs/DESIGN.md`: described group-only ration field spawning when same-group agents cluster densely.

Repo constraints to uphold:

- Sim/View separation: Simulation core uses fixed timesteps and must not depend on rendering.
- No O(N²): local interactions must use SpatialGrid locality (cell + neighbors).
- Long-run stability: preserve negative feedback loops; avoid introducing runaway growth/extinction attractors.
- Determinism: seedable RNG and fixed timestep schedule; no non-deterministic randomness.
- Phase 1 scope: cubes/GPU instancing only; no rendering-side coupling changes.

## Plan of Work

1) Remove the three config fields from `FeedbackConfig` and update any code that references them.
2) Remove the group-food spawn/queue/application code paths from `World`.
3) Remove group-food field support from `EnvironmentGrid` (storage, diffusion/decay, pruning).
4) Remove tests covering group-food behavior, and update any docs/ExecPlans that mention the removed mechanism.
5) Run unit tests and verify no remaining references to the removed keys.

## Concrete Steps

From repository root:

1) Edit code:
   - `src/terrarium/config.py`
   - `src/terrarium/world.py`
   - `src/terrarium/environment.py`
   - `tests/python/test_world.py`
   - `docs/DESIGN.md`
   - `.agent/plans/performance_smoothing_execplan.md` and remove/retire `.agent/plans/group_cluster_food_execplan.md`

2) Run:
   - `python --version`
   - `pytest tests/python`

3) Verify no references remain:
   - Search the repo for stale group-food spawning identifiers and confirm there are no remaining hits.

## Validation and Acceptance

- Unit tests: `pytest tests/python` passes.
- No removed-key references remain in the repository.
- Headless smoke run still works (manual): `python -m terrarium.headless --steps 3000 --seed 42 --log artifacts/metrics_smoke.csv`.
- Sim/View separation remains unchanged (no viewer coupling changes in this task).

## Idempotence and Recovery

- Edits are safe to reapply on a clean tree (pure deletions/refactors).
- If a downstream config YAML still contains the removed keys, loading will fail fast; the fix is to delete those keys from the YAML.

## Artifacts and Notes

- None yet.

## Interfaces and Dependencies

- `FeedbackConfig` no longer exposes group-food spawn knobs.
- The Simulation Core no longer contains any group-only food field or event queue.
