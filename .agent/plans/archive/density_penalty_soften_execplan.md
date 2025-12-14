# Density Penalty Softening (Groups Pack Tighter)

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Let same-group agents cluster more easily by weakening high-density penalties (stress, disease, reproduction suppression) while keeping personal-space separation so cubes do not overlap. The result should be visible in headless metrics (denser groups without runaway deaths) and in the viewer (tighter blobs that still avoid overlaps).

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two ("done" vs. "remaining"). Use timestamps.

- [x] (2025-12-13 12:45Z) Drafted plan and constraints.
- [x] (2025-12-13 20:32Z) Implemented density tuning in config defaults and updated README note.
- [x] (2025-12-13 20:37Z) Ran pytest suite and 400-step headless smoke; captured metrics CSV.
- [x] (2025-12-13 20:40Z) Recorded outcomes/metrics snapshot.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- (2025-12-13 20:38Z) Headless 400-step run (seed 42) stabilized around population 112 with 12 groups; tick_duration_ms hovered ~11–12 ms on this machine.

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: Raised `local_density_soft_cap` to 22, doubled `density_reproduction_penalty` to 0.6, softened `density_reproduction_slope` to 0.008, halved disease/death per-neighbor rates, and reduced stress drain per neighbor to 0.006.
  Rationale: Allow tighter group packing without removing negative feedback entirely; keep separation/personal_space unchanged to prevent overlaps.
  Date/Author: 2025-12-13 / Codex

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

- Density penalties are softer by default; same-group blobs can pack closer without immediate disease/stress spikes. Personal-space/separation forces unchanged, so overlaps remain prevented.
- Smoke metrics (seed 42, 400 steps) show stable population (final 112) and healthy energy (~17.7) with group count 12; no runaway growth or extinction observed.

## Context and Orientation

- Repo rules: strict Sim/View separation (View reads snapshots only), no O(N²) scans (SpatialGrid only), maintain determinism (seeded RNG, fixed Δt), preserve negative feedback for stability, Phase 1 cubes + instancing only.
- Key files: `src/terrarium/config.py` (Feedback defaults), `src/terrarium/world.py` (life-cycle density effects, separation/personal-space), `docs/DESIGN.md` (simulation rules), `tests/python/test_world.py` (core behaviors), `src/terrarium/headless.py` (metrics run).
- Locality: neighbor queries stay limited to the SpatialGrid (cell + adjacent cells); any tweaks must reuse the same neighbor list.

## Plan of Work

1) Tuning inputs: adjust FeedbackConfig defaults related to density penalties (soft cap, reproduction penalty/slope, disease and death per neighbor, stress drain) to allow tighter clustering while retaining negative feedback.
2) Overlap guard: leave personal-space and separation forces intact; verify no added O(N²) logic and Sim/View boundary remains unchanged.
3) Docs: add a short note to README (or relevant doc) describing the softened density tuning and how it still prevents overlap.
4) Validation: run `pytest tests/python` and a short headless smoke to confirm stability and performance baselines.

## Concrete Steps

- `.\\.venv\\Scripts\\python -m pytest tests/python`
- `.\\.venv\\Scripts\\python -m terrarium.headless --steps 400 --seed 42 --log artifacts/density_soften_smoke.csv`

## Validation and Acceptance

- Deterministic smoke completes without errors; population stays within [10, max_population] and groups remain >1 after warmup.
- Metrics show births/deaths remain bounded and tick time similar to prior runs; neighbor_checks scale linearly (no O(N²)).
- Visual/manual: in the viewer, same-group blobs pack closer than before but cubes still repel at contact (no obvious overlap).

## Idempotence and Recovery

- Config-only tuning; rerunning with the same seed reproduces trajectories. Revert FeedbackConfig defaults if results regress.
- No persistent storage; restarting resets state. Logs in `artifacts/` can be deleted safely.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples after runs.

## Interfaces and Dependencies

- FeedbackConfig exposes density-related knobs; SimulationConfig passes them through without altering determinism.
- World continues to apply density feedback inside `_apply_life_cycle` using the SpatialGrid neighbor list.
- Tests/headless runners remain the primary validation entry points.
