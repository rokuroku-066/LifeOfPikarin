# Dense groups spawn clan-only rations

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated. Follow `.agent/PLANS.md`.

## Purpose / Big Picture

When a tight cluster of the same group forms, they should leave behind food usable only by that group. This reinforces group territories without breaking determinism, avoids O(N²) scans, keeps Sim/View separation, and maintains Phase 1 cube scope. The goal is that clustered allies can seed short-lived, group-locked food that boosts them locally while remaining invisible to other groups.

## Progress

- [x] (2025-12-14 16:25Z) Drafted plan
- [x] (2025-12-14 16:45Z) Implemented config/env/world changes plus doc note and new group-food tests
- [x] (2025-12-14 16:50Z) Ran `pytest tests/python` (pass on Python 3.9.7)
- [x] (2025-12-14 16:53Z) Reviewed results and updated plan

## Surprises & Discoveries

- Python interpreter on host is 3.9.7; repository guidance prefers 3.11+. Tests will run on 3.9.7 unless a newer runtime is installed.

## Decision Log

- Decision: Store group-only food in the EnvironmentGrid keyed by `(cell_x, cell_y, group_id)` with its own decay/diffusion and per-cell cap so it stays local, bounded, and deterministic.
  Rationale: Reuses spatial hashing, avoids O(N²), supports locality and stability, and keeps data in the Sim layer only.
  Date/Author: 2025-12-14 / Codex
- Decision: Trigger group food when an agent has at least `group_food_neighbor_threshold` same-group neighbors within the cohesion radius; spawn with probability `group_food_spawn_chance` and amount `group_food_spawn_amount` capped per cell.
  Rationale: Uses existing neighbor scan and cohesion radius to define “dense cluster” without extra passes; probability prevents runaway growth.
  Date/Author: 2025-12-14 / Codex
- Decision: Agents in a group consume group food first (if present), then public food; other groups cannot consume clan food.
  Rationale: Enforces exclusivity while keeping feeding logic simple and deterministic.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

Dense same-group clusters now seed capped, decaying clan food; grouped agents eat it first and rivals cannot consume it. New tests cover spawning and exclusivity, docs mention the mechanic, and the full Python suite passes (on 3.9.7; 3.11 still recommended).

## Context and Orientation

- Key files: `src/terrarium/world.py` (per-agent loop, life cycle, event queues), `src/terrarium/environment.py` (food/danger/pheromone fields), `src/terrarium/config.py` (Simulation/Environment/Feedback parameters), `tests/python/test_world.py`, `docs/DESIGN.md`.
- Constraints to uphold:
  - Simulation (fixed timestep, deterministic RNG) is separate from View; View never drives Sim.
  - All locality via SpatialGrid; no O(N²) all-pairs scans.
  - Long-run stability requires negative feedback; new food must be bounded/decaying to avoid runaway population.
  - Determinism and seed reproducibility are mandatory.
  - Phase 1 visuals are cubes via instancing; keep Sim logic independent of rendering.

## Plan of Work

1) Extend config to expose knobs: spawn threshold/chance/amount (Feedback) and group-food field parameters (Environment: cap, decay, diffusion).
2) Enhance EnvironmentGrid with a group-food field (per-cell per-group), supporting add/sample/consume, decay/diffusion, and pruning of extinct groups.
3) In World step:
   - Detect dense same-group clusters using existing neighbor data (cohesion radius).
   - Enqueue group-food spawn events using deterministic RNG and configured amounts, capped per cell.
   - In life-cycle feeding, let grouped agents consume clan food first; others ignore it.
4) Keep pending event application deterministic alongside existing food/danger/pheromone queues.
5) Tests: add scenarios proving (a) dense allies create group-only food, (b) same-group agents can eat it, (c) other groups cannot, and (d) caps/decay prevent unbounded accumulation.
6) Docs: summarize the mechanic and tuning knobs in `docs/DESIGN.md`.
7) Validation: run `pytest tests/python`; note interpreter version caveat.

## Concrete Steps

- Edit `src/terrarium/config.py`: add Feedback + Environment fields for group-only food.
- Edit `src/terrarium/environment.py`: implement group-food storage, add/sample/consume, decay/diffusion, and pruning.
- Edit `src/terrarium/world.py`: spawn group food on dense clusters, queue/apply events, and consume clan food preferentially.
- Edit `tests/python/test_world.py`: add coverage for spawning/consumption/exclusivity; adjust fixtures if needed.
- Edit `docs/DESIGN.md`: document the new mechanic and parameters.
- Commands (repo root):
  - `python --version` (done; 3.9.7)
  - After edits: `pytest tests/python`

## Validation and Acceptance

- Behavior: With no public food, a clustered group spawns clan-only food that only that group’s agents can consume; rivals in the same cell do not gain energy.
- Determinism: Re-running with the same seed yields identical spawn/consumption outcomes.
- Performance: No new O(N²); group-food uses spatial hash and single-pass per-agent checks; per-tick allocations stay minimal.
- Long-run stability: Group-food decays/diffuses and is capped per cell to prevent runaway energy growth.

## Idempotence and Recovery

- Group-food field rebuilds deterministically each tick with decay/diffusion; rerunning steps is safe.
- If food becomes too plentiful, reduce `group_food_spawn_amount` or increase decay; if too scarce, raise spawn chance/amount or lower threshold.

## Artifacts and Notes

- New config knobs for group-only food (spawn + field properties).
- Environment field keyed by `(cell_x, cell_y, group_id)` with cap/decay/diffusion.

## Interfaces and Dependencies

- `EnvironmentGrid` exposes `add_group_food`, `sample_group_food`, `consume_group_food`, and prunes extinct group entries.
- `World` adds pending group-food queue and cluster trigger logic using existing neighbor scans.
- Config fields: `FeedbackConfig.group_food_neighbor_threshold`, `group_food_spawn_chance`, `group_food_spawn_amount`; `EnvironmentConfig.group_food_max_per_cell`, `group_food_decay_rate`, `group_food_diffusion_rate`.
