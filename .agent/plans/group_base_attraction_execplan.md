# Group base attraction + no-overlap separation (anchor at group birth point)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Make same-group agents cluster more reliably by giving each group a fixed “base” (a single anchor point) defined at the moment the group is created. Agents of that group experience a gentle attraction toward their base so colonies form and persist.

Additionally, reduce visual/physical overlap by strengthening very-close-range repulsion so agents do not sit on top of each other, without introducing O(N²) logic or breaking determinism.

## Progress

- [x] (2025-12-14 00:00Z) Identify current group creation paths and steering forces in `src/terrarium/world.py`.
- [ ] (2025-12-14 00:00Z) Add config knobs for base attraction and minimum separation in `src/terrarium/config.py`.
- [ ] (2025-12-14 00:00Z) Implement group base storage + pruning in `src/terrarium/world.py`.
- [ ] (2025-12-14 00:00Z) Add base attraction term to steering in `src/terrarium/world.py`.
- [ ] (2025-12-14 00:00Z) Strengthen close-range repulsion (no-overlap) in `src/terrarium/world.py` without extra neighbor passes.
- [ ] (2025-12-14 00:00Z) Update tests in `tests/python/test_world.py` to cover base anchoring + attraction + determinism.
- [ ] (2025-12-14 00:00Z) Update `docs/DESIGN.md` to describe the new “group base” mechanic and separation tweak.
- [ ] (2025-12-14 00:00Z) Run `python -m pytest tests\\python` and a deterministic headless smoke run.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Store bases as `group_id -> Vector2` inside `World`, not as an environment field.
  Rationale: Base must be a single point per group (not diffusing), deterministic, and does not require spatial lookup; keeps per-tick work O(N) and avoids expanding grid field state.
  Date/Author: 2025-12-14 / Codex

- Decision: Enforce “no-overlap” via additional close-range repulsion inside the existing neighbor loop.
  Rationale: Avoids adding extra neighbor passes and keeps performance stable.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

Pending.

## Context and Orientation

Key modules:

- `src/terrarium/world.py`:
  - Group creation occurs in `_try_form_group`, `_try_split_group`, detach-to-new-group path in `_update_group_membership`, and via `_mutate_group` during reproduction.
  - Steering is composed in `_compute_desired_velocity`, using local neighbors from `SpatialGrid.collect_neighbors`.
- `src/terrarium/config.py` defines `FeedbackConfig` tuning knobs.
- `tests/python/test_world.py` contains determinism and steering expectation tests.

Non-negotiables (restated):

- Sim/View separation: View reads snapshots only; Sim does not wait on animation.
- No O(N²): neighbor logic uses SpatialGrid-local queries only.
- Long-run stability: keep negative feedback loops (density stress/disease + reproduction suppression).
- Determinism: seedable RNG, fixed timestep schedule, no non-deterministic randomness.

## Plan of Work

1) Add config knobs:

- `FeedbackConfig.group_base_attraction_weight`
- `FeedbackConfig.group_base_soft_radius`
- `FeedbackConfig.group_base_dead_zone`
- `FeedbackConfig.min_separation_distance`
- `FeedbackConfig.min_separation_weight`

Defaults should be conservative (do not destabilize), but non-zero so the new behavior is observable without manual tuning.

2) Implement group base storage:

- Add `self._group_bases: Dict[int, Vector2]` to `World`.
- Add `_register_group_base(group_id, position)` that sets the base once (idempotent).
- Call it at every group creation point (new group id allocation).
- Prune bases to active groups each step to keep memory bounded.

3) Add base attraction to steering:

- In `_compute_desired_velocity`, for grouped agents add a base bias toward `base_pos - agent.position` with:
  - zero inside dead-zone
  - smooth falloff inside soft-radius
  - full weight outside

4) No-overlap separation:

- In `_separation`, keep the existing inverse-distance component but add an extra term for distances < `min_separation_distance` based on penetration depth.
- Ensure this uses the same neighbor iteration (no extra loops).

5) Tests + docs:

- Add tests asserting a newly formed group registers a base at the creator’s position (deterministic).
- Add a steering unit test showing base attraction changes desired velocity direction toward base.
- Update `docs/DESIGN.md` sections about group formation/cohesion to mention fixed bases and the separation enhancement.

## Concrete Steps

From repo root (`C:\\LifeOfPikarin`):

1) Unit tests:

    python -m pytest tests\\python

2) Deterministic smoke:

    python -m terrarium.headless --steps 5000 --seed 42 --log artifacts\\metrics_group_base.csv
    python -m terrarium.headless --steps 5000 --seed 42 --log artifacts\\metrics_group_base_2.csv

Expected: the two CSVs match row-for-row.

## Validation and Acceptance

- Same seed/config produces identical test results and headless metrics.
- Groups form and agents in the same group cluster around their group’s base (tight colonies).
- Agents do not visibly overlap for sustained periods (close-range repulsion dominates).
- Performance remains stable: no new global scans; only existing neighbor loop work increases by O(1) per neighbor.

## Idempotence and Recovery

- Safe to re-run tests and headless simulation.
- Rollback: revert modified files or set `group_base_attraction_weight = 0.0` and/or `min_separation_weight = 0.0`.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

- Python 3.11+
- `pytest` for unit tests
- `pygame` for `Vector2`

