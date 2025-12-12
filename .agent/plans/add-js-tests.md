# Add JavaScript unit tests for viewer utilities

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Add lightweight JavaScript unit tests around the web viewer utilities so that view-layer logic (e.g., color calculations) stays correct and deterministic. The outcome is a repeatable Node-based test command and pure utility code that the Three.js client uses for consistent rendering without impacting the simulation core (Sim → View remains one-way).

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2025-02-12 00:30Z) Draft plan and orient files.
- [x] (2025-02-12 00:50Z) Extract color utility into a testable module and wire it into the viewer.
- [x] (2025-02-12 01:00Z) Add Node test harness and write assertions for color mapping.
- [x] (2025-02-12 01:15Z) Run JS and Python tests and update docs if needed.
- [x] (2025-02-12 01:20Z) Summarize outcomes and finalize.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: Normalize group hue into [0, 360) via a shared helper and reuse it in the viewer.
  Rationale: Keeps browser rendering deterministic for any group id (including negatives) and enables pure Node tests without adding a rendering dependency.
  Date/Author: 2025-02-12 / assistant

- Decision: Use Node's built-in test runner with a minimal `package.json` (type module) instead of adding external dependencies.
  Rationale: Avoids extra install steps while still providing a repeatable JS test command for the viewer utility.
  Date/Author: 2025-02-12 / assistant

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

- Added `computeGroupHue` helper and rewired the viewer color mapping to use it without introducing Sim→View coupling.
- Established a Node-based JS test suite (`npm run test:js`) covering hue normalization, including negative ids and large values.
- Documented the new JS test command alongside existing Python tests in README. Both JS and Python suites pass after installing requirements.

## Context and Orientation

- Repo root instructions are in `AGENTS.md`; ExecPlan rules are in `.agent/PLANS.md`.
- Web viewer code lives under `src/terrarium/static/`. `app.js` is an ES module loaded by `index.html` to render Three.js cubes from WebSocket snapshots (View reads Sim state only; Sim does not depend on the View).
- There is no existing JavaScript test harness; tests currently cover Python simulation (`tests/python`).
- Goal is to add a small, pure helper (e.g., group color calculation) that is independent from DOM/Three.js so Node tests can exercise it without touching rendering or simulation logic.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1. Create a reusable color utility module in `src/terrarium/static/` that exposes a pure function (e.g., `computeGroupHue`) derived from the existing `groupColor` logic. Keep it free of DOM and Three.js dependencies so Node can import it. Update `app.js` to consume this helper while preserving current behavior and Sim→View separation.
2. Introduce a minimal Node test setup (using built-in `node --test`) under `tests/js/`. Write tests validating deterministic hue mapping (including wraparound and negative ids) to ensure group colors remain stable across changes.
3. Add a `package.json` with `type: module` and a `test:js` script to run the Node tests. Update README test section to mention the new JS test command so docs stay in sync with code changes.
4. Run the new JS tests and the required Python tests (`pytest tests/python`). Document any issues or environment limitations. Ensure no O(N²) or Sim/View coupling is introduced.
5. Update this plan's progress, decisions, and outcomes sections to reflect work done and validation steps completed.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- Run JS tests: `node --test tests/js`
- Run Python tests (required): `pytest tests/python`
- If npm dependencies become necessary in the future, install via `npm install` in repo root; currently expecting no external packages.

## Validation and Acceptance

Describe how to start or exercise the system and what to observe. Phrase acceptance as behavior, with specific inputs and outputs.

- Deterministic smoke check: Node tests should pass, confirming group hue calculation is deterministic for sample ids (including wraparound and negatives). No DOM or WebGL is involved, keeping Sim/View separation intact.
- Python tests remain green (`pytest tests/python`), proving simulation behavior is unaffected by the viewer changes.
- Visual sanity: Viewer still renders colored cubes in the browser, using the extracted color utility; Sim drives state via WebSocket snapshots, View only reads and renders.
- Performance: No runtime changes to simulation; viewer remains instanced rendering with no O(N²) loops. Color helper uses simple arithmetic (O(1)).
- Long-run stability: Unchanged; negative feedback loops and spatial hashing stay in Python core. Viewer remains read-only.

## Idempotence and Recovery

If steps can be repeated safely, say so. If a step is risky, provide a safe retry or rollback path.

- Adding the pure utility and tests is idempotent; rerunning test commands is safe.
- If viewer import fails, revert changes in `src/terrarium/static/app.js` and re-run tests.
- Git can restore previous state via `git checkout -- <file>` for any modified file before commit.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples as the work progresses.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, and interfaces/types that must exist at the end. Prefer stable names and repo-relative paths.

- `src/terrarium/static/color.js` exporting a pure hue helper (e.g., `computeGroupHue(id)` returning a numeric hue 0–360).
- `src/terrarium/static/app.js` imports the helper and uses it to derive `THREE.Color` instances for instanced mesh coloring.
- `tests/js/*.test.js` using Node's test runner to cover the helper behavior.
- `package.json` in repo root declaring `type: "module"` and a `test:js` script running `node --test tests/js`.
- No new runtime dependencies beyond built-in Node modules.
