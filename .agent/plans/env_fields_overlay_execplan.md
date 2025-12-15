# Overlay of Environment Fields for Viewer

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Expose sparse representations of food and pheromone fields from the simulation and transmit them to the web viewer so the visual layer can render translucent overlays showing resource and pheromone intensity without affecting simulation timing or rules. The viewer should display heatmaps above the ground plane while simulation timesteps remain deterministic.

## Progress

- [x] (2024-05-21 00:00Z) Drafted initial plan for exporting environment fields and rendering overlays.
- [x] (2024-05-21 00:25Z) Implemented environment export methods and snapshot wiring.
- [x] (2024-05-21 00:55Z) Updated client to render food and pheromone overlays from sparse lists.
- [x] (2024-05-21 01:10Z) Ran tests and captured verification notes.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Represent pheromone export as max concentration per cell with associated group id to limit payload size.
  Rationale: Viewer only needs aggregated intensity for heatmap; reduces bandwidth.
  Date/Author: 2024-05-21 / assistant

## Outcomes & Retrospective

- Pending implementation.

## Context and Orientation

Key files:
- `src/terrarium/environment.py`: EnvironmentGrid stores food cells and pheromone field; add export helpers without mutating state.
- `src/terrarium/world.py`: Snapshot packaging for simulation state; extend to carry environment field data.
- `src/terrarium/server.py`: SimulationController broadcasts snapshots over WebSocket; include new fields payload.
- `src/terrarium/static/app.js`: Client connects to WebSocket and renders Three.js scene; needs overlays and texture updates.

Constraints restated from repository rules:
- Maintain strict Sim/View separation: only export read-only data; no rendering feedback into simulation.
- Avoid O(N²): use existing sparse structures; avoid per-frame all-pairs operations.
- Determinism & fixed timestep: export should not change simulation state or timing.
- Phase 1 visuals: cube-based with overlays; keep GPU instancing untouched.
- Long-run stability: do not alter resource regeneration or pheromone dynamics.

## Plan of Work

Describe, in prose, the sequence of edits and additions.

1. Add EnvironmentGrid export methods for food and pheromones returning sparse lists of coordinates with quantities; aggregate pheromones by cell with max concentration and group id.
2. Extend Snapshot dataclass in `world.py` with fields container for exported environment data; populate in `World.snapshot()` by calling the new EnvironmentGrid methods.
3. Update SimulationController broadcast to include fields in WebSocket JSON payload.
4. Modify client connection handler to store received fields and integrate overlays; set up translucent planes in `initThree()` above ground.
5. In `updateView()`, transform sparse lists into textures for food heatmap and pheromone visualization keyed by group color, update overlays before rendering.
6. Add validation steps (unit tests and manual notes) ensuring payload structure and rendering hooks operate without altering simulation timing.

## Concrete Steps

Commands to run from repository root:
- Install dependencies if needed: `pip install -r requirements.txt`.
- Run simulation tests: `pytest tests/python`.
- If web viewer changes cannot be visually verified here, note manual verification steps (load UI, confirm overlays appear and update).

## Validation and Acceptance

Acceptance criteria:
- Snapshot data includes `fields` with sparse `food` and `pheromones` entries containing coordinates and quantities/group ids.
- WebSocket payload contains fields and client stores them without errors (check console logs).
- Viewer renders two translucent planes above ground showing food heatmap intensity and pheromone intensity tinted by group colors; textures update each frame from sparse data.
- Simulation timestep and determinism unaffected (no mutations or timing dependencies in export).
- Performance sanity: overlays update using sparse data → no per-pixel CPU loops beyond texture updates, suitable for current agent counts; no O(N²) loops introduced.
- Long-run stability unchanged; resource and pheromone logic not modified.
- Sim/View separation preserved: data flows sim → view only.

## Idempotence and Recovery

Edits are deterministic; rerunning build/test commands is safe. If overlay rendering causes issues, revert client-side changes without touching simulation logic. Snapshot export methods are read-only and can be safely re-invoked.

## Artifacts and Notes

- Keep console logs minimal; add comments explaining texture update approach if non-obvious.

## Interfaces and Dependencies

- New EnvironmentGrid methods: `export_food_cells()` returning list of `{x, y, amount}` or tuple; `export_pheromone_field()` returning list of `{x, y, value, group}` aggregated per cell.
- Snapshot fields attribute: dictionary with keys `food`, `pheromones` or similar; included in server broadcast JSON.
- Client maintains textures for food and pheromone overlays, updating them in `updateView()` before `renderViews()`.
