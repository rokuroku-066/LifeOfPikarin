# Intra-group Clustering and Inter-group Spacing

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Tighten cohesion inside the same group so flocks stay compact, while increasing repulsion from other groups so different-colored colonies keep respectful spacing. The change should be visible both in headless metrics (more persistent groups, lower cross-group mingling) and in the Web viewer (clusters that pack together and avoid other clusters).

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two ("done" vs. "remaining"). Use timestamps.

- [x] (2025-12-13 02:10Z) Drafted ExecPlan and reviewed design constraints.
- [x] (2025-12-13 03:30Z) Implemented group spacing tuning (config weights, steering logic), added tests, and updated docs.
- [x] (2025-12-13 03:50Z) Ran pytest, 600-step headless CSV, and web /api/status probe (population ~120, groups ~11).

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- (2025-12-13 03:55Z) Headless 600-step run (seed 42): nearest-neighbor averages same-group=3.51, other-group=12.69; groups ≈11; last tick_ms ~15.6 with population 180.

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: ...
  Rationale: ...
  Date/Author: ...

- Decision: Added explicit ally vs. other separation weights plus inter-group soft avoidance radius/weight (defaults: ally_cohesion_weight 1.3, ally_separation_weight 0.35, other_group_separation_weight 1.35, other_group_avoid_radius 6.0, other_group_avoid_weight 0.9); kept panic flee for very close contact.
  Rationale: Make same groups pack tightly while pushing different groups apart before collisions, without changing determinism or O(N^2) behavior.
  Date/Author: 2025-12-13 / Codex

## Outcomes & Retrospective

- Steering changes (ally cohesion vs. other separation/avoid) remain deterministic and covered by existing world tests; new group-switch guard keeps clusters from dissolving into majority with too few neighbors.
- Latest validation: pytest (25) and npm test:js both green. Long-run 20k-tick headless run (seed 42) ended with population 499 and 46 colonies (avg last 10k ticks 66.17), showing tighter in-group packing and sustained multi-colony coexistence without O(N²) work.

## Context and Orientation

- Repo rules: strict Sim/View separation, no O(N^2) neighbor scans (use SpatialGrid only), preserve determinism (seeded RNG), maintain long-run negative feedback to avoid explosion/extinction, Phase 1 cubes only. These apply to all changes.
- Key files: src/terrarium/world.py (steering, grouping, life cycle), src/terrarium/config.py (Simulation/Feedback/Species parameters), tests/python/test_world.py (group behaviors), src/terrarium/headless.py (deterministic headless run), src/terrarium/static/app.js + index.html (viewer consuming snapshots).
- Spatial locality: neighbor queries already limited to grid plus adjacent cells via SpatialGrid; any new logic must stay inside this data.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1) Parameter hooks: extend FeedbackConfig in config.py with explicit weights/radii for same-group cohesion and cross-group avoidance so tuning is deterministic and testable. Provide sensible defaults that favor tighter internal packing and earlier cross-group repulsion.
2) Steering update in world.py:
   - In _compute_desired_velocity, introduce a mid-range inter-group avoidance force (before panic flee) using neighbor offsets; keep it local (same neighbor list) with falloff.
   - Strengthen _group_cohesion and reduce same-group separation weight so allies can sit closer; keep max speed/accel clamps unchanged.
   - Ensure FLEE still triggers on very close cross-group contact but allow softer spacing to prevent mixing earlier.
3) Group stress/density tuning: if needed, adjust stress accumulation or reproduction penalties so denser same-group packing does not explode population; keep negative feedback intact.
4) Tests: add unit tests in tests/python/test_world.py verifying (a) desired velocity pulls an agent toward its same-group neighbors more than toward mixed ones, and (b) other-group agents induce stronger outward force than same-group agents at equal distance. Keep tests deterministic by fixing velocities and RNG seeds.
5) Validation scripts:
   - Headless: run ./.venv/Scripts/python -m terrarium.headless --steps 600 --seed 42 --log artifacts/headless_group_spacing.csv and check metrics (population stable, groups count >1, no extinction).
   - Quick spatial probe: add a short inline check (e.g., small script in notes) computing average nearest-neighbor distance to same-group vs other-group after a snapshot; expect same-group average < other-group.
   - Web viewer: uvicorn terrarium.server:app --port 8000 --reload, open in browser, observe tighter clusters and clearer gaps between differently colored groups over ~2-3 minutes.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- ./.venv/Scripts/python -m pytest tests/python
- ./.venv/Scripts/python -m terrarium.headless --steps 600 --seed 42 --log artifacts/headless_group_spacing.csv
- uvicorn terrarium.server:app --port 8000 --reload

## Validation and Acceptance

Describe how to start or exercise the system and what to observe.

- Deterministic smoke: headless run for 600 ticks with seed 42 finishes without errors; population remains below max_population and above 10; metrics show groups >= 2 after warmup.
- Behavior check: in a scripted snapshot, average distance to nearest same-group neighbor is at least 20% lower than to nearest other-group neighbor; inter-group avoidance keeps mixed neighbors rare.
- Visual sanity: in the Web viewer (top-down camera), agents of the same color form tight blobs; blobs maintain a visible gap when near other colors and do not continuously intermix; motion stays smooth with instanced cubes.
- Performance: tick time in headless metrics stays within current baseline (<5 ms per tick on the provided hardware for ~120+ agents); neighbor_checks still scales linearly with N (no O(N^2)).
- Stability: no runaway growth or extinction within a 5-minute web run; stress/density feedback still applied.

## Idempotence and Recovery

If steps can be repeated safely, say so. If a step is risky, provide a safe retry or rollback path.

- Config changes are deterministic; rerunning headless/web with the same seed should reproduce trajectories. If tuning overshoots, revert parameter defaults and rerun tests/headless.
- No migrations or persistent storage; restarting the server resets state. Deleting artifacts/headless_group_spacing.csv is safe.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples.

- To be populated with headless CSV sample rows and pytest output after runs.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, and interfaces/types that must exist at the end.

- FeedbackConfig exposes new fields for intra-group cohesion strength and inter-group avoidance weight (defaulted for Phase 1); SimulationConfig wiring passes them through unchanged.
- World._compute_desired_velocity, _separation, _group_cohesion consume the new weights without altering the Sim/View boundary.
- Tests in tests/python/test_world.py assert deterministic steering priorities using existing World API.
- headless.py remains the entry point for smoke runs; server.py and static/app.js keep consuming snapshots unchanged.
