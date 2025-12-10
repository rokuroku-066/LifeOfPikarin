# AGENTS.md

## Project: Long-run Terrarium (Cube Phase) — Visual Alife Sandbox

This repository aims to build a long-running, overhead-camera terrarium simulation for a visual art piece.
Phase 1 renders agents as cubes (GPU instancing) while the simulation runs deterministically and stably for long observation.

Codex: Read this file before doing any work and follow it as default working agreements.

---

## What matters (non-negotiables)

### 1) Strict separation: Simulation (Model) vs Visualization (View)
- The Simulation Core must advance in fixed timesteps and must NOT depend on rendering or animation timing.
- The View must only read simulation outputs (pose/state signals) and may interpolate for smooth visuals.
- Do not block or delay simulation state transitions because an animation “is not finished”. (View must never control Sim.)

### 2) Avoid O(N²)
- No “all pairs” scanning across all agents.
- All local interactions (neighbor queries, flocking, mating, crowding, etc.) must use Spatial Hash / Uniform Grid.
- Any per-agent loop may only examine:
  - its local cell, and
  - adjacent cells (e.g., 3×3 neighborhood).

### 3) Long-run stability (open-ended, but not self-destructing)
- The system must include negative feedback loops to prevent:
  - runaway population growth, and
  - total extinction being “the only attractor”.
- Preferred mechanisms:
  - density-driven stress / disease probability,
  - resource depletion and regeneration,
  - reproduction suppression under high density,
  - energy/metabolism pressure.

### 4) Determinism & reproducibility
- The simulation must be seedable.
- Given the same config + seed + fixed timestep schedule, the simulation should be reproducible.
- Avoid using non-deterministic sources for simulation randomness.

---

## Phase 1 scope (Cube implementation only)
- Visuals: cubes only, rendered with GPU instancing (no per-agent GameObject spam).
- No FBX rigs/Animator complexity in Phase 1.
- Focus: simulation correctness, performance, long-run stability, and visually legible emergent group behaviors.

Phase 2 (FBX replacement) will happen later; do not pre-optimize for FBX beyond keeping the Sim/View boundary clean.

---

## Repository orientation (expected docs & structure)
- The system design lives in: `docs/DESIGN.md`
  - When implementing anything, align with `docs/DESIGN.md`.
  - If a plan needs context from the design, restate the necessary parts in the plan (do not assume the reader remembers the design doc).

Recommended (but not mandatory) code layout:
- `src/Sim/` : engine-agnostic simulation core (pure C# data + logic)
- `src/Unity/` : Unity integration, renderers, scene wiring
- `docs/` : design + notes
- `.agent/PLANS.md` : ExecPlan authoring rules (see below)

If the repo already has a different structure, follow existing conventions.

---

## ExecPlans (required for non-trivial tasks)
When writing complex features, performance work, or multi-file refactors, use an ExecPlan as described in `.agent/PLANS.md` from design to implementation.

Rules:
- If a task touches >2 files, introduces a new subsystem, or changes simulation rules, start by drafting an ExecPlan.
- Keep the ExecPlan as a living document: update Progress / Decisions / Discoveries as you go.

---

## How to prompt Codex effectively in this repo (what you should do)
When acting as Codex in this repo:
- Prefer clear code pointers: repo-relative file paths, identifiers, and greppable names.
- Always include verification steps: how to run, what to observe, and how to know it worked.
- Split large tasks into smaller milestones so each is testable and reviewable.

---

## Validation expectations (Phase 1)
Every meaningful change must come with a way to verify:
- A deterministic “smoke run” for N steps (headless or in-editor) that logs:
  - population count,
  - births/deaths,
  - group counts (or proxies),
  - average energy/age,
  - any stability metrics.
- A visual sanity check:
  - the terrarium runs for an extended period without obvious numerical blowups,
  - agents move smoothly (View interpolation is fine),
  - group formation and splitting are visually legible from an overhead camera.

If you cannot run Unity in the current environment, prioritize:
- unit tests for the simulation core,
- deterministic step simulation,
- and leave a clear manual verification recipe for the user.

---

## Performance expectations (Phase 1)
- Avoid per-tick allocations in tight loops.
- Avoid LINQ in per-agent loops.
- Use preallocated buffers where possible.
- Keep per-agent data compact and contiguous (arrays/structs preferred).
- Record basic performance counters (tick time, neighbor checks, etc.) so regressions can be caught early.

---

## Review guidelines (if doing code review)
- Verify Sim/View boundary is not violated.
- Verify no O(N²) logic was introduced.
- Verify long-run negative feedback mechanisms still exist and are not accidentally bypassed.
- Verify deterministic seed handling remains intact. 
