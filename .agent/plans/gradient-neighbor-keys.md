# Gradient sampling via grid keys

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Refactor World gradient calculations (food, pheromone, danger) to use EnvironmentGrid cell indices instead of per-call Vector2 neighbor additions, reducing temporary allocations while keeping outputs identical. Verify determinism with fixed scenarios.

## Progress

- [x] (2024-05-05 00:00Z) Draft plan.
- [x] (2025-12-19 07:20Z) Implement grid-key-based gradients and offset reuse.
- [x] (2025-12-19 07:20Z) Add unit tests covering fixed neighbor scenarios.
- [x] (2025-12-19 07:22Z) Run pytest tests/python and validate.
- [x] (2025-12-19 07:23Z) Final review and update Outcomes.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Use EnvironmentGrid key operations to sample neighbor cells rather than new Vector2 offsets.
  Rationale: Matches requested refactor to avoid repeated Vector creation and align with grid indexing.
  Date/Author: 2024-05-05 Codex

## Outcomes & Retrospective

Gradient sampling now uses EnvironmentGrid cell keys, eliminating per-call neighbor Vector2 allocations. Added deterministic unit coverage for food, pheromone, and danger gradients (interior and boundary), and pytest suite passes.

## Context and Orientation

Key code paths:
- `src/terrarium/world.py` — gradient helpers `_food_gradient`, `_pheromone_gradient`, `_danger_gradient` currently sample via position offsets.
- `src/terrarium/environment.py` — grid storage and sampling methods; provides `_cell_key`, `peek_food`, `sample_pheromone`, `sample_danger`.
- Tests in `tests/python/test_world.py` will exercise gradient logic.

Constraints to restate:
- Simulation and visualization remain separate; only simulation touched.
- No O(N²) loops: gradients use fixed neighboring cells only.
- Determinism: sampling via grid keys must be reproducible per seed and timestep.
- Long-run stability: unchanged behavior expected; gradients should not alter feedback loops.

## Plan of Work

1. Introduce helper in `World` to derive orthogonal neighbor keys using `EnvironmentGrid._cell_key`/`_add_key2`, and precompute/reuse offsets instead of creating multiple Vector2 instances.
2. Adjust gradient helpers to fetch neighbor values via keys, calling `peek_food`, `sample_pheromone`, and `sample_danger` without intermediate Vector additions; ensure only one Vector2 result is allocated.
3. Update `EnvironmentGrid` sampling functions to accept precomputed cell keys (tuples) as inputs while preserving existing Vector2 call behavior.
4. Add deterministic unit tests in `tests/python/test_world.py` covering fixed grid setups for food, pheromone, and danger gradients to confirm identical outputs.
5. Run `pytest tests/python` to verify no regressions.

## Concrete Steps

- Modify `src/terrarium/world.py` to add neighbor-key helper and refactor gradient functions to use keys and minimal Vector allocations.
- Update `src/terrarium/environment.py` sampling methods to accept tuple keys.
- Extend `tests/python/test_world.py` with fixed-value gradient assertions.
- From repo root, run:
  - `python --version` (ensure 3.11+)
  - `pip install -r requirements.txt` (if env not prepared)
  - `pytest tests/python`

## Validation and Acceptance

- Deterministic smoke: run `pytest tests/python::test_food_gradient_...` etc.; expect gradients to match expected vectors for fixed cell values.
- Long-run stability: unchanged as core simulation logic untouched beyond sampling method; ensure existing tests still pass.
- Performance sanity: gradients avoid per-call Vector neighbor allocations; no O(N²) changes.
- Sim/View separation: only simulation-side sampling altered; no visualization impact.

## Idempotence and Recovery

- Changes are local and reversible via git checkout of touched files.
- Tests provide immediate verification; rerun after adjustments.

## Artifacts and Notes

- None yet.

## Interfaces and Dependencies

- `EnvironmentGrid.peek_food`, `sample_pheromone`, and `sample_danger` must accept either positions or cell-key tuples.
- `World._food_gradient`, `_pheromone_gradient`, `_danger_gradient` must return identical vectors to prior implementation given the same grid state.
