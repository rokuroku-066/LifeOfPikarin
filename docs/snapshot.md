# WebSocket snapshot schema (Phase 1 compatibility + Phase 2 signals)

The cube viewer in `src/terrarium/static/app.js` reads the snapshot payload emitted by the simulation WebSocket. The schema below keeps the existing Phase 1 contract stable while adding forward-compatible signals for richer animation in Phase 2.

## Top-level fields

- `tick` — simulation tick index (integer).
- `metrics` — object containing per-tick metrics. `population` is always filled and reflects the number of living agents.
- `agents` — full enumeration of all living agents for the tick (no diffing or partial batches).
- `world` — static world metadata. Currently contains `size` (float; world extent in the shared [0, size] coordinate system).
- `metadata` — simulation metadata useful for replay and interpolation:
  - `world_size` — same as `world.size` for convenience/back-compat.
  - `sim_dt` — fixed simulation timestep in seconds.
  - `tick_rate` — ticks per second (1 / sim_dt when sim_dt > 0).
  - `seed` — deterministic seed used for the run.
  - `config_version` — version tag for the simulation config.

## Agent payload

Required Phase 1 fields (always populated):

- `id` — stable unique ID; never reused while the sim runs.
- `x`, `y` — position in the shared [0, world_size] coordinate system.
- `vx`, `vy` — velocity per tick in the same units as `x`/`y` (per simulation step displacement).
- `group` — group identifier (-1 for ungrouped).

Additive Phase 2 signals (ignored by the current viewer but available for richer animation):

- `behavior_state` — current agent state (e.g., Wander, SeekingFood, SeekingMate, Flee).
- `phase` — coarse animation phase; currently `loop` while alive and `end` when not.
- `age`, `energy` — physical state values.
- `size` — normalized 0–1 size proxy derived from age and energy.
- `is_alive` — explicit liveness flag.
- `speed` — magnitude of the velocity vector.
- `heading` — persistent facing direction maintained even when `vx`/`vy` ≈ 0 to avoid jitter.
- `species_id` — current species index (single-species sim emits `0`).
- `appearance_seed` — stable seed to derive appearance (defaults to the agent id).
- `importance` — placeholder LOD weight for future load shedding.

## Units and consistency

- Positions use a shared world coordinate system `[0, world_size]` on both axes; velocities are expressed as displacement per simulation tick in the same units.
- `sim_dt` is the fixed delta-time used for integration; `tick_rate` shows how many ticks occur per second.
- Headings are radians derived from velocity and preserved when agents stop moving so the viewer can interpolate without atan2 jitter.
