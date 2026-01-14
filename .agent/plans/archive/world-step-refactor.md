# Refactor World.step orchestration into private helpers

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is stored at `.agent/plans/world-step-refactor.md` and must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

This change makes the simulation tick flow in `World.step` easier to read and maintain by extracting well-scoped helper methods, while preserving deterministic behavior and the existing simulation rules. The resulting code should be functionally identical, with the same RNG call order and neighbor buffer reuse, but organized around explicit stages so future changes are safer.

## Progress

- [x] (2025-12-26 04:28Z) Draft plan and confirm constraints for refactoring `World.step` without behavior changes.
- [x] (2025-12-26 04:28Z) Refactor `src/terrarium/sim/core/world.py` using in-file helper methods and a tick context container, keeping RNG and neighbor buffer behavior unchanged.
- [x] (2025-12-26 04:28Z) Run required Python checks (`python --version`, `pip install -r requirements.txt`, `pytest tests/python`).
- [x] (2025-12-26 04:28Z) Update plan with outcomes, decisions, and validation notes.
- [x] (2025-12-26 04:39Z) Adjust tick timing so metrics include finalize work and re-run required tests.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Keep all refactor helpers inside `world.py` and avoid new modules to preserve locality and reduce change surface.
  Rationale: The request explicitly forbids new modules and emphasizes minimal change.
  Date/Author: 2025-12-26 / Codex

## Outcomes & Retrospective

`World.step` has been reorganized into helper methods with a tick context and aggregate container while keeping the existing order of operations, neighbor buffer reuse, and RNG call patterns. Tick duration accounting now includes finalize work by measuring after `_finalize_tick` again. The Python test suite completed successfully after the timing fix.

## Context and Orientation

`World.step` in `src/terrarium/sim/core/world.py` handles the per-tick simulation loop, including neighbor queries, group membership updates, steering, movement integration, lifecycle effects, and aggregate metrics. This method currently contains the full control flow and per-agent logic. The refactor should split logic into private helpers while keeping deterministic RNG calls and the neighbor buffer reuse (`self._neighbor_agents`, `self._neighbor_offsets`, `self._neighbor_dist_sq`).

Determinism requirements apply: random streams are deterministic and call order must not change. Simulation and View remain strictly separated. Neighbor interactions must use `SpatialGrid` and avoid O(N²) scans. Long-run stability logic (feedback, population controls) must remain intact.

## Plan of Work

Update `src/terrarium/sim/core/world.py` by introducing a `TickContext` dataclass and additional small private methods to cover phases described in the task (begin tick, rebuild spatial index, prepare agent, collect neighbors, update group membership, compute steering, integrate motion, apply lifecycle, apply danger pulse, accumulate stats, finalize tick). Replace the monolithic `World.step` body with calls to these helpers while keeping the same order of operations and no new branching.

## Concrete Steps

Run commands from the repository root:

- `python --version`
- `pip install -r requirements.txt`
- `pytest tests/python`

Expected output for `python --version` is Python 3.11+.

## Validation and Acceptance

Validation requires `pytest tests/python` to pass. A deterministic smoke run and visual verification are not added in this refactor, but the method order and RNG usage remain unchanged, so existing tests should still cover determinism expectations.

Acceptance criteria:

- `World.step` behavior matches previous logic, including RNG call ordering and neighbor buffer reuse.
- Neighbor queries still rely on `SpatialGrid` and only local cells.
- Simulation/View separation remains unchanged because only simulation code is refactored.
- Tick metrics remain identical for the same seed.

Performance sanity check: refactor introduces no new allocations in tight loops beyond existing logic; neighbor buffers are reused.

Long-run stability check: existing feedback mechanisms remain unchanged because lifecycle and group/steering logic are untouched.

No O(N²) check: neighbor access remains via `SpatialGrid.collect_neighbors_precomputed` and uses its precomputed offsets.

Sim/View separation check: no changes to view-facing data or rendering.

## Idempotence and Recovery

Edits are confined to `world.py` and can be reverted via `git checkout -- src/terrarium/sim/core/world.py`. Running tests is repeatable.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

- `src/terrarium/sim/core/world.py` retains `World.step` and adds helper methods on `World` plus a local `TickContext` dataclass.
- Uses existing modules `groups`, `steering`, `lifecycle`, `fields`, and `metrics` without interface changes.
