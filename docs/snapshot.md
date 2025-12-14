# WebSocket snapshot schema (Phase 1 compatibility + Phase 2 signals)

The cube viewer in `src/terrarium/static/app.js` reads the snapshot payload emitted by the simulation WebSocket. The schema below keeps the existing Phase 1 contract stable while adding forward-compatible signals for richer animation in Phase 2.

## Top-level fields

- `tick`: controller tick counter (integer).
- `metrics`: per-tick metrics object (see below). `population` reflects the number of living agents.
- `agents`: full enumeration of all living agents (no diffing or partial batches).
- `world`: static world metadata. Currently contains `size` (float; world extent in the shared `[0, size]` coordinate system).
- `metadata`: simulation metadata useful for replay and interpolation:
  - `world_size`: same as `world.size` for convenience/back-compat.
  - `sim_dt`: fixed simulation timestep in seconds.
  - `tick_rate`: ticks per second (`1 / sim_dt` when `sim_dt > 0`).
  - `seed`: deterministic seed used for the run.
  - `config_version`: version tag for the simulation config.

## Metrics payload

Fields currently emitted from `terrarium.world.TickMetrics`:

- `tick`: tick index the metrics were computed for.
- `population`: living agent count.
- `births`, `deaths`: births/deaths during the tick.
- `average_energy`, `average_age`: per-tick averages across living agents.
- `groups`: number of active groups (ungrouped agents are excluded).
- `neighbor_checks`: neighbor checks performed during the tick (sanity metric to catch accidental O(N^2)).
- `tick_duration_ms`: wall-clock duration of the tick processing in milliseconds.

## Agent payload

Fields currently emitted for each living agent:

- `id`: stable unique ID; never reused while the sim runs.
- `x`, `y`: position in the shared `[0, world_size]` coordinate system.
- `vx`, `vy`: velocity in world units per second (integration uses `sim_dt`).
- `group`: group identifier (`-1` for ungrouped).
- `behavior_state`: current agent state (one of `Idle`, `SeekingFood`, `SeekingMate`, `Flee`, `Wander`).
- `heading`: facing direction in radians; derived from velocity and preserved when speed is ~0 to avoid jitter.
- `age`, `energy`: physical state values.
- `size`: normalized `0..1` proxy derived from age and energy.
- `speed`: magnitude of the velocity vector (world units per second).
- `is_alive`: explicit liveness flag (currently always `true` because `agents` enumerates living agents only).
- `phase`: coarse animation phase (currently always `loop`; kept for Phase 2 compatibility).
- `species_id`: current species index (single-species sim emits `0`).
- `appearance_seed`: stable seed to derive appearance (currently defaults to the agent id).
- `importance`: placeholder LOD weight for future load shedding (currently `1.0`).

## Units and consistency

- Positions use a shared world coordinate system `[0, world_size]` on both axes; velocities are expressed as world units per second (so integration is `pos += vel * sim_dt`).
- `sim_dt` is the fixed delta-time used for integration; `tick_rate` shows how many ticks occur per second.
- Headings are radians derived from velocity and preserved when agents stop moving so the viewer can interpolate without atan2 jitter.
