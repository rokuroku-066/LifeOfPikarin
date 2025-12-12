# Phase 2 snapshot signals and metadata prework

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Add forward-compatible snapshot signals and metadata for Phase 2 visuals while keeping the existing cube viewer unbroken. The simulation will continue to emit the current schema (id/x/y/vx/vy/group and metrics.population) but will also expose richer agent state, stable headings, and world timing/config metadata so future viewers can animate without changing the simulation loop.

## Progress

- [x] (2024-05-05 00:00Z) Drafted initial plan.
- [x] (2024-05-05 00:25Z) Implemented snapshot/data changes.
- [x] (2024-05-05 00:35Z) Updated docs and tests; ran pytest.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Keep the simulation loop unchanged and only enrich the snapshot payload to preserve determinism and separation of concerns.
  Rationale: View should remain a consumer; adding metadata should not affect physics or timings.
  Date/Author: 2024-05-05 / assistant

## Outcomes & Retrospective

To be filled after implementation.

## Context and Orientation

Current snapshot emission occurs in `src/terrarium/world.py` (`World.snapshot`) and is serialized to WebSocket clients in `src/terrarium/server.py` within `_broadcast_snapshot`. Agents are defined in `src/terrarium/agent.py`; simulation configuration and defaults are in `src/terrarium/config.py`. Tests covering snapshots and dynamics live in `tests/python/test_world.py`.

Constraints to restate per repo rules:
- Simulation and visualization remain separated; snapshots are read-only outputs.
- No O(N²) logic: neighbor interactions already use `SpatialGrid` in `world.py` and must stay that way.
- Long-run stability relies on existing feedback (density stress, mortality, energy); changes must not bypass these loops.
- Determinism: simulation stays seedable with fixed timesteps; added metadata must not introduce nondeterministic behavior.
- Phase 1 visuals are cube instancing; added fields must be additive and ignored safely by the current viewer.

## Plan of Work

1. Extend agent data to maintain a stable heading even when velocities are near zero; initialize heading deterministically and update only when movement is significant.
2. Enrich `World.snapshot` payload with explicit required fields (id/x/y/vx/vy/group) plus additive Phase 2 signals (behavior_state/phase, age/energy/size/is_alive, speed/heading, species/appearance hints). Keep full enumeration of living agents.
3. Add world/timing/config metadata (world_size, sim_dt, tick_rate, seed, config_version) to the snapshot structure and ensure `server.py` forwards it unchanged.
4. Document the stabilized snapshot schema and units; clarify velocity units and coordinate bounds.
5. Add unit tests to guard the new snapshot fields, heading stability at low speed, and ensure population metrics remain consistent; run `pytest tests/python`.

## Concrete Steps

1. Update `src/terrarium/agent.py` to add persistent heading data with sensible defaults.
2. Adjust initialization and stepping logic in `src/terrarium/world.py` to set/update heading, compute derived signals, and build enriched snapshot structures including metadata.
3. Update `src/terrarium/server.py` serialization to include new metadata without breaking existing fields.
4. Document the snapshot schema and units in `docs/`.
5. Add/adjust tests in `tests/python/test_world.py`; run `pytest tests/python` from repo root.

## Validation and Acceptance

- Deterministic smoke run: `pytest tests/python` should pass, confirming snapshot determinism is preserved.
- Snapshot acceptance: A snapshot after one tick should include required Phase 1 fields plus new signals and metadata; headings should remain unchanged when velocity is effectively zero.
- Stability: No changes to simulation loop timings; neighbor handling remains grid-based.
- Visual check guidance: Current viewer should continue rendering cubes using id/x/y/vx/vy/group with no schema break.

## Idempotence and Recovery

Edits are confined to Python modules and docs; changes can be reapplied by re-running the steps. If a change causes regressions, revert the modified files via git and re-run `pytest tests/python`.

## Artifacts and Notes

- None yet.

## Interfaces and Dependencies

- Snapshot JSON from `server.py` will include new `metadata`/`world` fields alongside existing `tick`, `metrics`, and `agents`. Agents carry heading/behavior fields but must always include id/x/y/vx/vy/group.
- No new external dependencies are introduced; existing `pygame.Vector2` math and dataclasses remain in use.
