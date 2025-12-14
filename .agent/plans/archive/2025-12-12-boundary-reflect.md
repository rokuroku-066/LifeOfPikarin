# Replace periodic boundaries with reflective bounce behavior

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

- Plan governance: see `.agent/PLANS.md`. This plan follows those rules.

## Purpose / Big Picture

Switch the terrarium simulation from periodic (wraparound) boundaries to reflective boundaries so agents bounce off the walls. Add tests and docs that match the new behavior and keep long-run stability/determinism intact. Users should see agents stay inside the world and reverse velocity when they hit edges.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2025-12-12 08:30Z) Inspect current world step/boundary handling and related tests/docs.
- [x] (2025-12-12 08:30Z) Implement reflective boundary logic and replace wrap usage.
- [x] (2025-12-12 08:30Z) Update/add unit tests for reflection behavior.
- [x] (2025-12-12 08:30Z) Update design/docs to describe reflective boundaries (and note BoundaryForce status).
- [x] (2025-12-12 08:30Z) Run required test suite and headless smoke; summarize results.
- [x] (2025-12-12 08:30Z) Review for determinism/performance and finalize.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- Headless runner needs `PYTHONPATH=src` when invoked directly; otherwise `ModuleNotFoundError: terrarium` occurs.

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

## Context and Orientation

- Repository constraints to uphold: Simulation/View separation (View reads Sim only), no O(N²) all-pairs (use spatial grid), determinism with seed + fixed timestep, long-run stability via negative feedback, Phase 1 cubes only.
- Target files: `src/terrarium/world.py` (simulation step/wrapping), `tests/python/test_world.py` (boundary tests), `docs/DESIGN.md` (behavior description), potentially `README.md` if boundary behavior is mentioned.
- Current behavior: `World.step()` calls `_wrap` at the end to enforce periodic boundaries. Need to inspect `_wrap` implementation and how velocity is updated.
- Validation expectations: must run `pytest tests/python`; run headless sim to confirm positions stay in bounds and bounce.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1. Review `src/terrarium/world.py` to locate `_wrap`, `step`, and any helper logic that assumes periodic boundaries. Note how positions/velocities are updated and how world size is retrieved.
2. Design a `_reflect(position, velocity, world_size)` helper that mirrors positions crossing 0 or `world_size` and flips corresponding velocity components. Implement with a while loop to handle multiple crossings in one tick while preserving determinism and avoiding extra allocations.
3. Update `World.step()` position update to compute `new_pos = agent.position + agent.velocity * dt` and then assign the reflected position/velocity. Remove or bypass `_wrap` usage; retain determinism.
4. Add/adjust tests in `tests/python/test_world.py` to place agents near each boundary with outward velocity, step once, and assert position remains within [0, world_size] and the velocity component flips sign. Update any wrap-specific expectations to reflection.
5. Update `docs/DESIGN.md` (and `README.md` if it describes wrapping) to state that boundaries are reflective. Mention whether steering BoundaryForce is present or not; clarify current choice.
6. Run `pytest tests/python` (required) and a headless run (`python -m src.terrarium.headless`) long enough to confirm agents stay in bounds and bounce without numeric explosion. Capture key observations.
7. Review changes for performance (no new allocations in hot loops), determinism, and Sim/View separation. Clean up and commit.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- Inspect code: `rg "_wrap" src/terrarium/world.py` then open relevant sections.
- Edit files with `$EDITOR` or apply_patch as needed.
- Run unit tests: `pytest tests/python` from repo root (required).
- Run headless smoke: `python -m src.terrarium.headless --steps 500 --seed 1` (adjust if CLI differs) and confirm positions stay in bounds in logs.

## Validation and Acceptance

Describe how to start or exercise the system and what to observe. Phrase acceptance as behavior, with specific inputs and outputs.

- Unit tests: `pytest tests/python` passes.
- Headless run: run a deterministic headless simulation; observe logs/metrics showing positions remain within [0, world_size] and agents bounce at boundaries; no numerical blow-up over extended steps.
- Functional acceptance: placing an agent near a wall with outward velocity results in position staying inside bounds and velocity component flipping after one step.
- Performance sanity: reflective logic uses simple arithmetic/loops without per-tick allocations; expect similar performance to wrapping for N agents (Phase 1 target scales).
- Stability: negative feedback mechanisms unchanged; reflective boundaries prevent escape without introducing instabilities.
- No O(N²): boundary handling operates per-agent without all-pairs scanning; spatial grid unaffected.
- Sim/View separation: changes stay within simulation; rendering logic unchanged and only reads sim outputs.

## Idempotence and Recovery

- Code edits are standard git-tracked changes; can be reapplied or reverted with git.
- Tests and headless runs are safe to rerun; deterministic given seed.
- If reflective behavior misbehaves, revert to previous commit or adjust helper logic; no irreversible steps.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples. Update with test/headless outputs as work proceeds.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, and interfaces/types that must exist at the end.

- `World` class in `src/terrarium/world.py` exposes `step` with reflective boundary handling via a new helper (e.g., `_reflect`).
- Agents retain position/velocity vectors; reflection operates on numpy arrays or similar without changing interfaces.
- Tests in `tests/python/test_world.py` verify reflective behavior.
- Docs in `docs/DESIGN.md` describe reflective boundaries and clarify boundary steering force status.
