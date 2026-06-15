# Add deterministic GroupMemory to shared flock behavior

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. It follows `.agent/PLANS.md`.

## Purpose / Big Picture

Add a small, deterministic shared memory system for groups. Agents report food and danger cells into per-group memory, old entries decay on environment ticks, useful food memories become stronger, misses become weaker, and newly split or mutated groups inherit only a degraded top subset from their parent. The visible behavior should be subtle: hungry grouped agents bend slightly toward known food cells and all grouped agents weakly avoid remembered danger cells, without View code controlling Simulation.

## Progress

- [x] (2026-06-15 00:00Z) Read repository instructions, plan rules, and confirmed Python 3.12.13.
- [x] (2026-06-15 00:01Z) Installed/confirmed dependencies and ran baseline `pytest tests/python`; 65 tests passed.
- [x] (2026-06-15 00:05Z) Drafted this ExecPlan before modifying source.
- [x] (2026-06-15 00:25Z) Added memory config, agent short-term cache fields, group_memory system, and world integration.
- [x] (2026-06-15 00:32Z) Added steering bias, lifecycle reporting/reinforcement, inheritance hooks, metrics, docs, and tests.
- [x] (2026-06-15 00:40Z) Ran unit tests and deterministic headless smoke check.

## Surprises & Discoveries

The existing lifecycle already computes exact consumed food per tick, making it the safest place to report and reinforce food memory without changing resource accounting. Existing danger sensing already returns `sensed_danger` from steering and danger pulses are queued after lifecycle, so danger memory can be reported beside danger pulse queuing.

## Decision Log

- Decision: Implement `GroupMemory` as a new simulation-only system at `src/terrarium/sim/systems/group_memory.py`.
  Rationale: Keeps Model-side state separate from View and avoids adding visualization coupling.
  Date/Author: 2026-06-15 / Codex.
- Decision: Use existing environment cell keys and cap each group's entries at `max_entries_per_group`.
  Rationale: Avoids O(N²) behavior and bounds per-agent memory query cost.
  Date/Author: 2026-06-15 / Codex.
- Decision: Use the main deterministic RNG for split inheritance degradation.
  Rationale: The simulation already uses this stream for group membership changes, so seeded runs remain reproducible.
  Date/Author: 2026-06-15 / Codex.

## Outcomes & Retrospective

GroupMemory was implemented as a bounded, decaying per-group map. Tests verify food reports, misses, danger reports, deterministic split inheritance, and metrics exposure. Existing Python tests still pass and a deterministic headless smoke run completes.

## Context and Orientation

Simulation state lives under `src/terrarium/sim`. `World.step()` in `src/terrarium/sim/core/world.py` advances a fixed timestep. `lifecycle.apply_life_cycle()` consumes food and creates births. `steering.compute_desired_velocity()` computes desired motion from local environment, neighbors, and group biases. Group formation/splitting is in `src/terrarium/sim/systems/groups.py`. Headless logs are produced by `src/terrarium/app/headless.py`.

A memory entry is a compact record keyed by environment cell `(cx, cy)`. It holds food, danger, success, last-seen tick, and hit count. The memory map is per group and bounded to avoid unbounded memory growth.

Repository constraints restated: Simulation and Visualization remain strictly separated; the View never drives Sim. No all-pairs scans are introduced; neighbors still come from `SpatialGrid`, while memory scans are bounded by a small per-group cap. Long-run stability mechanisms such as density stress, disease, resource regeneration, and reproduction suppression remain unchanged. Determinism is preserved through seeded RNG and fixed timestep behavior.

## Plan of Work

Add `MemoryConfig` to `src/terrarium/sim/core/config.py` and include it in YAML loading. Add per-agent cache fields for short-term cells and cached memory steering in `src/terrarium/sim/core/agent.py`. Add `src/terrarium/sim/systems/group_memory.py` with `MemoryEntry`, `GroupMemory`, reporting, decay, pruning, query, inheritance, and metrics helpers. Instantiate and reset `GroupMemory` in `World`, decay it alongside environment ticks, report food/danger from lifecycle/world, and wire inheritance from group split/mutation. Add a weak memory steering vector in `steering.compute_desired_velocity()`. Add memory metrics to `TickMetrics` and detailed headless CSV. Update tests and design docs.

## Concrete Steps

Run from `/workspace/LifeOfPikarin`:

    python --version
    pip install -r requirements.txt
    pytest tests/python

After edits, run:

    pytest tests/python
    python -m terrarium.app.headless --steps 120 --seed 42 --deterministic-log --log /tmp/group_memory_metrics.csv --log-format detailed --summary /tmp/group_memory_summary.json

Expected results: pytest passes, headless command exits 0, and detailed CSV contains memory columns such as `group_memory_entries`.

## Validation and Acceptance

Acceptance behavior: grouped agents that eat report their cell to group memory; hungry grouped agents receive a small pull toward remembered food; danger reports create a weak repulsion; entries decay and are pruned; split child groups inherit at most top-k degraded entries. Deterministic smoke run uses seed 42 and fixed timestep through the headless command above. Metrics/log lines should include population, births/deaths, groups, average energy/age, tick duration, and group memory counters. Visual sanity can be checked by running the web viewer and observing that agents still move smoothly from the fixed oblique camera; this change does not alter viewer rendering.

Performance sanity: `max_population=700` remains expected. Memory query cost is at most `max_entries_per_group` entries and can be strided by `memory_query_stride`, so it is bounded and does not scan all agents. Long-run stability is preserved by leaving density/resource/metabolism feedback unchanged and by decaying/removing stale memories.

## Idempotence and Recovery

All commands are safe to repeat. If tests fail, inspect the failing test, revert only the related edits with `git checkout -- <path>` if needed, and rerun `pytest tests/python`. The plan can be updated at each retry.

## Artifacts and Notes

Baseline validation transcript: `65 passed in 1.82s` before source edits.

## Interfaces and Dependencies

New interface: `SimulationConfig.memory: MemoryConfig`; `World._group_memory: GroupMemory`; `group_memory.GroupMemory.report_food`, `report_danger`, `reinforce_food_visit`, `decay`, `query_bias`, `inherit_memory`, and `summary`. No new third-party dependency is required.
