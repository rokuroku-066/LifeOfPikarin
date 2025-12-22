# Remove group food spawn and global population pressure logic

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Refer back to `/workspace/LifeOfPikarin/.agent/PLANS.md` for repository-wide planning rules; this document follows those requirements.

## Purpose / Big Picture

Eliminate the free group-food spawning mechanism and the global population pressure death term so the simulation relies on local interactions, resources, and existing density feedbacks for stability. After this change, configs should no longer expose these controls, and the world step should not enqueue or consume any group-food spawn or global population pressure logic.

## Progress

- [x] (2025-12-19 05:10Z) Mapped all code/config touchpoints for `group_food_spawn` and `global_population_pressure`.
- [x] (2025-12-19 05:12Z) Removed the related config fields and world processing while keeping sim/view separation and spatial grid usage intact.
- [x] (2025-12-19 05:13Z) Updated tests to reflect the removals and ran `pytest tests/python`.
- [x] (2025-12-19 05:24Z) Stripped remaining group-food field handling from `environment.py`, adjusted docs/tests, and re-ran `pytest tests/python`.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Use targeted removals to keep group-food consumption structures intact while deleting the free-spawn path and global pressure hazard term.
  Rationale: Limits change scope to requested behaviors without disrupting other resource mechanics.
  Date/Author: 2025-12-19 / assistant

## Outcomes & Retrospective

Removed the free group-food spawn path and the global population pressure hazard while keeping other resource mechanics intact. Config surface now excludes the deprecated fields, the environment grid no longer tracks dormant group-food fields, and tests verify their absence. Validation via `pytest tests/python` passed after the edits.

## Context and Orientation

Relevant modules:
- `src/terrarium/config.py`: Defines `FeedbackConfig` and other configuration dataclasses.
- `src/terrarium/world.py`: Houses lifecycle logic, pending field queues, and hazard calculations.
- Tests under `tests/python/` validate determinism and lifecycle behaviors.
- Environment-related group food data lives in `src/terrarium/environment.py`, but only the spawn hook in `world.py` populates it.

Simulation must stay deterministic (`DeterministicRng`), use the spatial grid for locality (no O(N²)), and keep simulation timing independent from visualization.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.
- Update `FeedbackConfig` (config.py) to remove `group_food_spawn` and `global_population_pressure` fields and any neighbor threshold used solely for spawning.
- In `world.py`, delete `_pending_group_food` handling, the `_maybe_spawn_group_food` helper, and any calls/queues tied to it; ensure field application no longer processes group-food spawn entries.
- Remove the global population pressure hazard from `_apply_life_cycle` so mortality depends only on base/age/density and existing feedbacks.
- Adjust or add tests in `tests/python` to assert the removed fields are absent and that lifecycle logic no longer references the deleted behaviors.

## Concrete Steps

Commands to run from repo root:
- Inspect current references: `rg "group_food_spawn" src tests` and `rg "global_population_pressure" src tests`.
- After code edits, run the mandatory test suite: `pytest tests/python`.
Expected: Tests should pass with no new flaky behavior; runtime similar to current suite.

## Validation and Acceptance

Acceptance criteria:
- Config dataclasses no longer expose group-food spawn or global population pressure fields.
- World step executes without queuing or applying group-food spawn events.
- Lifecycle hazard computation omits any global population pressure term.
- Tests updated to reflect removals and `pytest tests/python` passes.

Deterministic smoke check: run `pytest tests/python` (covers deterministic step comparisons). Long-run stability relies on existing local density/resource feedbacks; removing global pressure should not introduce O(N²) logic.

Performance sanity: unchanged spatial grid usage and no new per-tick allocations introduced by the removals.

Sim/View separation: all changes confined to simulation core; no visualization timing hooks added.

## Idempotence and Recovery

Edits are standard code removals; rerunning the steps is safe. If a change needs rollback, `git checkout -- <file>` for touched files and rerun tests.

## Artifacts and Notes

- Validation: `pytest tests/python` (all tests passed).

## Interfaces and Dependencies

No new external dependencies. Existing interfaces remain except for removed config fields; tests should validate their absence to prevent accidental reuse.
