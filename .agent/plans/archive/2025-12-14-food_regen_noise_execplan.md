# Randomly fluctuate food regeneration (deterministic)

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated. Follow `.agent/PLANS.md`.

## Purpose / Big Picture

The terrarium’s population currently tends to converge to a stable equilibrium as ticks increase. To keep the system visually alive over long observation, we will introduce a deterministic, seed-driven “climate noise” multiplier that slowly fluctuates the global food regeneration rate. This adds a gentle, ongoing push-pull cycle without breaking Sim/View separation or determinism.

The user-visible outcome is that long headless runs show continuing population drift/oscillation instead of a near-flat line, while remaining stable (no runaway explosion and no inevitable extinction).

## Progress

- [x] (2025-12-14 00:00Z) Drafted plan.
- [x] (2025-12-14 15:35Z) Add config knobs for food regen noise.
- [x] (2025-12-14 15:37Z) Implement deterministic climate noise application in Sim.
- [x] (2025-12-14 15:41Z) Add/adjust tests and docs; run `pytest tests/python`.
- [x] (2025-12-14 15:45Z) Run headless test `python -m terrarium.headless --steps 20000 --seed 42 --log artifacts/metrics.csv`
- [x] (2025-12-14 15:46Z) Review the headless test results; adjust if needed.

## Surprises & Discoveries

- `python -m terrarium.headless ...` failed from repo root with `ModuleNotFoundError: No module named 'terrarium'` because `src/` was not on `sys.path` unless installed/editable-installed.
  - Fix: add a small shim package at `terrarium/__init__.py` that extends the package path to include `src/terrarium`.

## Decision Log

- Decision: Implement “random” regen fluctuation via a slow-changing multiplier (target sampled at fixed intervals; smoothed over time), driven by a deterministic RNG stream derived from the simulation seed.
  Rationale: Keeps behavior reproducible, avoids per-cell random noise, and produces gentle long-term variation rather than jitter.
  Date/Author: 2025-12-14 / Codex
- Decision: Make `python -m terrarium.*` runnable from repo root without requiring `pip install -e .`.
  Rationale: Keeps the ExecPlan “Concrete Steps” runnable in a fresh checkout and reduces setup friction.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

- Implemented deterministic “climate noise” that modulates food regeneration globally on environment ticks only (no render coupling) and keeps behavior seed-reproducible.
- Added unit coverage to ensure the multiplier is bounded, changes over time when enabled, and is deterministic for a fixed seed.
- Smoke run (seed=42, steps=20000): population continued to vary (not a flat line) and remained stable (no runaway / extinction).

## Context and Orientation

Key files:

- `src/terrarium/config.py` defines `EnvironmentConfig` and its defaults.
- `src/terrarium/world.py` advances the simulation (fixed timestep) and is responsible for scheduling environment ticks.
- `src/terrarium/environment.py` owns the food field and applies regeneration in `_regen_food`.
- `terrarium/__init__.py` is a lightweight shim so `python -m terrarium.*` works from repo root without editable installs.
- `tests/python/test_world.py` contains determinism-related tests.
- `docs/DESIGN.md` notes that long-run stability can be improved by seasonal/random resource variation.

Repository constraints (must hold after change):

- Simulation (Model) and Visualization (View) are strictly separated; View never drives Sim.
- No O(N²) all-pairs logic; locality comes from `SpatialGrid` neighbor queries only.
- Long-run stability must include negative feedback loops to avoid runaway growth/extinction.
- Determinism matters: seedable, fixed timestep schedule, reproducible outcomes.
- Phase 1 visuals are cubes only; simulation logic must not depend on rendering.

## Plan of Work

1) Expose new environment knobs:
   - `food_regen_noise_amplitude`: max deviation of regen multiplier around 1.0 (e.g. 0.2 => 0.8–1.2).
   - `food_regen_noise_interval_seconds`: how often to sample a new target multiplier.
   - `food_regen_noise_smooth_seconds`: how quickly the multiplier eases toward the target (0 = step changes).

2) Apply multiplier deterministically:
   - Add a small “climate noise” state to `World` that updates only on environment ticks (not render frames).
   - Drive it with a deterministic RNG stream derived from the simulation seed (separate from agent RNG to reduce coupling).
   - Set the current multiplier on `EnvironmentGrid` before calling `EnvironmentGrid.tick(...)`.

3) Use multiplier in environment regen:
   - In `EnvironmentGrid._regen_food`, multiply `cell.regen_per_second` by the current multiplier.

4) Tests and docs:
   - Add a test that asserts the multiplier changes over steps (when enabled), remains bounded, and is deterministic for a fixed seed.
   - Update `docs/DESIGN.md` with a short note about the new knobs (ties back to “seasonal/random resource variation”).

## Concrete Steps

From repo root:

1) Confirm Python:
   - `python --version`

2) Run tests (before/after change):
   - `pytest tests/python`

3) Run a deterministic smoke sim and record metrics:
   - `python -m terrarium.headless --steps 20000 --seed 42 --log artifacts/metrics.csv`
   - Inspect whether population continues to drift/oscillate instead of fully flattening.

## Validation and Acceptance

Acceptance is met when:

- Determinism: Two runs with the same `seed` and config produce identical results (metrics sequence).
- O(N²): No new global pairwise scans are introduced; climate update is O(1) per environment tick.
- Long-run behavior: In a long headless run (>= 20000 steps), population does not collapse permanently to a flat line; it shows continuing gentle variation without runaway explosion/extinction.
- Sim/View separation: Only simulation code changes; static web viewer remains read-only of snapshots.

Performance sanity check:

- Use the existing `tick_ms` metric; expect no meaningful regression because the climate update is a handful of float ops per environment tick.

## Idempotence and Recovery

- The change is configuration-controlled: set `food_regen_noise_amplitude = 0` or `food_regen_noise_interval_seconds <= 0` to disable and revert to constant regen behavior.
- If the population becomes too volatile, reduce `food_regen_noise_amplitude` or increase `food_regen_noise_smooth_seconds`.

## Artifacts and Notes

- Headless metrics: `artifacts/metrics.csv` (seed=42, steps=20000)
  - Population range (whole run): 200..412
  - Last 10000 steps: min/max 241..272 (still variable; not a flat line)

## Interfaces and Dependencies

- `EnvironmentConfig` gains three float fields for regen noise.
- `World` owns climate-noise state and updates it on environment ticks using deterministic RNG.
- `EnvironmentGrid` gains a multiplier and uses it in `_regen_food`.
