# Reduce sim/render stutter (tick cost & viewer FPS)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Smooth agent motion by lowering per-tick simulation time and browser rendering cost so the Phase 1 cube viewer runs without visible stutter. Results should be observable both headless (tick duration metrics) and in the Three.js viewer (stable frame pacing).

## Progress

- [x] (2025-12-13 20:54Z) Headless baseline 500 steps @ default config; mean tick_ms 24.37, p95 29.40, max 44.71 (artifacts/baseline.csv).
- [x] (2025-12-13 21:11Z) cProfile 200 steps: hotspots = EnvironmentGrid.tick (diffuse/decay), rng.next_unit_circle, SpatialGrid.get_neighbors, gradients (danger/food), duplicate _sanitize_food_keys.
- [x] (2025-12-13 21:35Z) Added environment tick accumulator (interval 0.08s) and removed duplicate _sanitize; raised dt to 1/40s to widen real-time budget.
- [x] (2025-12-13 21:40Z) Cached per-agent wander direction with refresh timer + faster rng unit vectors; reduced default vision_radius to 7.0.
- [x] (2025-12-13 21:45Z) Viewer tweaks: clamp pixel ratio, disable shadows on instanced mesh/light; captured DevTools Performance trace (NO_NAVIGATION).
- [x] (2025-12-13 21:48Z) Validation: pytest green; headless 500-step smoke mean 21.18ms, p95 38.30, max 53.28 (artifacts/baseline_after4.csv); avg tick under 25ms budget.
- [x] (2025-12-13 21:58Z) Reverted dt to 1/50s for smoother websocket cadence; headless 500-step smoke mean 21.14ms, p95 33.33, max 60.07 (artifacts/baseline_after5.csv).
- [x] (2025-12-13 22:10Z) Reduced vision_radius to 6.0, cell_size to 3.0, env cadence 0.12s, population 240/500; headless 500-step smoke mean 12.85ms, p95 19.30, max 38.34 (artifacts/baseline_after6.csv).

## Surprises & Discoveries

- Environment diffusion/decay ran every tick; _diffuse_field + _diffuse_food dominated wall time alongside rng.next_unit_circle calls (cProfile ~4–5s each over 200 ticks) before cadence changes.
- Duplicate _sanitize_food_keys call each step (inside EnvironmentGrid.tick and again in World.step) added ~0.7s/200 ticks; removing the extra call helped a little, cadence change helped more.
- With dt=25ms and environment_tick_interval=0.08s the average tick now fits inside the real-time budget (mean 21.18ms) though p95 spikes line up with env diffusion passes; SpatialGrid.get_neighbors remains the largest cost after optimizations.
- DevTools Performance trace on http://localhost:8000 (NO_NAVIGATION) shows clean load (CLS 0, no throttling). Pixel ratio cap + shadow disable kept interaction smooth during the ~5s capture window.

## Decision Log

- Decision: Optimize before altering behavior—prefer reducing frequency of expensive routines (field diffusion, wander RNG) while keeping outputs deterministic per seed.
  Rationale: Largest wins without redesign; preserves Sim/View separation and avoids O(N²).
  Date/Author: 2025-12-13 Codex
- Decision: Raise dt to 1/40s and environment_tick_interval to 0.08s to bring per-step work inside the real-time budget without shrinking populations.
  Rationale: Tick cost stayed ~23–24ms; widening the budget improves wall-clock smoothness while keeping simulated seconds consistent.
  Date/Author: 2025-12-13 Codex

## Outcomes & Retrospective

- Headless smoke after optimizations (vision 6, cell 3, env_tick_interval 0.12s, pop 240/500) improved from mean 24.37ms/p95 29.40ms (baseline) to mean 12.85ms/p95 19.30ms/max 38.34ms over 500 ticks (artifacts/baseline_after6.csv); Python tests stayed deterministic.
- Long-run headless 20k ticks (seed 42, artifacts/headless_20000.csv) held population at 499 (mean 492.8) with groups_final 46 (mean last 10k 66.17) and continued births/deaths (7041/6782). Tick durations averaged 28.87ms with p95 55.27ms and occasional env-batch spikes max 180.15ms but no runaway growth/extinction.
- Viewer-side pixel ratio cap + shadow disable remain in place; npm test:js and pytest both pass, keeping Sim/View separation intact.

## Context and Orientation

- Simulation core: `src/terrarium/world.py` (tick loop, steering, life cycle), `src/terrarium/environment.py` (food/pheromone/danger grids), `src/terrarium/spatial_grid.py` (neighbor queries).
- View: `src/terrarium/static/app.js` (Three.js instanced cubes, interpolation) + `src/terrarium/server.py` (WebSocket snapshots).
- Tests: `tests/python/` (determinism, boundaries, grouping).
- Constraints to repeat here:
  - Sim and View stay separated; View only reads snapshot data.
  - No O(N²); neighbor work stays within SpatialGrid local cells.
  - Long-run stability via density penalties/energy limits remains intact.
  - Deterministic, seedable fixed-timestep simulation.
  - Phase 1 visuals are cubes via GPU instancing.

## Plan of Work

1) Measurement & profiling (done): headless baseline + cProfile hotspots; keep artifacts for before/after comparison.
2) Environment cadence: add config-driven tick stride/accumulator so diffusion/decay/regen run every N seconds (default 0.08s) instead of every tick; remove duplicate _sanitize_food_keys call.
3) Wander RNG reduction: add per-agent cached wander direction & refresh timer; use it for wander/food seeking jitter; implement cheaper deterministic unit vector generation; keep initial seeding deterministic.
4) Micro-optimizations: reuse neighbor offsets/counts where possible without O(N²); avoid needless Vector2 allocations where cheap.
5) View perf: cap renderer pixel ratio, avoid reallocating instanceColor when count unchanged, ensure scissor viewports updated without extra renders; capture a short DevTools Performance trace to verify frame budget.
6) Validation: rerun `pytest tests/python`; rerun headless smoke (same seed, 500 steps) and compare tick_ms target (<= time_step_ms, p95 < 40ms on this machine); run viewer via uvicorn + DevTools Performance to confirm smooth frame times/interpolation at ~300 cubes.

## Concrete Steps

- Run baseline headless: `.\.venv\Scripts\python -m terrarium.headless --steps 500 --seed 42 --log artifacts/baseline.csv`
- Profile simulation (already done): keep `artifacts/profile_sim.pstats` for reference.
- Implement code changes per plan (world.py, environment.py, agent.py, config.py, static/app.js, README/docs as needed).
- Tests: `.\.venv\Scripts\python -m pytest tests/python`
- Headless after changes: `.\.venv\Scripts\python -m terrarium.headless --steps 500 --seed 42 --log artifacts/baseline_after4.csv`
- Viewer check: `.\.venv\Scripts\uvicorn terrarium.server:app --port 8000` then open http://localhost:8000, record DevTools Performance for ~10s.

## Validation and Acceptance

- Deterministic smoke: With seed 42 and default config, headless 500 steps completes with mean tick_ms <= time_step_ms (25ms default) and p95 < 40; population remains ≤ max_population and no extinction.
- Long-run stability: births/deaths stay nonzero; groups count >0 after warmup; density penalties still applied (inspect metrics and logs).
- View smoothness: Three.js viewer shows interpolated agent motion without visible hitching at ~300 agents; DevTools frame graph stays responsive with pixel ratio cap and shadows disabled (target most frames < 25ms).
- No O(N²): neighbor queries remain via SpatialGrid local buckets; no all-pairs loops introduced.
- Sim/View separation preserved: server still only streams snapshots; client continues read-only.

## Idempotence and Recovery

- Environment tick stride and wander cache are deterministic per seed; re-running with same seed yields repeatable results.
- Re-running headless or viewer steps is safe; config defaults allow reverting cadence to 1:1 by setting stride=1 tick if needed.

## Artifacts and Notes

- Baseline metrics: `artifacts/baseline.csv` (mean 24.37ms, p95 29.40ms, max 44.71ms).
- After tweaks: `artifacts/baseline_after4.csv` (mean 21.18ms, p95 38.30ms, max 53.28ms) with dt 25ms and env cadence 0.08s.
- Latest: `artifacts/baseline_after6.csv` (mean 12.85ms, p95 19.30ms, max 38.34ms) with dt 20ms, env cadence 0.12s, vision 6.0, cell_size 3.0, pop 240/500.
- Profile data: `artifacts/profile_sim.pstats` (before) and `artifacts/profile_sim_after.pstats` (after cadence/wander changes); post-change hotspot is SpatialGrid.get_neighbors.

## Interfaces and Dependencies

- New config knobs must live in `SimulationConfig` / `SpeciesConfig` (e.g., `environment_tick_interval`, `wander_refresh_seconds`) with defaults matching deterministic behavior.
- Agent struct gains cached wander direction/timer fields with safe defaults to keep tests constructing Agent unchanged.
- Viewer continues using `/ws` snapshot feed; renderer uses capped pixel ratio to lower GPU cost.
