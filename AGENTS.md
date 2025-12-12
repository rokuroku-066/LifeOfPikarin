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

---

## Repository orientation (expected docs & structure)
- The system design lives in: `docs/DESIGN.md`
  - When implementing anything, align with `docs/DESIGN.md`.
  - If a plan needs context from the design, restate the necessary parts in the plan (do not assume the reader remembers the design doc).

Recommended (but not mandatory) code layout:
- `src/terrarium/` : simulation core, FastAPI server, and static web viewer assets (Python-only)
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

If you cannot run the web viewer in the current environment, prioritize:
- unit tests for the simulation core,
- deterministic step simulation logs (headless),
- and leave a clear manual verification recipe for the user.

---

## Performance expectations (Phase 1)
- Avoid per-tick allocations in tight loops.
- Avoid LINQ in per-agent loops.
- Use preallocated buffers where possible.
- Keep per-agent data compact and contiguous (arrays/structs preferred).
- Record basic performance counters (tick time, neighbor checks, etc.) so regressions can be caught early.

## Mandatory test execution for any modification
To keep the Python simulation stable, **you must run the Python unit tests for every change (no exceptions)**:
1. Before writing code, ensure Python 3.11+ is available (check with `python --version`).
2. Install dependencies via `pip install -r requirements.txt`.
3. Execute `pytest tests/python` from the repository root and wait for it to finish on every edit.
4. If the environment prevents running the test suite, explicitly state the blocking reason in your commit message or PR description and record any manual verification performed.

## Keep code, tests, and docs synchronized
When you change source code, **update the related tests and documentation in the same change**:
- Add or adjust tests that cover the new or modified behavior before you consider the work complete.
- Revise README/AGENTS/design notes or in-repo docs so setup and usage instructions stay accurate.
- Do not defer documentation/test fixes to “later”; treat them as part of the same task.

---

## Review guidelines (if doing code review)
- Verify Sim/View boundary is not violated.
- Verify no O(N²) logic was introduced.
- Verify long-run negative feedback mechanisms still exist and are not accidentally bypassed.
- Verify deterministic seed handling remains intact.

## How to run tests locally
- First-time environment setup (Ubuntu/Debian):
  - `sudo apt update`
  - `sudo apt install -y python3 python3-venv python3-pip`
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
- From the repository root, run the simulation unit tests (required for every change):
  - `pytest tests/python`
- If you add new test suites, list their invocation here to keep validation steps discoverable.
