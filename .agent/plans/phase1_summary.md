# Phase 1 ExecPlan Summary (through 2025-12-15)
- All ExecPlans through Phase 1 have been moved to `.agent/plans/archive/`.

## Chronological work log
- 2024-05-05: Phase 2 snapshot signals prework. Added heading/metadata to snapshots without changing the loop; ran pytest.
- 2024-05-19: Replaced custom Vec2 with pygame.math.Vector2, keeping behavior via safe normalize/clamp helpers; pytest passed.
- 2024-05-21: Exported sparse food/pheromone fields in snapshots and rendered translucent overlays in the viewer; tests captured.
- 2024-05-26: Added environment resource patches plus hazard/pheromone fields with regen/diffuse/decay ticks (reused dicts to avoid allocations). Migrated viewer to Three.js instancing, replacing the 2D canvas.
- 2024-06-03: Formalized diffusion+decay for food/pheromone/danger fields and integrated them into AI weighting; added escape fallback when gradients are absent.
- 2024-06-14: Refreshed viewer to perspective with lighting/shadows; server now sends velocity; client interpolation buffer smooths motion.
- 2025-01-05: Unity 6 C#9 compatibility (file-scoped->block, record->class, init->set). SimTests pass on .NET 8.416.
- 2025-02-12: Extracted viewer color calc to `computeGroupHue`, added Node built-in tests, documented `test:js` in README.
- 2025-02-17: Implemented group isolation hysteresis and switching. Added loneliness accumulator, majority switch, and cohesion steering; verified with pytest.
- 2025-05-03: Removed legacy C#/Unity and made the repo Python-only. Cleaned README/deps; pytest green.
- 2025-05-18: Fixed World.Reset to rebuild environment/RNG for seed reproducibility (full_implementation follow-up).
- 2025-12-10: Full_implementation finishing touches (vision-radius filter, scratch reuse, removed TickDuration from deterministic compares, headless runner/CSV). C#9 compat tests passed. In remaining_tasks ran a 3000-tick smoke (p95 6.77 ms, births/deaths continue) and synced Unity DTOs. population_stability advanced first births by tuning initial energy/repro/density+age hazards.
- 2025-12-10: Ported environment_field_diffusion to Python; wired food/pheromone/danger diffusion/decay order into World.step; ran tests.
- 2025-12-11: group_formation_dynamics starts all agents ungrouped, adds warmup-gated local create/merge/split; updated metrics and Unity mapper.
- 2025-12-12: Switched periodic->reflective boundaries and updated tests/docs (discovered PYTHONPATH=src requirement). Split web viewer into three cameras (top/angle/POV) and adjusted angled camera height.
- 2025-12-13: boundary_avoidance adds wall bias and heading correction; sanitized out-of-bounds environment keys.
- 2025-12-13: group_clustering strengthens same-group cohesion and cross-group spacing; pytest and 600-tick smoke (pop ~180, groups ~11).
- 2025-12-13: cube_phase1_appearance adds energy brightness, age scaling, reproduction pulse; JS helper tests and manual visual check done.
- 2025-12-13: density_penalty_soften relaxes density stress/disease/repro suppression so flocks pack tighter (400-tick smoke: pop 112, groups 12).
- 2025-12-13: perf_pheromone_clamp clamps field keys to bounds, adds decay, prunes dead group layers, rewrites broken config.py in UTF-8. At 3000 ticks, tick_ms plateaus around 40 ms.
- 2025-12-13: perf_smooth adds environment tick throttling, cached wander direction, vision 6/cell 3, pixel-ratio cap; 500-tick avg 12.85 ms / p95 19.3 ms.
- 2025-12-13: group_wide_split lets lonely grouped agents bud a new group (groups 21, pop 110 at 400 ticks).
- 2025-12-13/14: group_size_split_scaling adds size-proportional split probability plus merge cooldown/minority guard/recruit. 12k ticks (seed 42) yield average groups 42.6 in the latter half, no collapse, pytest green.
- 2025-12-14: Improved spatial neighbor lookup by reusing grid references, logging headless timing in `artifacts/headless_neighbor_perf.csv`.
- 2025-12-14: Tuned config for 10k headless runs (cell size, food/energy/density feedback) to cut tick_duration_ms to ~2–6 ms late-run at pop ~78.
- 2025-12-14: Added group base anchors and stronger close-range repulsion to tighten clustering without overlap; updated configs/tests.
- 2025-12-14: Boosted adoption for small groups by relaxing neighbor thresholds and increasing join chance; pytest verified.
- 2025-12-14: Removed group-food spawning knobs/mechanics and scrubbed remaining references; tests stayed green.
- 2025-12-14: Reduced stutter by trimming per-tick allocations and loop work in world/environment while keeping determinism; pytest passed.
- 2025-12-14: Introduced deterministic climate noise multiplier for food regeneration to keep populations oscillating gently over long runs; validated with headless smoke and pytest.
- 2025-12-14: Baseline pytest recorded ahead of removing the unused danger field system.
- 2025-12-14: Final Phase 1 cleanup—added neighbor-threshold guard for group switching, cross-platform `npm run test:js`, pheromone pruning regression test, README/DESIGN parameter updates, ExecPlan outcomes, and a 20k-tick headless run (seed 42) logged to `artifacts/headless_20000.csv` (pop_final 499, groups_final 46, tick_ms_mean 28.9, p95 55.3).
- 2025-12-15: Added a deterministic 5000-tick regression test with tuned configs (caps, neighbor radius, environment cadence, group dynamics) to hold peak population at 400–500, keep 5–10 groups, and keep average tick_duration_ms under 25 ms.

## Issues encountered and fixes
- Missing dotnet SDK blocked tests -> installed .NET 8.416 on Windows and reran SimTests.
- Headless run raised `ModuleNotFoundError: terrarium` -> set PYTHONPATH=src.
- pygame not installed on system Python -> install deps in project `.venv`, rerun pytest.
- `config.py` contained control chars/missing fields -> rewrote in UTF-8 and added pheromone decay.
- Pheromone field grew unbounded and slowed ticks -> clamp coordinates, add default decay, prune dead-group layers to cap dict size.
- Group adoption randomness made tests flaky -> set `group_adoption_chance=0` in tests for determinism.
- Danger/food gradient sampling spawned OOB keys -> clamp indices and sanitize keys.
- `npm run test:js` path failed on Windows -> use `node --test .\\tests\\js\\*.js` as a workaround.
- PowerShell Add-Type couldn't load net8 DLL for smoke run -> used SimRunner/headless CLI to log 3000 ticks.
- Environment diffusion ran every tick and was heavy -> added `environment_tick_interval` to throttle and improved timings.

## Unresolved items
- None for Phase 1 (cube scope).

## Remaining tasks
- None; keep monitoring long-run metrics when introducing Phase 2 features.
