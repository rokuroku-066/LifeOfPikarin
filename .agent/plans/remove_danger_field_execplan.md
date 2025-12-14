# Remove danger field system (危険フィールド撤去)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Remove the "danger field" mechanism entirely from the simulation core:

- No `danger` scalar field stored in `EnvironmentGrid`.
- No diffusion/decay work for `danger`.
- No sampling/gradient steering based on `danger`.
- No config knobs for `danger`.

After the change, the simulation remains deterministic and stable under fixed timesteps; the viewer continues to render cubes from snapshots (View reads only; Sim is not driven by View); and unit tests pass.

## Progress

- [x] (2025-12-14 23:04Z) Verified baseline: `pytest tests/python` passes (31 tests).
- [x] (2025-12-14 23:10Z) Remove `danger_*` config and environment storage.
- [x] (2025-12-14 23:10Z) Remove `danger` steering/deposit logic from `World`.
- [x] (2025-12-14 23:11Z) Update docs/tests that mention `danger`.
- [x] (2025-12-14 23:12Z) Re-run `pytest tests/python` and confirm pass.
- [x] (2025-12-14 23:13Z) Smoke run: `python -m terrarium.headless --steps 500 --seed 42`.
- [x] (2025-12-14 23:15Z) Commit + push changes to the current branch (`20c8ff1`).

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Remove the `danger` field entirely (not just disable via config).
  Rationale: Request explicitly asks to abolish the mechanism; carrying dead config/paths adds maintenance cost and ambiguity.
  Date/Author: 2025-12-14 (Codex)

## Outcomes & Retrospective

`danger` field was fully removed (config, environment storage, world steering/deposit), and docs/tests were updated to match. The sim remains deterministic/seeded and bounded by spatial-grid neighbor queries; `pytest tests/python` passes and a headless smoke run completes.

## Context and Orientation

Repository constraints relevant to this change:

- **Sim/View separation**: the simulation advances in fixed timesteps and must not depend on rendering; the viewer only reads snapshots.
- **No O(N²)**: neighbor interactions must remain limited to spatial-grid local queries.
- **Determinism**: RNG must remain seedable and reproducible.
- **Long-run stability**: avoid destabilizing population feedback loops; prefer local, density-driven mechanisms.

Current implementation locations (before removal):

- `src/terrarium/config.py`: `EnvironmentConfig` defines `danger_diffusion_rate`, `danger_decay_rate`, `danger_pulse_on_flee`.
- `src/terrarium/environment.py`: `EnvironmentGrid` stores `_danger_field` and diffuses/decays it in `tick()`.
- `src/terrarium/world.py`: `World` samples danger, computes a gradient, biases steering away, and deposits danger pulses.
- `tests/python/test_environment.py`, `README.md`, `docs/DESIGN.md`: describe/parameterize the danger field.

## Plan of Work

1) Remove `danger_*` configuration from `EnvironmentConfig` and from any loader/usage sites.

2) Remove all `danger` storage and update logic from `EnvironmentGrid`:
   - Delete `_danger_field`/`_danger_buffer` and their reset behavior.
   - Delete `sample_danger()` / `add_danger()`.
   - Remove the `danger` diffusion/decay call from `tick()`.

3) Remove all danger-related logic from `World`:
   - Remove `_pending_danger` queue and its application.
   - Remove danger sampling and gradient steering.
   - Keep local flee/avoidance behavior that does not rely on a global field (e.g. close-range inter-group repulsion).

4) Update tests and docs:
   - Remove references to `danger_*` in unit tests.
   - Update README and design doc sections that describe environment fields to match reality (food + pheromone only).

5) Validate determinism and correctness:
   - Run `pytest tests/python`.
   - Run a deterministic headless smoke sim and confirm it completes without errors and produces plausible metrics.

## Concrete Steps

From repo root (`c:\\LifeOfPikarin`):

1) Edit code/docs (see Plan of Work).

2) Run unit tests (mandatory):

   - `pytest tests/python`

   Expected: all tests pass.

3) (Optional but recommended) Run a deterministic smoke sim:

   - `python -m terrarium.headless --steps 2000 --seed 42 --deterministic-log --log artifacts/metrics_no_danger.csv`

   Expected: command completes; CSV is created; values are stable across repeated runs with same flags (except file timestamp/OS metadata).

4) Commit + push:

   - `git status`
   - `git commit -am "<message>"` (plus add any new files)
   - `git push`

## Validation and Acceptance

Acceptance criteria (human-verifiable):

- Running `pytest tests/python` passes.
- Headless sim can run for thousands of steps without exceptions.
- Viewer still connects and renders agents (no schema changes expected).
- No simulation step depends on viewer timing (Sim/View separation preserved).
- No new all-pairs neighbor logic was introduced; spatial-grid neighbor collection remains bounded.

## Idempotence and Recovery

- Changes are safe to retry by re-running tests and smoke sim commands.
- If something breaks, rollback path is `git restore .` (discard working tree changes) or `git revert <commit>` after commit.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

No external dependencies added.

Key public interfaces that must remain functional:

- `terrarium.environment.EnvironmentGrid.tick()` for food/pheromone updates.
- `terrarium.world.World.tick()` fixed timestep stepping and snapshot emission.
- `pytest tests/python` suite.
