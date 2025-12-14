# Web viewer to Three.js instanced renderer

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

The goal is to replace the current 2D canvas renderer in the web UI with a Three.js-based instanced renderer so that agent snapshots are visualized efficiently in 3D. Users will load the viewer, interact with pan/zoom controls, and see agents rendered via GPU instancing or points while the simulation remains deterministic and driven solely by the backend snapshots.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2024-05-26 00:00Z) Drafted initial ExecPlan for Three.js migration.
- [x] (2024-05-26 00:30Z) Implemented HTML and asset loading changes for Three.js (module script + container).
- [x] (2024-05-26 00:50Z) Implemented Three.js renderer with instancing update path and controls/resizing.
- [x] (2024-05-26 01:10Z) Run required tests and document results.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

## Context and Orientation

The web UI lives under `src/python/static/` with `index.html`, `app.js`, and `styles.css`. Currently `app.js` renders snapshots onto a 2D canvas via `fillRect`. The backend serves agent snapshots over websockets; visualization is decoupled from simulation. The repository enforces separation of simulation and view, avoidance of O(N²) logic, determinism, and long-run stability. Phase 1 visuals are GPU-instanced cubes/points. Tests run via `pytest tests/python`.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1. Update `src/python/static/index.html` to provide a container for the Three.js renderer instead of a fixed 2D canvas, ensure module loading for Three.js, and adjust script tags to import the ES module version of `app.js`. Add CDN or local script for Three.js if needed.
2. Refactor `src/python/static/app.js` into an ES module that initializes a Three.js `Scene`, `PerspectiveCamera`, `WebGLRenderer`, and controls (likely `OrbitControls`). Replace 2D drawing with instanced rendering (e.g., `InstancedMesh` or `Points`). Maintain snapshot handling by updating instance matrices and colors without introducing O(N²) work.
3. Add camera resize handling and controls configuration so users can pan/zoom; ensure renderer mounts to the HTML container. Keep simulation-view separation by consuming snapshots only.
4. Update documentation in `README.md` or `docs` to explain Three.js asset loading, viewer usage, and any new controls or build steps.
5. Add or adjust tests/docs if needed to reflect module changes and run `pytest tests/python` per repo requirements.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- From repo root, edit the static files as described. If using CDN Three.js, no build is needed; otherwise place assets under `src/python/static/`.
- Run formatting if applicable (not specified for JS here).
- Run tests: `pytest tests/python`.

## Validation and Acceptance

Describe how to start or exercise the system and what to observe. Phrase acceptance as behavior, with specific inputs and outputs. Include:
- a deterministic “smoke run” recipe (seed/config/timestep)
- what metrics/log lines to expect
- a visual sanity check recipe (overhead camera, long-run, group behaviors visible)

Acceptance criteria:
- When running the web server and opening the UI, the viewer shows agents rendered via Three.js instancing/points, not 2D canvas rectangles.
- Pan/zoom (e.g., via OrbitControls) works and the view resizes with the window.
- Snapshot updates change instance transforms/colors without stutter; no simulation timing is driven by rendering.
- Deterministic smoke test: run `pytest tests/python` to ensure backend behavior unchanged.
- Performance sanity: viewer handles at least current snapshot sizes with GPU instancing; rendering updates avoid per-frame O(N²) operations.
- Long-run stability: visualization does not alter simulation; backend counters/logs remain deterministic.
- No O(N²): rendering updates loop over agents once per snapshot without nested scanning; controls do not require neighbor queries.
- Sim/View separation: viewer only consumes `/api` or websocket snapshots and never influences simulation tick timing.

## Idempotence and Recovery

If steps can be repeated safely, say so. If a step is risky, provide a safe retry or rollback path.

- Editing static files is idempotent; reloading the page reflects changes. Commit history provides rollback via git.
- Tests can be rerun safely multiple times. If Three.js asset loading fails, revert HTML changes and restore 2D canvas as fallback.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, and interfaces/types that must exist at the end. Prefer stable names and repo-relative paths.

- Three.js library accessible to `src/python/static/app.js` (via CDN module import or local copy under `src/python/static/third_party/three.module.js`).
- `app.js` exported initialization that sets up `Scene`, `Camera`, `Renderer`, controls, and snapshot update handler.
- HTML container with `id` for renderer mount in `index.html`.
- Backend websocket/snapshot interface unchanged; viewer listens and updates instanced objects accordingly.

## Extra acceptance checklist (repo-specific)

Every ExecPlan must include:

* A performance sanity check (what N agents you expect to handle in Phase 1, and how you measure tick time).
* A long-run stability check (what prevents runaway growth/extinction; what you will observe to confirm).
* A “no O(N²)” explicit note (which subsystem enforces locality and how).
* A “Sim/View separation” explicit note (how data flows one-way).
