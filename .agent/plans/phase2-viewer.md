# Phase 2 viewer refresh with fixed camera and externalized assets

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.
This plan follows `.agent/PLANS.md` and must be maintained accordingly.

## Purpose / Big Picture

Replace the Phase 1 multi-view cube renderer with the Phase 2 single fixed oblique camera viewer that renders instanced Pikarin body/face meshes, a floor, and two walls. Asset loading should be ready for real GLB and textures without bundling placeholders in the repo, while keeping the fallback geometry path so the viewer can still render if assets are missing.

## Progress

- [x] (2025-09-23 20:12Z) Capture current viewer structure and Phase 2 requirements from docs.
- [x] (2025-09-23 20:34Z) Update viewer JS/HTML/CSS for single camera, GLB instancing, and background planes.
- [x] (2025-09-23 20:37Z) Add dummy assets for GLB and textures, plus fallback path handling.
- [x] (2025-09-23 20:40Z) Update docs for viewer refresh and run required Python tests.
- [x] (2025-09-23 20:46Z) Validate with required test commands and summarize manual verification steps.
- [x] (2025-09-24 09:05Z) Remove bundled dummy assets while keeping the fallback geometry path and update documentation.
- [x] (2025-09-24 09:42Z) Add a standalone dummy asset generator script and update README usage.
- [x] (2025-09-24 10:12Z) Bake GLB mesh transforms into instanced geometry to preserve offsets.

## Surprises & Discoveries

The minimal GLB placeholder contains no meshes, so the viewer needs a fallback geometry path to keep rendering.

## Decision Log

- Decision: Use a GLB load-with-fallback path so dummy assets can be swapped for real assets without code changes.
  Rationale: Keeps Phase 2 interface stable and allows dummy assets to be minimal.
  Date/Author: 2025-09-23 / Codex
- Decision: Remove bundled placeholder assets while keeping the fallback geometry path.
  Rationale: Assets will be supplied externally, but the viewer should still render safely if they are missing.
  Date/Author: 2025-09-24 / Codex
- Decision: Provide a script to generate placeholder GLB/textures on demand.
  Rationale: Enables local validation without committing placeholder binaries.
  Date/Author: 2025-09-24 / Codex
- Decision: Apply mesh world transforms to cloned geometries before instancing.
  Rationale: Preserves authored offsets between body and face meshes in GLB files.
  Date/Author: 2025-09-24 / Codex

## Outcomes & Retrospective

Viewer now uses a single fixed oblique camera, textured floor and walls, and instanced body/face meshes with a fallback geometry path. GLB mesh transforms are baked into instanced geometries to preserve authored offsets. The repo no longer bundles dummy assets; real assets should be supplied under `src/terrarium/app/static/assets/` when available. A standalone script can generate placeholder assets for local testing without committing them.

## Context and Orientation

The viewer lives under `src/terrarium/app/static/`. The current `app.js` renders a three-panel view (top/angle/POV) with OrbitControls and instanced cube geometry. `index.html` includes overlay labels for three views, and `styles.css` defines the split-layout styles. The Phase 2 spec in `docs/DESIGN_PHASE2.md` describes a single fixed camera, a floor plus two textured walls, and instanced Pikarin body/face meshes loaded from `static/assets/pikarin.glb`.

Key constraints that must be preserved:

The simulation and viewer must remain strictly separated, meaning the viewer only interpolates snapshots and never drives simulation state. Avoid O(N^2) logic by keeping per-agent operations linear and only per-agent updates in the render loop. Long-run stability and determinism are simulation concerns, so viewer changes must not modify sim behavior. The viewer must remain deterministic about its data flow and use fixed snapshot interpolation. Performance must stay high through instancing and avoiding per-frame allocations.

## Plan of Work

Update the viewer to match Phase 2 by removing multi-camera layout, OrbitControls, and grid helpers from `src/terrarium/app/static/app.js`, replacing them with a single PerspectiveCamera configured per the spec. Add GLTFLoader usage to load `static/assets/pikarin.glb`, build instanced meshes for body and face (baking mesh transforms into geometry), and update transforms/colors per agent. Add background floor and wall planes with texture loading. Provide a fallback dummy geometry if the GLB fails to load or is missing. Update `index.html` to remove multi-view labels and POV tracking. Simplify `styles.css` to remove split view styling. Remove bundled assets from `src/terrarium/app/static/assets/`, add a script to generate placeholders on demand, and update docs to indicate real assets must be provided.

## Concrete Steps

Run commands from repository root.

1) Edit viewer files and add assets.
2) Run `pytest tests/python`.
3) Note any manual verification steps for the viewer and document them.

Expected command transcripts:

    pytest tests/python
    ========================= test session starts =========================
    ...
    ========================= XX passed in Ys =========================

## Validation and Acceptance

A deterministic smoke run will use the existing simulation unit tests, ensuring stable metrics in `pytest tests/python`. A visual sanity check will be manual: run `python scripts/generate_dummy_assets.py --output-dir src/terrarium/app/static/assets` to create placeholders, start the server, and verify the single oblique camera shows the floor and two walls; instanced Pikarin meshes move smoothly; body colors change while face stays fixed. If assets are missing, confirm the fallback geometry path renders without crashing and keeps instancing active. Performance sanity check: observe that 200+ agents render smoothly and there is no per-frame allocation churn (instanced meshes and preallocated buffers are used). No O(N^2) interactions are introduced because the viewer only loops through agent list once per frame. Sim/View separation stays one-way because snapshots only inform transforms.

## Idempotence and Recovery

All edits are repeatable. If GLB loading fails, the fallback geometry will render, so re-running the viewer remains safe. If asset files need to be replaced later, overwrite files under `static/assets/` without code changes.

## Artifacts and Notes

Captured a viewer screenshot via Playwright at `artifacts/phase2-viewer.png`. Python tests passed via `pytest tests/python`. Placeholder assets were removed; use real art assets under `src/terrarium/app/static/assets/` or generate placeholders via `scripts/generate_dummy_assets.py` for visual verification.

## Interfaces and Dependencies

The viewer depends on Three.js and GLTFLoader via CDN imports, and uses `src/terrarium/app/static/app.js`, `index.html`, and `styles.css`. Real assets must live under `src/terrarium/app/static/assets/` and include `pikarin.glb`, `ground.png`, `wall_back.png`, and `wall_side.png` so the viewer’s resource URLs stay stable. Use `scripts/generate_dummy_assets.py` to create placeholder assets locally if needed.
