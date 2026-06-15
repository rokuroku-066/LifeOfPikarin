# Correct group food hits and throttle danger reports

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. It follows `.agent/PLANS.md`.

## Purpose / Big Picture

This change makes group-memory metrics better match the intended meaning of shared knowledge. A known food cell that produces food again should count as a food-memory hit, while the first discovery remains a food report. Danger reporting should stop counting the same agent repeating the same cell every tick, so danger memory remains useful without drowning out food and success memory.

## Progress

- [x] (2026-06-15 00:00Z) Read repository instructions and baseline code paths for lifecycle food reporting, group memory metrics, and danger pulses.
- [x] (2026-06-15 00:00Z) Ran required pre-edit Python version, dependency install, and unit tests; 70 tests passed.
- [x] (2026-06-15 00:00Z) Implement known-food-cell hit reinforcement and same-agent danger report cooldown.
- [x] (2026-06-15 00:00Z) Add tests and documentation for the revised metric semantics.
- [x] (2026-06-15 00:00Z) Reran required tests; 72 tests passed. Commit and PR remain next.

## Surprises & Discoveries

The existing `GroupMemory.reinforce_food_visit` already increments food hit metrics for positive revisits, but `lifecycle.apply_life_cycle` only calls it on non-positive food outcomes. `World._apply_danger_pulse_if_needed` already updates `last_danger_cell` and `last_danger_tick`, but it updates them unconditionally at report time and does not use them to rate-limit reports.

## Decision Log

- Decision: Use the existing `MemoryConfig` to expose `danger_report_cooldown_ticks` with a default of 50 ticks.
  Rationale: This keeps the throttle deterministic and configurable without introducing unseeded state or new unbounded per-group dictionaries.
  Date/Author: 2026-06-15 / Codex.

- Decision: Count food hits only when a positive food gain happens in a cell already known by the group.
  Rationale: The metric should answer whether shared knowledge led to another successful visit, not whether a brand-new food source was discovered.
  Date/Author: 2026-06-15 / Codex.

## Outcomes & Retrospective

Implemented the food hit metric correction and same-agent danger report cooldown. Focused tests now pass for the touched behaviors; full required tests passed before commit.

## Context and Orientation

`src/terrarium/sim/systems/lifecycle.py` applies metabolism, food consumption, food memory reports, and reproduction. `src/terrarium/sim/systems/group_memory.py` owns bounded group memory entries and metrics. `src/terrarium/sim/core/world.py` emits danger pulses when agents flee or sense danger. `src/terrarium/sim/core/config.py` defines deterministic simulation configuration.

This change is Simulation-only state. The View remains a one-way consumer and never drives the simulation. No all-pairs logic is introduced; food and danger reports are per-agent work using the current cell key already computed by the tick. Determinism is preserved because the new decisions use only tick, agent fields, and configuration.

## Plan of Work

Change `apply_life_cycle` so grouped agents inspect whether `base_cell_key` already exists in their group memory before deciding between `report_food` and `reinforce_food_visit`. Add a `danger_report_cooldown_ticks` integer to `MemoryConfig`. Change `World._apply_danger_pulse_if_needed` so the environment pulse remains unchanged, but `GroupMemory.report_danger` is called only if the agent has not reported the same cell recently. Add tests for both semantics and update design documentation.

## Concrete Steps

Run from `/workspace/LifeOfPikarin`:

    python --version
    pip install -r requirements.txt
    pytest tests/python

After edits, rerun:

    pytest tests/python

## Validation and Acceptance

Acceptance is met when unit tests pass and cover these behaviors: an already-known food cell with positive food increments `food_hits`; a brand-new food cell with positive food creates an entry without incrementing hits; repeated danger reports from the same agent and same cell within the cooldown do not increment `group_danger_memory_reports`, but reports after the cooldown do. A deterministic smoke run remains available through the existing headless tests and should continue reporting group memory metrics without changing simulation/view boundaries.

Manual visual sanity check, if desired, is unchanged: run the web viewer and observe the Phase 2 oblique camera with smooth View interpolation. This change has no rendering impact.

## Idempotence and Recovery

All edits are normal source, test, and docs changes. Rerunning tests is safe. If the behavior is wrong, revert this branch commit or restore the touched files from Git and rerun `pytest tests/python`.

## Artifacts and Notes

Baseline tests passed before editing: `70 passed in 1.82s`. After editing, full tests passed: `72 passed in 1.57s`.

## Interfaces and Dependencies

`MemoryConfig.danger_report_cooldown_ticks` must exist as an integer. `Agent.last_danger_cell` and `Agent.last_danger_tick` remain the per-agent state used for cooldown. No new third-party dependencies are required.
