# Refactor terrarium package layout and split world.py into systems/types/utils

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is stored at `.agent/plans/terrarium-structure-refactor.md` and must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

The current `src/terrarium/world.py` is extremely large and the package layout is flat. The goal is to reorganize the package into `app/` and `sim/` subpackages, split `world.py` into focused modules (core, systems, types, utils), and update imports/tests/docs so the project remains runnable. Success is visible when the server/headless entrypoints still work, tests pass, and `World.step()` reads as a thin orchestrator calling system helpers.

## Progress

- [x] (2025-01-13 01:05Z) Create new package directories under `src/terrarium/` and relocate app/static assets and simulation core modules.
- [x] (2025-01-13 01:20Z) Split `world.py` into systems/types/utils modules and rewire `World` to use them.
- [x] (2025-01-13 01:35Z) Update imports across tests/docs and update packaging metadata in `pyproject.toml`.
- [x] (2025-01-13 01:55Z) Run required Python setup and tests; collect verification notes.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Use the user-proposed directory layout (app + sim/core/systems/types/utils) without backward-compat wrapper modules.
  Rationale: This reduces ambiguity and matches the requested plan while keeping filenames stable to lower movement cost.
  Date/Author: 2025-01-13 / Codex
- Decision: Move group/steering/lifecycle/field logic into dedicated system modules that operate on the `World` instance.
  Rationale: Keeps `World.step()` as a thin orchestrator while minimizing behavioral changes to the simulation core.
  Date/Author: 2025-01-13 / Codex

## Outcomes & Retrospective

Completed the package refactor, moved app/static assets and simulation core modules into the new layout, and split `world.py` into systems/types/utils modules. Tests pass with updated imports, and documentation reflects the new entrypoints.

## Context and Orientation

The repository currently keeps all Terrarium modules directly under `src/terrarium/` (e.g., `world.py`, `agent.py`, `server.py`). The task is to move app entrypoints into `src/terrarium/app/`, core simulation components into `src/terrarium/sim/core/`, and split the large `world.py` into smaller modules:

- `sim/utils/math2d.py` for vector math helpers and clamps.
- `sim/types/metrics.py` for `TickMetrics`.
- `sim/types/snapshot.py` for snapshot dataclasses.
- `sim/systems/` for group/steering/lifecycle/fields/metrics logic.
- `sim/core/world.py` retains the `World` class, but becomes a thin orchestrator.

Key files to change include `pyproject.toml`, tests under `tests/python`, and docs (`README.md`, `docs/snapshot.md`).

Terminology: "Sim" refers to the deterministic simulation core. "View" refers to rendering or visualization that consumes snapshots, which must never drive the Sim.

## Plan of Work

Start by creating the new package directories and moving server/headless/static into `app/`. Move core simulation modules (`agent.py`, `config.py`, `environment.py`, `rng.py`, `spatial_grid.py`) into `sim/core/`. Move `world.py` to `sim/core/world.py` and then split it into module clusters: math helpers into `sim/utils/math2d.py`, dataclasses into `sim/types/metrics.py` and `sim/types/snapshot.py`, and system methods into `sim/systems/*`. Update `World` to import and call these system helpers in `step` while maintaining the same behavior.

Then update all imports in tests, app modules, and any other references to the new paths. Update `pyproject.toml` to use `setuptools.packages.find` and adjust package data for the relocated static assets. Finally update README/docs to reflect the new module paths and commands. Run mandatory Python version check, dependency install, and `pytest tests/python`.

## Concrete Steps

Run all commands from the repository root.

1) Create directories and init files, then move app modules and static assets.
   Expected: `src/terrarium/app/` contains `server.py`, `headless.py`, and `static/`.

2) Move simulation core modules into `src/terrarium/sim/core/` and move `world.py` into that folder.
   Expected: `src/terrarium/sim/core/world.py` exists with updated imports.

3) Split `world.py` into `sim/utils/math2d.py`, `sim/types/metrics.py`, `sim/types/snapshot.py`, and system modules under `sim/systems/`.
   Expected: `World.step()` references system functions; helper modules import only what they need.

4) Update imports across tests, app modules, and any other references. Update packaging metadata in `pyproject.toml`.
   Expected: no references to `terrarium.world`, `terrarium.server`, etc.

5) Update documentation for new entrypoints and module paths.

6) Run required Python version check, install dependencies, and run tests.

## Validation and Acceptance

Behavioral acceptance is:

- The simulation remains deterministic and the View only consumes snapshots. `World.step()` does not depend on rendering state.
- All neighbor interactions still use `SpatialGrid` and no new O(N²) loops are introduced.
- Population feedback loops and lifecycle logic are unchanged and still run in the same order.
- The server and headless entrypoints are usable at the new paths.

Required validation steps:

- Deterministic smoke run: `python -m terrarium.app.headless --steps 100 --seed 1` and confirm the run completes with consistent metrics logs.
- Unit tests: `pytest tests/python`.
- Visual sanity check: `uvicorn terrarium.app.server:app --reload --port 8000` and load the viewer to verify agents move smoothly in the fixed camera view.
- Performance sanity check: run headless with a large population and observe tick time logs (e.g., `--steps 300 --seed 1` with default config), confirming no sudden regressions.
- Long-run stability check: run headless for an extended period and verify population stabilizes without runaway growth or total extinction.
- Explicit no O(N²) note: neighbor interactions remain inside `SpatialGrid.collect_neighbors_precomputed` using local cells.
- Explicit Sim/View separation note: only snapshot data flows from Sim to View; no rendering hooks in the Sim modules.

## Idempotence and Recovery

File moves can be safely re-run with `git status` checks; if a move fails, revert with `git restore` or re-run `git mv` to correct. Module splits are safe to re-apply by re-opening the target files and ensuring the functions live in the expected module.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

The following interfaces must exist and be importable at the end:

- `terrarium.app.server:app` and `terrarium.app.headless:run_headless` entrypoints.
- `terrarium.sim.core.world.World` class.
- `terrarium.sim.core.agent.Agent`, `AgentState`, `AgentTraits`.
- `terrarium.sim.core.config.SimulationConfig` and related config types.
- `terrarium.sim.core.environment.EnvironmentGrid` and `FoodCell`.
- `terrarium.sim.core.rng.DeterministicRng`.
- `terrarium.sim.core.spatial_grid.SpatialGrid`.
- `terrarium.sim.types.metrics.TickMetrics`.
- `terrarium.sim.types.snapshot.Snapshot` and related snapshot dataclasses.
- `terrarium.sim.utils.math2d` helper functions.
