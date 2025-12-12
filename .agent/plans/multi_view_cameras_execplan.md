# Multi-view cameras for web viewer (top/angle/agent POV)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Enable the web viewer to show three simultaneous viewpoints: a fixed overhead top-down camera on the left, an angled camera from the field edge on the upper right, and an agent-follow camera on the lower right that switches to a new random agent when the current one dies. Users can observe global patterns and individual behavior at once.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2025-12-12 00:50Z) Draft ExecPlan and gather context from AGENTS.md, DESIGN.md, current web viewer files.
- [x] (2025-12-12 01:20Z) Implement HTML/CSS layout to host three viewports and labels.
- [x] (2025-12-12 02:05Z) Update Three.js code to render a shared scene to three cameras (top/angle/agent POV) with scissor viewports; add agent selection/switching logic.
- [x] (2025-12-12 02:30Z) Manual visual check in browser (chrome-devtools) to confirm layout and camera behavior.
- [ ] (2025-12-12 02:45Z) Run `pytest tests/python` and ensure pass.
- [x] (2025-12-12 02:55Z) Update README (or viewer docs) to describe the three-view layout and POV switching; finalize retrospective.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- Python tests currently fail at `tests/python/test_world.py::test_lonely_agent_switches_to_nearby_majority` (group_id stays at 0 after three steps). This predates the viewer change; simulation logic needs follow-up.
- `npm run test:js` fails on Windows because `node --test tests/js` cannot resolve the directory. Running `node --test .\\tests\\js\\*.js` succeeds (4 tests pass).
## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: Use a single Three.js renderer with scissor viewports to paint three cameras.
  Rationale: Avoids creating multiple WebGL contexts and keeps the existing InstancedMesh/shared buffers intact for performance.
  Date/Author: 2025-12-12 / Codex
- Decision: OrbitControls are kept only on the angled camera; top-down and POV cameras remain fixed.
  Rationale: Matches requested fixed overhead/POV views while still allowing one interactive angle without affecting simulation data.
  Date/Author: 2025-12-12 / Codex

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

- Achieved three-way rendering (top-down orthographic, angled OrbitControls view, agent POV) using one renderer and shared InstancedMesh; manual devtools check shows expected splits and labels.
- POV camera now auto-rotates with agent heading and reassigns on death; UI exposes tracked agent id.
- Gaps: `pytest tests/python` currently fails on an existing group-switch test; needs separate fix in Simulation. `npm run test:js` script path fails on Windows though direct `node --test .\\tests\\js\\*.js` passes.

## Context and Orientation

Viewer assets live in `src/terrarium/static/index.html`, `styles.css`, and `app.js`. WebSocket `/ws` streams simulation snapshots; the view interpolates poses into a shared InstancedMesh of cubes (no writes back to Sim). Constraints from AGENTS.md / DESIGN.md: Simulation and View are strictly separated (View is read-only), avoid O(N²) by using SpatialGrid in Sim; long-run stability relies on feedback mechanisms; determinism is required on Sim side. Phase 1 visuals stay on cubes with GPU instancing. Tests live in `tests/python/`.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1) Layout: Update `src/terrarium/static/index.html` and `styles.css` to create a three-panel viewport area (left full-height, right split into two rows). Add labels and tracked-agent indicator near controls. Ensure responsive sizing with CSS variables and proper header height handling.
2) Rendering pipeline: Refactor `src/terrarium/static/app.js` to support multiple cameras rendered via a single WebGLRenderer using scissor viewports. Add Orthographic top-down camera, angled perspective camera, and agent-follow perspective camera. Keep shared scene/InstancedMesh (no per-view duplication).
3) Agent POV selection: Introduce logic to pick a random agent when none is tracked, reuse last heading when stationary, and switch to a new random agent when the tracked one disappears (death). Display tracked agent id/state in UI.
4) Resize & animation loop: Update resize handler and render loop to set per-view viewport/scissor, update projection matrices, and render three views each frame while keeping interpolation and performance.
5) Docs/tests: Add README (or viewer section) note describing the new triple-view layout and controls. Run mandatory `pytest tests/python` to ensure Sim remains unchanged.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- Workdir `C:\LifeOfPikarin`
- After edits: `pytest tests/python` (expect all tests passing).
- Manual check: `uvicorn terrarium.server:app --reload --port 8000` then open `http://localhost:8000` in browser; verify three panes render (top/angle/POV) and POV switches when tracked agent disappears.
- For layout inspection without server data: open `src/terrarium/static/index.html` in browser (WebSocket will reconnect) and confirm pane arrangement via chrome devtools.

## Validation and Acceptance

- Three simultaneous views visible: left top-down (orthographic), upper right angled from field edge, lower right agent POV.
- Agent POV tracks a randomly chosen agent; when that agent is absent in the latest snapshot, POV switches to another existing agent without stalling.
- Metrics overlays (tick/population) still update; tracked agent id displayed.
- Rendering uses shared InstancedMesh; no duplicate per-agent allocations; render loop remains single per-frame pass with three scissor viewports (no O(N²) logic added).
- Performance sanity: with default snapshot rates and ~300–500 agents, render remains smooth (<16ms/frame on modern GPU) since scene updated once and rendered 3x; no additional per-tick allocations beyond existing buffers.
- Long-run stability unaffected: simulation logic untouched; viewer remains read-only and seed/determinism preserved (WebSocket only reads snapshots).
- Tests: `pytest tests/python` passes.

## Idempotence and Recovery

Edits are limited to static assets; rerunning the steps is safe. If layout breaks, revert the three files touched and reapply changes following this plan. Renderer uses scissor viewports; disabling scissor test returns to single-view rendering if needed.

## Artifacts and Notes

- Chrome devtools screenshot (see chat attachment) confirms three-pane layout with labels and POV camera switching at tick ~9134.

## Interfaces and Dependencies

Three.js ESM from unpkg remains the only frontend dependency. WebSocket `/ws` and REST `/api/control/*` contracts remain unchanged. Shared InstancedMesh and agent snapshot schema stay the same; only new UI elements are added around them.
