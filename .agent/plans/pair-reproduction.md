# Implement pair-based reproduction in the simulation

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is stored at `.agent/plans/pair-reproduction.md` from the repository root and must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

The simulation should only spawn offspring when two eligible parents pair within a local neighbor radius, while preserving determinism and locality. Players should be able to see that reproduction requires nearby mates, that child traits and appearance derive from both parents (including circular hue averaging), and that lineage/group inheritance follow the new rules. This is observable via deterministic tests and reproducible simulation runs.

## Progress

- [x] (2025-09-26 19:35Z) Audit current reproduction flow, traits/appearance inheritance helpers, and tests to update for pair-based logic.
- [x] (2025-09-26 19:54Z) Implement pair-based reproduction flow and inheritance helpers across lifecycle/world/config.
- [x] (2025-09-26 20:04Z) Update tests and docs, then run required Python test suite.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Implement deterministic mate choice by nearest neighbor with ID tiebreak.
  Rationale: Keeps reproduction deterministic and O(N) while aligning with user-requested design.
  Date/Author: 2025-09-26 / Codex

## Outcomes & Retrospective

Pending.

## Context and Orientation

The reproduction logic lives in `src/terrarium/lifecycle.py` and `src/terrarium/world.py`. The `World.step()` method coordinates simulation ticks and calls lifecycle functions, while `SpatialGrid` neighbor queries supply local neighbor lists. Current inheritance helpers cover single-parent trait/appearance mutation; new pair-based helpers must be introduced. Tests under `tests/python` encode deterministic behavior and must be updated for the new pairing requirements.

## Plan of Work

First, inspect the current lifecycle reproduction logic and identify where single-parent reproduction is triggered, including how neighbors are gathered and how children are spawned. Next, add pair-based inheritance helpers in `src/terrarium/world.py` for traits, appearance (including circular hue mean), lineage, and group, and wire them into the reproduction logic in `src/terrarium/lifecycle.py`. Update `World.step()` to manage `paired_ids` and pass neighbor data into lifecycle processing. Add a new mutation chance config in `src/terrarium/config.py` while keeping determinism intact. Finally, adjust or add Python tests in `tests/python` to cover the pair-based requirements, and update any relevant docs to match the new reproduction rules.

## Concrete Steps

Run the following commands from the repository root to orient and validate changes:

    rg "reproduction" src/terrarium
    rg "life_cycle" -n src/terrarium
    rg "inherit" src/terrarium/world.py
    rg "lineage" src/terrarium

After code changes, run:

    python --version
    pip install -r requirements.txt
    pytest tests/python

Expected: Python 3.11+ version output; tests complete successfully.

## Validation and Acceptance

Deterministic smoke run: start a headless run with a fixed seed, run for a fixed number of steps, and log population/births/deaths/average energy (use existing logging hooks or tests) to verify reproduction happens only with neighbors. The run should be reproducible across identical seeds/configs.

Visual sanity check: run the viewer or manual simulation and confirm reproduction occurs only when agents approach each other, and that overall population remains stable without runaway growth or extinction.

Performance sanity check: validate that neighbor queries remain local (SpatialGrid), and observe tick time at a representative population (e.g., 200 agents) to ensure no regressions.

No O(N^2): confirm mate selection uses neighbor lists only; no global scanning is introduced.

Sim/View separation: verify reproduction logic is entirely in the simulation core and view remains read-only.

Acceptance criteria: a human can observe that offspring are produced only from paired parents, that child traits/appearance reflect both parents with deterministic mutation, and that lineage/group inheritance follow the specified rules.

## Idempotence and Recovery

All edits are confined to simulation and tests; changes can be reverted by resetting to the previous git commit. Running tests and smoke runs is safe and repeatable.

## Artifacts and Notes

No artifacts yet.

## Interfaces and Dependencies

Expect to edit:
- `src/terrarium/lifecycle.py` (pair-based reproduction flow).
- `src/terrarium/world.py` (inheritance helpers, step orchestration).
- `src/terrarium/config.py` (new mutation chance config).
- `tests/python/...` (updated deterministic reproduction tests).
- Any relevant docs describing reproduction behavior.

No new external dependencies are planned.
