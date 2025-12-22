# Remove bootstrap_mode configuration and references

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: maintain this plan per `.agent/PLANS.md` rules.

## Purpose / Big Picture

We need to eliminate the `bootstrap_mode` configuration/flag from the codebase and associated documentation so configuration remains single-sourced and users are not instructed to set a deprecated option. The outcome should be a cohesive configuration flow without `bootstrap_mode` references.

## Progress

- [x] (2025-12-16 04:54Z) Drafted initial ExecPlan detailing goals and constraints.
- [x] (2025-12-16 04:55Z) Identified `bootstrap_mode` usages in `src/terrarium/world.py`; none found in docs/config files.
- [x] (2025-12-16 04:55Z) Implement code/config changes removing `bootstrap_mode` and updating defaults as needed.
- [x] (2025-12-16 04:55Z) Update documentation to reflect removal and new configuration guidance.
- [x] (2025-12-16 04:55Z) Run required tests (excluding `tests/python/test_long_run_performance.py`) and record results.
- [x] (2025-12-16 04:55Z) Final retrospective and plan closure.

## Surprises & Discoveries

_None yet._

## Decision Log

- Decision: Remove `bootstrap_mode` gating and always run neighbor-aware steering plus SpatialGrid population from the first tick.
  Rationale: Keeps behavior consistent and deterministic without undocumented special cases while preserving O(N^2)-free locality.
  Date/Author: 2025-12-16 / assistant

## Outcomes & Retrospective

- Removed `bootstrap_mode`, making SpatialGrid neighbor collection and steering active from the first tick while keeping determinism and locality.
- Updated README defaults to match configuration (max_population 700) and documented the removal of bootstrap behavior.
- `pytest tests/python -k 'not test_long_run_performance'` now passes after the change.

## Context and Orientation

- Core simulation and configuration live under `src/terrarium/`.
- Tests reside in `tests/python/` and related paths.
- Documentation lives in `docs/` and `README.md`.
- Repository constraints: maintain determinism, avoid O(N^2) scans, keep Sim/View separation, and update docs/tests alongside code.

`bootstrap_mode` currently appears in configuration and documentation; its removal should keep configuration deterministic and avoid obsolete setup steps.

## Plan of Work

1. Search for all occurrences of `bootstrap_mode` across the repository to understand usage in code, configs, and docs.
2. Determine intended behavior; if necessary, replace with existing defaults or remove conditional logic while preserving deterministic setup.
3. Update configuration files and any code paths referencing `bootstrap_mode` to rely on remaining configuration options.
4. Revise documentation (e.g., README, docs) to remove mentions of `bootstrap_mode` and reflect the new configuration flow.
5. Run the Python test suite excluding `tests/python/test_long_run_performance.py` and ensure it passes; document results.

## Concrete Steps

- Use ripgrep from repo root to locate `bootstrap_mode` references.
- Edit relevant source/config files under `src/terrarium/` (or other paths) to remove the flag and align defaults.
- Update documentation files (README/docs) to reflect the absence of `bootstrap_mode`.
- From repository root, run `pytest tests/python -k 'not test_long_run_performance.py'` (or equivalent exclusion) to validate changes.

Expected command transcript:
  - `pytest tests/python -k 'not test_long_run_performance.py'`

## Validation and Acceptance

Acceptance criteria:
- No references to `bootstrap_mode` remain in code, configuration, or documentation.
- Configuration still produces deterministic initialization without the flag.
- Required tests pass (Python suite excluding `tests/python/test_long_run_performance.py`).
- No new O(N^2) logic introduced; spatial locality preserved.
- Sim/View separation remains intact; changes are confined to configuration and supporting logic.
- Long-run stability considerations remain unaffected by removal.
- Performance expectations hold (no new per-tick allocations or regressions).

## Idempotence and Recovery

Changes are standard file edits; use git to revert if needed. Rerunning the test command is safe and deterministic given fixed seeds.

## Artifacts and Notes

- Key files likely include configuration under `src/terrarium/` and documentation under `README.md` or `docs/`.
- Maintain deterministic seeds and avoid introducing global mutable state.

## Interfaces and Dependencies

- Do not add new external dependencies.
- Keep configuration loading deterministic and documented.
- Ensure remaining configuration interfaces are documented and consistent.
