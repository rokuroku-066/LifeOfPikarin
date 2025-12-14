# Boundary Avoidance Steering To Reduce Edge Clustering

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. This plan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Agents currently stack along world edges because only hard reflection keeps them in bounds; there is no inward steering bias, and edge cells enjoy lower perceived density. The goal is to add a soft boundary avoidance force in the Simulation Core so agents gently steer back toward the interior before hitting walls, while preserving determinism and existing reflection. A user should see fewer long-lived clumps on the border during long runs with cube rendering.

## Progress

- [x] (2025-12-13 01:02Z) Inspect current boundary handling and identify where a soft avoidance term should live.
- [x] (2025-12-13 01:22Z) Implement configurable boundary avoidance steering (config defaults, World steering update).
- [x] (2025-12-13 01:53Z) Add tests and docs, run `pytest tests/python` and a short headless smoke run.
- [x] (2025-12-13 02:15Z) Add facing bias near walls (`boundary_turn_weight`) to orient agents away from edges and update tests/docs.
- [x] (2025-12-13 03:05Z) Retune grouping vs boundary bias; lowered wander jitter, strengthened group formation/adoption, softened boundary strength to recover clustering; re-ran tests.

## Surprises & Discoveries

- Group adoption randomness interfered with the “lonely agent switches majority” test; set `group_adoption_chance=0` in the test to keep neighbors stable for determinism.
- Boundary avoidance test initially spawned a child because low reproduction threshold; capped `max_population` and zeroed food to isolate boundary steering only.
- Simple push still allowed edge camping orientation; added turn-weight blend so heading prefers interior when within margin.
- Environment food grid blew up because gradient sampling created out-of-bounds cells; clamped grid indices and added sanitization to keep keys within world bounds, which also restored fast test runtimes.
- Heavy boundary/center bias reduced grouping; rebalanced parameters (group formation/adoption up, wander jitter down, boundary weights moderated) to encourage flocks while keeping edge repulsion.

## Decision Log

- Decision: Add soft boundary avoidance driven by `boundary_margin` and `boundary_avoidance_weight` with defaults (8.0, 1.1), keeping reflection as hard bound.
  Rationale: Gentle inward bias reduces edge clumping without changing determinism or neighbor complexity; config weight 0 cleanly disables.
  Date/Author: 2025-12-13 / Codex

## Outcomes & Retrospective

- Soft boundary force added without touching O(N²) paths; defaults nudge agents off walls while keeping reflection.
- Tests and headless smoke run completed; boundary behavior now covered by a deterministic unit test.

## Context and Orientation

- Simulation/View separation: only Simulation Core changes; no viewer writes into sim state.
- No O(N²): boundary steering must be O(1) per agent; neighbor work stays via `SpatialGrid`.
- Stability: keep reflection; add soft avoidance to reduce edge dwell without removing negative feedback loops.
- Determinism: reuse deterministic RNG; new force must be purely deterministic from position.
- Phase 1 cubes: rendering untouched; only pose/state outputs are read by the view.
- Key files: `src/terrarium/world.py` (steering + integration), `src/terrarium/config.py` (simulation parameters), `tests/python/test_world.py` (unit coverage), `docs/DESIGN.md` (design contract), `src/terrarium/headless.py` (smoke run).
- Current state: `_reflect` mirrors positions/velocities after movement; `_compute_desired_velocity` lacks any boundary term, so agents near edges face reduced neighbor density and can park along walls.

## Plan of Work

Describe edits in sequence:
1) Confirm current steering path in `World._compute_desired_velocity` and how `_reflect` enforces bounds; note absence of boundary force.
2) Introduce configurable boundary avoidance parameters (margin and weight) in `SimulationConfig` with sane defaults; ensure YAML loader keeps compatibility.
3) Implement `_boundary_avoidance` helper in `world.py` that yields an inward bias when within the margin, scaling with proximity, and add it to the steering blend without touching SpatialGrid logic.
4) Add unit test(s) ensuring an agent near a wall gains inward velocity even without neighbors, and keep reflection tests intact.
5) Update `docs/DESIGN.md` (boundary force now on by default) and, if needed, README configuration notes.
6) Run validation: `pytest tests/python`; headless smoke (`python -m terrarium.headless --steps 600 --seed 1337 --log artifacts/edge_smoke.csv`) to confirm metrics and absence of crashes; optionally compute edge-near counts in the log reader script.

## Concrete Steps

- From repo root run: `python --version` (ensure 3.11+), `pytest tests/python`.
- After changes, repeat `pytest tests/python`.
- Run a short headless deterministic smoke: `python -m terrarium.headless --steps 600 --seed 1337 --log artifacts/edge_smoke.csv` and sanity-check that population stays bounded and run completes.

## Validation and Acceptance

- Deterministic smoke run succeeds (no crashes) with bounded population and reasonable tick times; CSV produced at `artifacts/edge_smoke.csv`.
- Unit tests include a case showing boundary avoidance produces inward velocity for an edge-adjacent agent with no neighbors; all tests pass.
- Performance sanity: per-tick work remains O(N) (only adds constant-time vector math). No per-tick allocations beyond existing patterns.
- Long-run stability: reflection still active; boundary bias reduces edge clumping without disabling negative feedback (density stress/disease remain).
- Sim/View separation maintained; only Simulation outputs are read by View.
- No O(N²): boundary force uses only agent position and world size.

## Idempotence and Recovery

- Config defaults keep behavior stable; setting boundary weight to zero reverts to previous behavior.
- Changes are confined to Simulation Core; rerunning tests/headless is sufficient to verify a clean state.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

- New config fields in `SimulationConfig` must be exposed with defaults and YAML loader support.
- `World._compute_desired_velocity` consumes new config values for boundary avoidance.
