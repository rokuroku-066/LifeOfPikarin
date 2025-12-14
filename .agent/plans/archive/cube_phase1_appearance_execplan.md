# Cube appearance cues for Phase 1 viewer (energy/age/repro signals)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Show meaningful per-agent cues in the Phase 1 cube renderer so viewers can immediately read colony structure and life cycle state: group hues, energy brightness, size by age, and a subtle reproduction pulse. Implementation must keep Sim and View separated and maintain deterministic snapshots.

## Progress

- [x] (2025-12-13 11:00Z) Draft plan, review AGENTS.md and DESIGN.md §5-1, scan current viewer code and snapshot fields.
- [x] (2025-12-13 11:28Z) Add pure appearance mapping helpers (hue->color, energy->lightness, age->scale, reproduction desire->pulse) with JS tests.
- [x] (2025-12-13 11:48Z) Apply helpers in `src/terrarium/static/app.js` for instanced transforms/colors using agent heading/position/size.
- [x] (2025-12-13 12:05Z) Run tests (`pytest tests/python`, JS node tests) and document manual visual check recipe; finalize plan sections.
- [x] (2025-12-13 12:18Z) Manual viewer check in browser (uvicorn + devtools): brightness by energy, elder shrink/jitter, and reproduction pulse now visually distinct.

## Surprises & Discoveries

- Initial `pytest tests/python` using system Python 3.9 failed because pygame was missing; rerunning with the repo `.venv` (Python 3.13) succeeded after confirming dependencies were already installed.

## Decision Log

- Decision: Keep rendering via existing InstancedMesh; layer cues through per-instance transform/color only.  
  Rationale: Honors Phase 1 GPU instancing goal and avoids changing rendering strategy.  
  Date/Author: 2025-12-13 / Codex
- Decision: Derive lightness curve from live average energy metrics instead of hard-coding thresholds.  
  Rationale: Keeps brightness meaningful if simulation energy parameters change while avoiding extra server fields.  
  Date/Author: 2025-12-13 / Codex

## Outcomes & Retrospective

- Implemented Phase 1 cube cues (energy-driven lightness, age scaling with elder jitter, reproduction pulse) in the web viewer; JS helper tests and Python sim tests now pass under `.venv` (Python 3.13).

## Context and Orientation

- Simulation delivers snapshots via FastAPI/WebSocket (`src/terrarium/server.py`). Snapshot fields already include position (`x`, `y`), heading, energy, age, group id, and a precomputed `size`.
- The web viewer lives in `src/terrarium/static/app.js` using Three.js InstancedMesh with `computeGroupHue` from `src/terrarium/static/color.js`.
- Phase 1 view rules (DESIGN.md §5-1): position/heading direct, hue per group, brightness from energy, scale by life stage (child small, adult standard, old shrink/jitter), and a faint pulse when reproduction desire is high.
- Non-negotiables: Sim/View one-way data flow; no O(N²) (rendering stays O(N)); deterministic seeds preserved (no view-side randomness affecting sim); Phase 1 cubes + instancing only.

## Plan of Work

1) Add reusable appearance mapping helpers (in `src/terrarium/static/color.js`) that take numeric snapshot fields and return normalized view values: lightness (energy), elder scale factor, reproduction desire, and a pulse envelope. Keep them pure for testing.  
2) Extend JS tests under `tests/js` to cover new helpers (energy->lightness clamping, age stage scaling, pulse envelope).  
3) Update `app.js` rendering loop to:  
   - use `agent.heading` instead of recomputing yaw from velocity;  
   - apply per-instance scale from helper (respecting snapshot `size` and age jitter for elders);  
   - compute HSL color using group hue + energy-derived lightness + optional reproduction pulse; write into instanced color buffer;  
   - add a mild breathing/pulse multiplier when reproduction desire is high (energy & adult age or SeekingMate state), without feeding back into sim.  
4) Keep renderer performance: reuse buffer attributes, avoid allocations in the per-frame loop.  
5) Validation: run required Python tests; run JS tests; note manual browser steps (open viewer, observe brightness/size/pulse differences by energy/age/state over a short run).

## Concrete Steps

- Edit helper module and tests.  
- Edit `src/terrarium/static/app.js` to integrate helpers.  
- Run `pytest tests/python` from repo root.  
- Run `node --test tests/js/*.js` (Windows path compatible).

## Validation and Acceptance

- Automated: `pytest tests/python` passes; JS tests cover appearance mapping edge cases.  
- Manual (if browser available): start server `uvicorn src.terrarium.server:app`, open `http://localhost:8000`, observe cubes: low-energy agents appear darker; young agents visibly smaller; older agents slightly shrunken with mild jitter; agents in SeekingMate/high-energy show a faint rhythmic brightening.  
- Performance: Instanced rendering remains; no additional per-agent allocations each frame.  
- Determinism: view uses only snapshot data and time-based interpolation; no changes to simulation outputs.

## Idempotence and Recovery

- Pure helper functions and app.js changes are reversible; rerunning tests after edits confirms state.  
- If viewer artifacts appear, revert helper usage in `app.js` while keeping tests to isolate regression.

## Artifacts and Notes

- To be updated with key diffs or log snippets after implementation.

## Interfaces and Dependencies

- `src/terrarium/static/color.js` exports appearance helpers used by `app.js`.  
- Snapshots supply fields: `x`, `y`, `heading`, `group`, `energy`, `age`, `size`, `behavior_state`.  
- Three.js InstancedMesh remains the render vehicle; no shader changes expected.
