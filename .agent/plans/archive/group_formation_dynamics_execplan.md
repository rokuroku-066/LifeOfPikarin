# Group Formation From Zero With Rare Merge/Split

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Make group (flock/colony) count start at zero so observers can watch spontaneous group formation. Add low-frequency mechanisms for group merging and splitting while keeping determinism, locality (SpatialGrid), and stability intact for the cube-phase simulation.

## Progress

- [x] (2025-12-11 15:10Z) Plan drafted and files identified.
- [x] (2025-12-11 15:52Z) Implement ungrouped bootstrap + group dynamics knobs.
- [x] (2025-12-11 15:58Z) Update Unity mapper and docs/tests.
- [x] (2025-12-11 16:05Z) Run `dotnet test tests/SimTests/SimTests.csproj`.
- [x] (2025-12-11 16:12Z) Validation notes captured and plan closed.

## Surprises & Discoveries

(fill in as they appear)

## Decision Log

- Decision: Represent “no group” with sentinel GroupId = -1 and ignore it in metrics and pheromones.
  Rationale: Ensures groups metric starts at 0 without impacting existing group logic and keeps hashing simple.
  Date/Author: 2025-12-11 / Codex
- Decision: Gate group creation with `GroupFormationWarmupSeconds` (default 6s) and use local probabilistic founding/merge/split.
  Rationale: Provides an observable zero-to-first-group transition while keeping events localized and low-frequency.
  Date/Author: 2025-12-11 / Codex

## Outcomes & Retrospective

Groups now begin unassigned (metrics start at 0) and form via warmup-gated local founding or adoption; merges/splits remain low probability and stress-gated. Simulation/tests stay deterministic and pass.

## Context and Orientation

Relevant files and concepts:
- `src/Sim/World.cs`: simulation loop, neighbor processing, reproduction, metrics, pheromone/danger/food events.
- `src/Sim/Agents.cs`: Agent data model and TickMetrics.
- `src/Sim/Configs.cs`: Simulation/Species/Environment/Feedback parameters.
- `src/Unity/AgentViewMapper.cs`: maps Agent.GroupId to color hue for instanced cubes.
- Tests in `tests/SimTests/WorldTests.cs` cover determinism, spatial grid scope, stability, metrics CSV.

Repository constraints to restate explicitly:
- Sim/View separation: Unity side only reads Agent snapshots; simulation timing stays fixed-step.
- No O(N²): all neighbor logic must stay bounded to SpatialGrid local queries (self + adjacent cells).
- Long-run stability: retain density stress, disease, metabolism, energy soft caps so population neither explodes nor collapses.
- Determinism: seeded RNG only; avoid non-deterministic sources.
- Phase 1 visuals: cubes via GPU instancing; no per-agent GameObjects.

## Plan of Work

1) Add group dynamics controls in config (FeedbackConfig) for formation/merge/split probabilities and warmup; keep defaults conservative to make events observable but infrequent.
2) Bootstrap with all agents ungrouped (GroupId = -1) and track nextGroupId in `World`.
3) In the per-agent loop, add localized group membership updates:
   - Form: ungrouped agents with enough ungrouped neighbors after warmup may found a new group (assign to nearby ungrouped neighbors).
   - Merge: when surrounded by another group, occasionally adopt the local majority group (slow, low-frequency convergence).
   - Split: stressed agents in dense same-group neighborhoods may drop to ungrouped or seed a new group at low probability.
4) Guard pheromone/danger/group-aware behaviors to skip ungrouped IDs; ignore sentinel in metrics; make hue mapping neutral for ungrouped.
5) Update tests to assert groups metric starts at 0 and that group formation can occur under tuned parameters; adjust docs/README if behavior expectations change.

## Concrete Steps

Run commands from repo root unless stated:
- Implement edits in `src/Sim/World.cs`, `src/Sim/Configs.cs`, `src/Sim/Agents.cs`, `src/Unity/AgentViewMapper.cs`, and `tests/SimTests/WorldTests.cs`.
- After code changes: `dotnet test tests/SimTests/SimTests.csproj`.
- Optional smoke: `dotnet run --project src/SimRunner/SimRunner.csproj -- --steps 600 --seed 42 --log artifacts/groups_zero_start.csv`.

Expected transcripts to compare:
- Tests should end with `Total tests: ... Passed!` and exit code 0.
- Smoke CSV first row `groups` column should be 0; later rows should become >0.

## Validation and Acceptance

Behavioral acceptance:
- Groups metric starts at 0 on first logged tick with default config (ungrouped bootstrap).
- Groups form spontaneously after warmup using only local neighbor info; can be observed in metrics CSV increasing from 0.
- Group merges/splits occur but with visibly lower frequency than formation (stochastic, local).
- No O(N²) loops added; neighbor work stays bounded to SpatialGrid lookups.
- Sim/View separation preserved (no Unity hooks inside sim).

Deterministic smoke run:
- Fixed seed run for 600–1200 ticks should be repeatable; metrics CSV identical for same seed/config.
- Performance sanity: tickDurationMs roughly unchanged from baseline (< a few ms for default agent counts).

Long-run stability check:
- Population remains within [5, MaxPopulation] with feedback enabled; births/deaths continue (no extinction runaway).

Visual sanity (Unity/manual):
- Overhead camera shows cubes starting uncolored/neutral, then colored clusters appear over time; occasional small merges/splits without jitter.

## Idempotence and Recovery

- Bootstrap and group transitions are deterministic given seed; rerunning steps reuses same RNG sequence.
- If group counts explode or never form, adjust new feedback parameters (formation chance/warmup) and rerun tests; changes remain localized to config defaults.

## Artifacts and Notes

- Tests: `dotnet test tests/SimTests/SimTests.csproj` (2025-12-11) → passed (12 tests, 0 failed).
- Add brief log snippets or CSV excerpts here after validation to show groups rising from 0 and occasional merge/split counts.

## Interfaces and Dependencies

- New FeedbackConfig fields (formation/merge/split) must be documented and defaulted.
- World uses `_nextGroupId` and sentinel `UngroupedGroupId = -1`; metrics ignore sentinel.
- AgentViewMapper maps ungrouped to neutral hue and grouped IDs to hue buckets.
