# Add social/territorial lineage traits for group dynamics

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Introduce additional social and lineage-aware traits to agents so that group formation, cohesion, territorial avoidance, and factional preferences can reflect inherited personality parameters. The result should be visible through biased group joining/splitting, lineage-friendly group choices, and modified avoidance/cohesion behaviors while preserving determinism and performance.

## Progress

- [x] (2025-12-19 03:00Z) Draft ExecPlan for social/territorial traits and faction-aware grouping.
- [x] (2025-12-19 03:22Z) Implement trait data model and config clamps/mutation weights.
- [x] (2025-12-19 03:22Z) Update world logic for adoption, detachment, avoidance, and lineage preference.
- [x] (2025-12-19 03:23Z) Add/adjust tests and validate simulation determinism (pytest tests/python).
- [ ] (YYYY-MM-DD HH:MMZ) Finalize documentation and retrospective.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Represent new social traits as scalar floats defaulting to 1.0 to avoid altering existing balance drastically.
  Rationale: Keeps backward compatibility while enabling future tuning via config clamps and mutation weights.
  Date/Author: 2024-06-01 / Codex
- Decision: Bias adoption/loyalty behaviors multiplicatively by sociality/loyalty and gate new-group formation with founder multipliers (clamped to probability 1.0).
  Rationale: Preserves existing probabilities at default while enabling trait-driven variation without destabilizing the sim.
  Date/Author: 2025-12-19 / Codex
- Decision: Loyalty now suppresses switching out of an existing group (applied as a divisor on adoption chance) while still allowing ungrouped agents to join based on sociality.
  Rationale: Aligns loyalty semantics with expected faction stability so high-loyalty agents resist majority pull unless ungrouped.
  Date/Author: 2025-12-19 / Codex

## Outcomes & Retrospective

Initial outcome: new social/territorial traits flow through clamp/mutation, group behaviors (adoption, detachment, avoidance, cohesion, kin bias) respond to traits, and pytest suite passes. Long-run visual/stability check still pending.

## Context and Orientation

- Core data structures live in `src/terrarium/agent.py` (Agent/AgentTraits), `src/terrarium/config.py` (SimulationConfig and evolution clamps/mutation weights), and `src/terrarium/world.py` (simulation loop, grouping logic, trait mutation/clamping).
- Group dynamics: `_update_group_membership`, `_try_adopt_group`, `_try_split_group`, `_mutate_group`, and movement biases (`_intergroup_avoidance`, `_group_cohesion`, `_alignment`).
- Constraints to restate per repo rules:
  - Sim/View separation: only adjust simulation data and outputs; no rendering-side coupling.
  - No O(N²): rely on existing SpatialGrid neighbor lists; only use already-collected neighbor sets.
  - Long-run stability: ensure new biases do not remove negative feedback (density stress, resource limits).
  - Determinism: use existing deterministic RNG and config-driven weights; no random sources outside DeterministicRng.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location (function, module) and what to insert or change.

1) Extend `AgentTraits` in `src/terrarium/agent.py` with new float fields (sociality, territoriality, loyalty, founder, kin_bias) defaulting to 1.0; ensure dataclass defaults align with existing behavior.
2) Update `src/terrarium/config.py` to include clamp ranges and mutation weights for the new traits. Keep defaults centered at 1.0 with narrow mutation influence to preserve current balance; wire into YAML loading.
3) Adjust trait handling in `src/terrarium/world.py`:
   - `_clamp_traits`, `_copy_traits`, `_mutate_traits` to handle new fields using config clamps/weights.
   - Group behavior hooks:
     - `_try_adopt_group`: scale adoption chance using agent sociality/loyalty.
     - Detach/switch timing: loyalty reduces leave/switch frequency; founder boosts new-group chance in detach/split/birth mutation paths.
     - `_mutate_group` and related group creation paths: apply founder multiplier to creation probabilities.
     - `_intergroup_avoidance`: multiply avoidance weight by territoriality.
     - `_group_cohesion` / `_alignment`: weight cohesion/alignment by sociality.
     - `_update_group_membership`: incorporate kin_bias via lineage-aware scoring when selecting majority/switch targets; compute lineage counts from neighbor data without extra global scans.
4) Keep allocations minimal: reuse existing neighbor lists and group count scratch maps; no new per-tick dynamic structures beyond existing scratch maps.
5) Validation steps: update or add unit tests around trait mutation/clamping and group adoption scoring; run `pytest tests/python`. Provide deterministic seed recipe for manual observation if viewer unavailable.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- From repo root: `python --version` (expect 3.11+).
- Install deps if needed: `pip install -r requirements.txt`.
- Run tests after changes: `pytest tests/python` (should pass deterministically).
- Completed on 2025-12-19: `python --version` (Python 3.12.12) and `pytest tests/python` (all passing).

## Validation and Acceptance

- Functional: Agents should inherit new social traits; group adoption likelihood increases with higher sociality/loyalty, while high loyalty delays detachment/switch; founder increases new-group formation chances; territoriality amplifies avoidance of other groups; sociality strengthens cohesion/alignment; kin_bias biases group selection toward neighbors sharing lineage when ties exist.
- Deterministic smoke: Run a fixed-seed simulation headless for N ticks and log group counts, births/deaths, and average energies; outcomes should be repeatable across runs with same seed/config.
- Performance: Observe tick metrics remain stable (expect Phase 1 to handle existing default population without regressions); no O(N²) loops introduced.
- Long-run stability: Density/stress/resource feedbacks remain intact; population should neither explode nor collapse solely due to new traits.
- Sim/View separation: All changes remain in simulation code and config; no rendering dependencies.

## Idempotence and Recovery

- Plan steps can be reapplied safely; code changes occur via tracked commits.
- If mutations cause instability, reduce mutation weights/clamps in config and re-run validation.

## Artifacts and Notes

- Capture relevant diff snippets and test outputs during implementation.

## Interfaces and Dependencies

- `AgentTraits` gains five new float fields defaulting to 1.0.
- `EvolutionConfig` gains clamp tuples and mutation weights for these fields, parsed from YAML.
- Group dynamics functions use these traits without altering SpatialGrid interfaces or environment dependencies.
