# Add group-biased hue mutation for appearance inheritance

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Per .agent/PLANS.md, this document must be maintained throughout implementation.

## Purpose / Big Picture

The goal is to introduce an optional group-derived bias to appearance hue mutations so that group averages are nudged away from the initial mean, while keeping determinism and preserving existing behavior when the bias is zero. This change will be visible in long-run simulations as group hues drift in stable, deterministic directions when mutations occur, without altering simulation timing or View logic.

## Progress

- [x] (2025-12-26 06:38Z) Review existing appearance inheritance, config wiring, and tests; draft update plan for bias and clamping.
- [x] (2025-12-26 06:39Z) Implement group bias helper and apply to appearance inheritance paths.
- [x] (2025-12-26 06:39Z) Update tests and documentation to reflect new config option.
- [x] (2025-12-26 06:39Z) Run required Python environment checks and unit tests.
- [x] (2025-12-26 06:42Z) Update default group hue bias to 0.2 and revalidate tests.
- [x] (2025-12-26 06:45Z) Align pair hue bias with child group choice and add coverage.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Use a simple integer hash with LSB to derive the group sign.
  Rationale: Matches the requirement for a deterministic ±1 derived from group_id with minimal code change.
  Date/Author: 2025-09-27 / Codex
- Decision: Set `appearance.bias_h_group_deg` default to 0.2.
  Rationale: Aligns with follow-up requirement to enable a small default bias while keeping zero available for opt-out.
  Date/Author: 2025-12-26 / Codex
- Decision: Use the final child group id when biasing pair appearance mutations.
  Rationale: Ensures hue drift aligns with the child’s actual group membership in cross-group mating.
  Date/Author: 2025-12-26 / Codex

## Outcomes & Retrospective

Implemented group-biased hue mutation with deterministic sign hashing, added coverage for clamped bias behavior, and documented the new configuration option. All required Python tests passed. Updated the default group bias to 0.2 per follow-up and revalidated tests. Pair appearance bias now uses the final child group id with added coverage.

## Context and Orientation

Appearance inheritance is implemented in `src/terrarium/sim/core/world.py` in `_inherit_appearance` and `_inherit_appearance_pair`. Appearance configuration lives in `src/terrarium/sim/core/config.py` under `AppearanceConfig`. Appearance mutation determinism is verified in `tests/python/test_world.py` in `test_appearance_inheritance_is_deterministic_and_mutates`. Simulation and View are strictly separated, and no rendering or View-side behavior must be altered by this change.

Key constraints to respect:

Simulation and Visualization are strictly separated; View never drives Sim. Neighbor interactions must stay local via SpatialGrid, with no O(N²) scans. Long-run stability feedback loops must remain intact. Determinism is mandatory, using fixed seeds and deterministic RNG streams.

## Plan of Work

I will add a `bias_h_group_deg` field to `AppearanceConfig` in `src/terrarium/sim/core/config.py` with a default of 0.0. In `World`, I will add a `_group_wind_sign(group_id)` helper that returns 0.0 for ungrouped agents and ±1.0 based on a deterministic integer hash. I will update `_inherit_appearance` to add the group bias only when a mutation occurs, clamping the hue delta to `[-mutation_delta_h, +mutation_delta_h]` before wrapping.

For `_inherit_appearance_pair`, I will choose the group id for bias by checking if parents share the same group id; if they differ, I will select one using the appearance RNG to keep the mutation stream deterministic. The bias will then be applied to the hue mutation delta with the same clamping rule.

I will update tests in `tests/python/test_world.py` to cover the new bias behavior, including clamping and determinism. I will also update the README to mention the new configuration option so documentation stays synchronized.

## Concrete Steps

1. Add `bias_h_group_deg` to `AppearanceConfig` and confirm config loading uses the field via `AppearanceConfig(**raw.get("appearance", {}))`.
2. Implement `_group_wind_sign` in `World`, and apply its result in `_inherit_appearance` and `_inherit_appearance_pair` during hue mutation only.
3. Update or add tests in `tests/python/test_world.py` to validate deterministic bias and clamping.
4. Update README with a brief description of the new configuration field.
5. Run `python --version`, `pip install -r requirements.txt`, and `pytest tests/python` from repo root.

Expected command transcripts:

    $ python --version
    Python 3.11.x

    $ pytest tests/python
    ...
    1 passed

## Validation and Acceptance

Acceptance is met when:

- With `bias_h_group_deg=0.0`, appearance mutations behave exactly as before.
- With a non-zero bias, only hue mutations are shifted by a group-derived sign, and the delta is clamped to the `mutation_delta_h` range.
- The RNG stream remains deterministic for the same seed, verified by unit tests.

Deterministic smoke run recipe: Use `python -m terrarium.app.headless --steps 200 --seed 42 --log tests/artifacts/metrics.csv --log-format basic` and confirm population, births/deaths, and groups do not exhibit non-deterministic variation between runs.

Visual sanity check: Run the viewer (`uvicorn terrarium.app.server:app --reload --port 8000`) and confirm agents move smoothly with group coloration showing steady bias per group, while the camera remains fixed and View does not control Sim.

Performance sanity check: Use the headless run and confirm tick time remains stable (no added O(N²) loops). The group bias should use constant-time per-agent work.

No O(N²) explicit note: Appearance inheritance operates per agent and uses deterministic RNG; no neighbor scanning is added.

Sim/View separation explicit note: The new bias is computed inside the Simulation world and only affects snapshot appearance values; View reads snapshots only.

## Idempotence and Recovery

Edits are local and repeatable. If a change causes incorrect hue bias, revert the affected functions in `world.py` and the new config field, then rerun the tests.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

- `src/terrarium/sim/core/config.py`: `AppearanceConfig` gains `bias_h_group_deg: float`.
- `src/terrarium/sim/core/world.py`: `World._group_wind_sign`, `_inherit_appearance`, `_inherit_appearance_pair` updated.
- `tests/python/test_world.py`: new or updated tests for bias behavior.
- `README.md`: note about `appearance.bias_h_group_deg`.
