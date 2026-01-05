# Blend ally cohesion/alignment during flee steering

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md. This plan is maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

When agents flee from danger or rival groups, they should still keep cohesion and alignment with allies. This makes fleeing appear as a grouped escape while still prioritizing threat avoidance. The change is visible by observing that agents in the same group flee together rather than scattering.

## Progress

- [x] (2025-09-27 19:15Z) Inspect current flee handling and locate steering logic that returns early.
- [x] (2025-09-27 19:18Z) Implement blended flee desired velocity with ally cohesion/alignment, separation, and boundary avoidance.
- [x] (2025-09-27 19:21Z) Add/update tests to validate flee blending behavior.
- [x] (2025-09-27 19:22Z) Update design documentation to reflect blended flee behavior.
- [x] (2025-09-27 19:25Z) Run required Python tests.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Start with fixed weights for cohesion/alignment/separation in flee mode, with a keep factor scaled by danger level.
  Rationale: Matches user request for a simple blend while preserving flee dominance.
  Date/Author: 2025-09-27 / Codex

## Outcomes & Retrospective

Blended flee behavior now mixes ally cohesion/alignment with separation and boundary avoidance, and tests confirm the flee vector is moderated by allied presence while still fleeing. Documentation updated to match behavior.

## Context and Orientation

The flee handling lives in `src/terrarium/sim/systems/steering.py` inside `compute_desired_velocity`. It currently returns early when `flee_vector` is non-zero. Ally cohesion is computed by `group_cohesion`, alignment by `alignment`, and separation by `separation`. Boundary avoidance is handled by `boundary_avoidance` later in the same function.

This task changes simulation rules, so it must preserve determinism, use the spatial grid for neighbors (no O(N^2) changes), maintain Sim/View separation, and avoid per-tick allocations beyond existing patterns.

## Plan of Work

Edit `compute_desired_velocity` to build a blended desired velocity when fleeing. Keep flee as the dominant term, then add ally cohesion/alignment (same group only), separation for collision avoidance, and boundary avoidance. Apply a keep factor that reduces cohesion/alignment when danger is strong. Ensure the function returns the blended `Vector2` while still setting `AgentState.FLEE`.

Add a test in `tests/python/test_world.py` that seeds a danger gradient causing flee and verifies that adding an ally produces a less extreme flee vector (still fleeing but pulled toward ally). Update `docs/DESIGN.md` to describe the new blended flee behavior.

## Concrete Steps

Run these commands from the repo root:

1. Inspect current steering behavior:

   rg -n "flee_vector" -S src/terrarium/sim/systems/steering.py
   sed -n '1,220p' src/terrarium/sim/systems/steering.py

2. Implement blended flee behavior in `src/terrarium/sim/systems/steering.py`.

3. Add/update tests in `tests/python/test_world.py`.

4. Update design documentation in `docs/DESIGN.md`.

5. Run required tests:

   python --version
   pip install -r requirements.txt
   pytest tests/python

Expected: tests pass without failures.

## Validation and Acceptance

A deterministic smoke run is already covered by `pytest tests/python` for core behaviors. The new test should show:

- When fleeing, desired velocity still points away from danger.
- Adding an ally causes the flee vector to be less extreme (cohesion/alignment influence) without reversing direction.

Manual visual sanity check (if runnable): start the viewer and confirm grouped agents flee in clusters rather than scattering.

Explicit constraints:

- No O(N^2): neighbor inputs remain from spatial grid; no new all-pairs loops.
- Sim/View separation: only steering logic changes in sim; view remains read-only.
- Determinism: no new randomness is introduced.
- Long-run stability: flee blending should not remove negative feedback mechanisms.

Performance sanity check: observe tick time remains stable for 200+ agents in existing profiling logs; no additional per-agent allocations beyond existing vectors.

## Idempotence and Recovery

Edits are localized and can be reverted by restoring the previous flee early-return logic. Re-running tests is safe and repeatable.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

Uses existing steering helpers: `group_cohesion`, `alignment`, `separation`, `boundary_avoidance`, and `fields.danger_gradient`. No new dependencies.
