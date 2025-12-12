# Perspective camera, lighting, and interpolation update

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

Repo guidance: follow `.agent/PLANS.md` for formatting and repository-specific constraints.

## Purpose / Big Picture

Shift the terrarium viewer from an orthographic overhead projection to a perspective camera with lighting and ground plane so cubes look three-dimensional, add interpolation for smoother motion between server updates, and expose agent orientation via velocities. Users should see a diagonal camera view with lit cubes casting shadows and moving smoothly without simulation timing changes.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2024-06-14 00:00Z) Drafted ExecPlan with objectives and constraints.
- [x] (2024-06-14 00:30Z) Implement client perspective camera, lighting, shadow, and ground updates.
- [x] (2024-06-14 00:30Z) Add interpolation buffer and orientation handling in client rendering loop.
- [x] (2024-06-14 00:30Z) Extend server/world payload to include velocity, adjust broadcast cadence.
- [x] (2024-06-14 00:45Z) Run validation (pytest) and describe manual visual check expectations.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- Installing dependencies pulled in pygame during pytest run.

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: Use snapshot interpolation with prev/next buffers and alpha clamp based on last receipt time.
  Rationale: Keeps simulation authoritative while rendering smooth motion without altering tick timing.
  Date/Author: 2024-06-14 / Codex.
- Decision: Maintain instanced mesh with max count to avoid frequent allocations.
  Rationale: Reduces per-update churn and preserves GPU instancing efficiency.
  Date/Author: 2024-06-14 / Codex.

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

- Pending implementation.

## Context and Orientation

Current viewer uses an `OrthographicCamera` in `src/terrarium/static/app.js` with rotation-disabled orbit controls and a rotated grid to appear as floor. Agents are rendered as `InstancedMesh` cubes with `MeshBasicMaterial` and positions updated directly from latest websocket message. Simulation snapshots from `src/terrarium/world.py` include positions but not velocity; `src/terrarium/server.py` broadcasts state every two ticks. Root AGENTS.md enforces Sim/View separation, determinism, avoidance of O(N²), long-run stability, and mandatory pytest `tests/python` execution after changes.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1. Update `src/terrarium/static/app.js` `initThree()` to create a `PerspectiveCamera` positioned diagonally, enable orbit rotation with constrained polar angles, add ambient and directional lights with shadows, enable renderer shadow map, add ground plane receiving shadows, stop rotating the grid, and adjust resize handling to update camera aspect and projection.
2. Modify websocket connection URL to choose ws/wss based on current protocol for HTTPS compatibility.
3. Rework instanced agent creation in `ensureInstancedAgents()` to use `MeshStandardMaterial`, preallocate to a maximum count, enable shadows on instances, and avoid re-creating meshes unless size increases.
4. Introduce snapshot interpolation on the client: store previous and latest snapshots from websocket messages instead of immediate updates; in `animate()`, compute alpha based on last received interval, interpolate positions and orientations (using velocity to compute yaw), and update instanced mesh matrices accordingly while keeping simulation logic untouched.
5. Change `updateView()` usage to map snapshot coordinates to (x,0,z) without grid rotation.
6. On the server side, reduce `SimulationController.broadcast_interval` in `src/terrarium/server.py` to 1 to provide more frequent snapshots, and extend `src/terrarium/world.py` snapshot payload to include `vx`/`vy` from agent velocity vectors.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- From repo root, edit files per Plan of Work.
- After code changes, run Python tests: `pytest tests/python` (expected to pass).
- For manual visual check (if environment allows), start server per README and open viewer; expect perspective view with shadows and smooth motion.

## Validation and Acceptance

Describe how to start or exercise the system and what to observe. Phrase acceptance as behavior, with specific inputs and outputs.

- Deterministic smoke run: run `pytest tests/python` to confirm simulation consistency (no changes to logic beyond payload/interval) and ensure tests still pass.
- Visual sanity: launch web viewer; camera defaults to angled perspective with orbit rotation allowed within limits; cubes lit with ambient/directional light casting shadows on ground plane; grid lies on XZ plane; agents move smoothly with visible directional orientation aligning with velocity.
- Performance sanity: instanced mesh reused up to maximum count to avoid per-update allocations; expect stable frame updates for typical agent counts (same as prior phase) while computing per-frame interpolation only once per instance.
- No O(N²): client interpolation loops over agent count only; simulation side unchanged aside from payload and broadcast cadence; spatial interactions remain untouched.
- Sim/View separation: server continues to own simulation; client interpolates for visuals only and does not influence simulation updates.

## Idempotence and Recovery

If steps can be repeated safely, say so. If a step is risky, provide a safe retry or rollback path.

- Code edits are standard file modifications; git commits provide rollback. Re-running interpolation logic or mesh allocation is safe because instanced mesh expands only when more capacity is needed.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples.

- Pending after implementation/testing.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, and interfaces/types that must exist at the end. Prefer stable names and repo-relative paths.

- `src/terrarium/static/app.js`: exports/initializes Three.js viewer using `PerspectiveCamera`, `AmbientLight`, `DirectionalLight` with shadows, `MeshStandardMaterial`, interpolation buffers, and orientation-based transforms.
- `src/terrarium/server.py`: `SimulationController.broadcast_interval` set to 1.
- `src/terrarium/world.py`: `snapshot()` returns agents with `vx` and `vy` fields in addition to existing metadata.
