# 10k-tick headless performance tuning

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated per `.agent/PLANS.md`.

## Purpose / Big Picture

Trim tick_duration_ms during long (10k) headless runs by preventing runaway population/energy growth and by lowering neighbor-query work, while preserving determinism, spatial-grid locality, and Sim/View separation. Target: keep 10k-step run under ~35–40 ms median tick at population well below hard cap.

## Progress

- [x] (2025-12-14 09:53Z) Drafted plan after measuring baseline 10k run (tick_ms ~60ms at pop=1000)
- [x] (2025-12-14 10:02Z) Adjusted config (grid cell_size, food/metabolism, reproduction/density limits)
- [x] (2025-12-14 10:03Z) Ran `python -m pytest tests/python` (pass)
- [x] (2025-12-14 10:06Z) Ran 10k headless tuned run `artifacts/headless_10k_tuned.csv`

## Surprises & Discoveries

- Baseline 10k run (seed 42) hit max_population=1000; tick_duration_ms ~60–110 near end; avg_energy ~162 suggests food/energy overly abundant.
- Tuned config finished 10k steps in ~37s wall-clock; late tick_ms ~2–6 ms with population stabilized ~78.

## Decision Log

- Decision: Increase grid `cell_size` to 6.0 (matching reduced vision radius) to cut neighbor bucket scans while keeping locality via SpatialGrid.
  Rationale: Fewer cell iterations per agent lowers per-tick neighbor overhead without O(N²) risk. Date/Author: 2025-12-14 / Codex
- Decision: Reduce energy inflow and raise energy outflow (food_per_cell 6, regen 0.35, metabolism 0.85, high_energy_metabolism_slope 0.04, birth_energy_cost 10, reproduction_threshold 14, energy_soft_cap 16).
  Rationale: Prevent energy ballooning that fueled births even under density pressure. Date/Author: 2025-12-14 / Codex
- Decision: Strengthen density controls (local_density_soft_cap 16, density_reproduction_slope 0.02, density_death_per_neighbor 0.00008, stress_drain 0.01) and lower max_population to 800.
  Rationale: Keep populations below heavy-load regime via softer cap and stronger negative feedback while avoiding extinction. Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

- Tests passing (Py 3.9.7). Tuned 10k headless (seed 42) ends with population ~78, groups ~37, avg_energy ~11.8, tick_ms ~2–6; big reduction from baseline (~60–110ms at pop 1000). Performance target met with stable, non-extinct population.

## Context and Orientation

- Files: `src/terrarium/config.py` (simulation defaults), `src/terrarium/world.py` (uses cell_size/feedback), `src/terrarium/environment.py` (food regen uses config), `tests/python` for regression.
- Constraints: Sim/View one-way; SpatialGrid locality (no O(N^2)); determinism + fixed dt; long-run stability via feedback (no boom/bust); Phase 1 cubes only.
- Current issue: population saturates hard cap, high energy, leading to large neighbor_checks (~10k) and tick_ms ~60ms.

## Plan of Work

1) Tighten resource/energy feedback: lower base food supply/regen and raise high-energy metabolism + birth cost/threshold so energy stops ballooning.
2) Strengthen density controls: lower local_density_soft_cap and increase reproduction penalty slope + density death/stress drains to keep population below cap naturally.
3) Reduce neighbor workload: increase grid cell_size to match vision radius, shrinking bucket scans.
4) Validate via pytest and 10k headless log; compare tick_ms and population trajectory against baseline.

## Concrete Steps

- Edit `src/terrarium/config.py` to adjust Environment/Species/Feedback defaults and `SimulationConfig.cell_size`.
- Run: `python -m pytest tests/python`
- Run: `PYTHONPATH=src python -m terrarium.headless --steps 10000 --seed 42 --log artifacts/headless_10k_tuned.csv`
- Inspect tail of CSV for population and tick_ms.

## Validation and Acceptance

- All pytest suites pass.
- 10k headless run completes; population stays meaningfully below previous 1000 cap (goal < ~700) and tick_duration_ms median/late-stage is noticeably lower (~<=40ms) without exploding neighbor_checks.
- Long-run stability: population does not crash to 0 and remains bounded; energy averages reasonable (< ~100).
- No O(N^2): SpatialGrid still used; larger cell_size only reduces bucket count.
- Sim/View separation unchanged (only config touched).

## Idempotence and Recovery

- Config-only changes; re-running commands is safe. Original values can be restored by git checkout of `src/terrarium/config.py`.

## Artifacts and Notes

- Baseline log: `artifacts/headless_10k.csv` (pop ~1000, tick_ms ~60-110).
- Tuned log will be written to `artifacts/headless_10k_tuned.csv`.

## Interfaces and Dependencies

- No new APIs; only default config constants are adjusted. Must maintain determinism and existing file structure.
