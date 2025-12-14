# Group cohesion hysteresis and switching

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Add local-density-based group cohesion and hysteresis so agents retain group membership when near allies, gradually detach when isolated, and can switch to nearby majority groups. Also add cohesion steering to keep groups clustered. This supports visually legible colonies that can split or merge without flapping membership.

## Progress

- [x] (2025-02-17 00:00Z) Drafted ExecPlan for cohesion and hysteresis changes.
- [x] (2025-02-17 00:20Z) Add configuration parameters for cohesion radius, detach thresholds, switch chance, and weights.
- [x] (2025-02-17 00:20Z) Extend Agent state with loneliness accumulator.
- [x] (2025-02-17 00:35Z) Implement isolated detection, hysteresis, and switching in world group membership update.
- [x] (2025-02-17 00:40Z) Add cohesion steering in desired velocity computation.
- [x] (2025-02-17 00:45Z) Update docs with new rules and parameters.
- [x] (2025-02-17 00:50Z) Add deterministic tests for isolation, reset, and switching; run pytest tests/python.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Use existing neighbor collection to compute close same-group count and majority group for switching.
  Rationale: Keeps locality O(1) per neighbor cell and aligns with current group membership helpers.
  Date/Author: 2025-02-17 Codex

## Outcomes & Retrospective

- Lonely agents now only switch when nearby majority meets `group_adoption_neighbor_threshold`; otherwise they either seed a new group via `group_detach_new_group_chance` or briefly ungroup. Added deterministic coverage in `tests/python/test_world.py::test_lonely_agent_does_not_switch_without_threshold_neighbors` and `..._switches_when_neighbor_threshold_met`; pytest (25 tests) now passes.
- Long-run headless 20k-tick smoke (seed 42) kept population stable (final 499, births 7041/deaths 6782) with persistent colonies (groups avg last 10k = 66.17, final 46), indicating the hysteresis prevents both collapse and runaway growth while staying within SpatialGrid locality.

## Context and Orientation

Relevant files:
- `src/terrarium/config.py`: defines FeedbackConfig parameters consumed in world and agents.
- `src/terrarium/agent.py`: holds agent state such as group id and per-step accumulators.
- `src/terrarium/world.py`: simulation loop, neighbor queries, group membership updates, and velocity computation.
- `docs/DESIGN.md`: documents behavior and parameters.
- `tests/python`: pytest suite validating deterministic behaviors.

Constraints to respect (per AGENTS.md):
- Sim/View separation: simulation decisions must not depend on rendering timing.
- No O(N²): only inspect neighbors in spatial grid adjacent cells.
- Long-run stability: avoid runaway growth or collapse; use negative feedback.
- Determinism: rely on seedable RNG and fixed timesteps.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.
1) Add new cohesion/detach parameters to `FeedbackConfig` in `src/terrarium/config.py` with conservative defaults aligning with current behavior. Document fields in dataclass docstring if present.
2) Add `group_lonely_seconds` float field to `Agent` in `src/terrarium/agent.py`, defaulting to 0.0 and included in serialization if applicable. Ensure deterministic numeric state only.
3) In `src/terrarium/world.py`:
   - Use neighbor offsets to count close same-group neighbors (distance squared within `group_cohesion_radius`^2) during `_collect_neighbor_data` or immediately afterward.
   - In `_update_group_membership`, implement hysteresis: increment `group_lonely_seconds` by dt when close same-group neighbor count below `group_detach_close_neighbor_threshold`; reset to 0 when enough allies nearby. When accumulator exceeds `group_detach_after_seconds`, mark agent as detaching.
   - When detaching, attempt switch to nearby majority group with `group_switch_chance`, otherwise ungroup. Reuse majority computation or add `_try_switch_group` helper for clarity.
   - Apply logic for both grouped and ungrouped agents where appropriate, ensuring determinism.
4) In `_compute_desired_velocity`, when agent is grouped, compute cohesion vector toward average position of close same-group neighbors weighted by `group_cohesion_weight`. Combine with existing separation/pheromone/food/danger without O(N²).
5) Update `docs/DESIGN.md` to describe new group retention/detach rules, hysteresis reasons, parameters, and alignment with multi-colony behavior.
6) Add pytest covering:
   - Agent isolated for enough time detaches to ungrouped or switches to majority group under deterministic seed.
   - Nearby same-group restores accumulator to 0 preventing detach.
   Use fixed RNG seed and small neighbor arrangements.
7) Run `pytest tests/python` from repo root. Capture outputs.

## Concrete Steps

Commands to run (from repo root):
- `python --version` to confirm environment.
- `pytest tests/python` after implementing changes.

## Validation and Acceptance

Acceptance criteria:
- Sim uses only neighbor cells for group decisions; no global scans (no O(N²)).
- Agents with few close same-group neighbors accumulate loneliness and detach after configured seconds; nearby allies reset accumulator.
- Detaching agent switches to nearby majority group based on probability or becomes ungrouped.
- Cohesion steering pulls grouped agents toward nearby allies without breaking separation or determinism.
- Tests pass: `pytest tests/python` succeeds with deterministic seeds.
- Documentation describes rules and tunable parameters.

## Idempotence and Recovery

- Config additions and Agent field are additive; rerunning steps is safe.
- If new logic misbehaves, toggling parameters (e.g., weights to zero) should revert behavior to baseline.
- Git provides rollback for code/doc changes.

## Artifacts and Notes

- Record pytest output and any headless run observations in commit/PR description if necessary.

## Interfaces and Dependencies

- `FeedbackConfig` exposes new floats/ints for cohesion/detach thresholds and weights.
- `Agent` exposes `group_lonely_seconds` numeric state; serialization remains compatible.
- `World` functions `_update_group_membership` and `_compute_desired_velocity` consume new config fields and neighbor data without increasing complexity beyond neighbor cells.
- Tests rely on deterministic RNG seeded via existing utilities.
