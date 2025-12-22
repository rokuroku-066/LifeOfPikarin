# Reduce unaffiliated individuals via grouping bias and spacing checks

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: maintain this plan per `.agent/PLANS.md` rules.

## Purpose / Big Picture

We need to make unaffiliated individuals join nearby groups more readily and avoid overly dense group clusters so that by tick 5000 the unaffiliated count is less than half of all individuals. The change must update simulation rules (e.g., group attraction/repulsion) and add a test in `tests/python/test_long_run_performance.py` verifying the requirement.

## Progress

- [x] (2024-05-28 00:00Z) Drafted initial ExecPlan with goals and constraints.
- [x] (2024-05-28 00:30Z) Added long-run unaffiliated proportion check to performance test.
- [x] (2024-05-28 00:45Z) Tuned group adoption/separation parameters and added group-seeking bias for ungrouped agents.
- [x] (2024-05-28 01:05Z) Ran pytest suite after code and doc updates.

## Surprises & Discoveries

_None yet._

## Decision Log

- Decision: Use additional group attraction for unaffiliated agents and crowding mitigation between groups to reduce unaffiliated proportion.
  Rationale: Encouraging joining and discouraging tight cluster overlap should lower unaffiliated counts without O(N^2) scans.
  Date/Author: 2024-05-28 / assistant
- Decision: Introduced explicit group-seeking bias with configurable radius/weight and strengthened adoption plus inter-group avoidance defaults.
  Rationale: This directly pulls unaffiliated individuals toward nearby groups while spacing groups to keep adoption effective.
  Date/Author: 2024-05-28 / assistant

## Outcomes & Retrospective

_Pending implementation and testing._

## Context and Orientation

- Simulation core lives in `src/terrarium/world.py` and related modules under `src/terrarium/`.
- Long-run performance tests are under `tests/python/test_long_run_performance.py`.
- Project constraints: strict Sim/View separation, no O(N^2) scans—neighbor queries must use spatial grid, maintain determinism with seedable randomness, ensure long-run stability with negative feedback loops.

Currently unaffiliated individuals may remain isolated when group attraction is insufficient and group clusters may overcrowd, indirectly increasing unaffiliated counts.

## Plan of Work

1. Update `tests/python/test_long_run_performance.py` to assert that by tick 5000 the unaffiliated population is below half of total individuals. Integrate into existing long-run performance test flow.
2. Inspect `src/terrarium/world.py` to adjust joining behavior for unaffiliated agents: increase bias toward nearby groups within neighbor search results and possibly reduce thresholds for joining.
3. Add inter-group spacing pressure to prevent tight clustering that leaves individuals unaffiliated; implement as density-based repulsion using spatial grid neighborhoods only.
4. Tune parameters in configuration (if applicable) to balance attraction vs. crowding without destabilizing population counts. Keep deterministic seed usage.
5. Validate via `pytest tests/python` ensuring new condition holds and performance remains acceptable.

## Concrete Steps

- Edit `tests/python/test_long_run_performance.py` to add the unaffiliated proportion assertion at tick 5000 in the long-run test scenario.
- Modify `src/terrarium/world.py` (and related config/constants) to:
  - Increase unaffiliated agents' probability of joining nearby groups when neighbors are within range.
  - Apply group spacing or crowding penalty to avoid dense group overlap while respecting spatial-grid locality.
- Re-run `pytest tests/python` from repo root to confirm success.

Expected command transcript:
  - `pytest tests/python`

## Validation and Acceptance

Acceptance criteria:
- Running `pytest tests/python` passes, including the new unaffiliated proportion assertion at tick 5000.
- Simulation maintains determinism given fixed seed and timestep configuration.
- Performance remains spatial-grid bound (no O(N^2) scans); neighbor interactions stay within adjacent cells.
- Long-run stability: population does not explode or crash due to new group bias; spacing pressure provides negative feedback against overcrowding.
- Sim/View separation preserved: changes occur in simulation logic only; visualization unaffected.

## Idempotence and Recovery

Edits are standard code changes; git history allows rollback via `git checkout -- <file>`. Rerunning tests is idempotent.

## Artifacts and Notes

- Key files: `tests/python/test_long_run_performance.py`, `src/terrarium/world.py`, and any tuning constants.
- Keep changes deterministic by using existing RNG patterns; avoid new global state.

## Interfaces and Dependencies

- Use existing spatial grid neighbor queries; do not introduce global all-agent scans.
- Ensure any new parameters are configurable and documented alongside tests if necessary.
- Python 3.11+ with dependencies from `requirements.txt` via `pip install -r requirements.txt`.
