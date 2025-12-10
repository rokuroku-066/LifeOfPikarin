# Environment field diffusion and decay integration

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Extend the environment to track food, pheromone, and danger scalar fields per cell that diffuse to neighbors and decay over time, then integrate them into the World tick so agent actions modify fields and agent decisions weigh these fields. The end result lets agents forage toward food, prefer home pheromone, and flee danger while the fields spread and fade deterministically each tick.

## Progress

- [x] (2024-06-03 00:00Z) Drafted ExecPlan and surveyed EnvironmentGrid, Configs, World behavior, and test locations.
- [x] (2025-12-10 07:05Z) Implemented field storage and diffusion/decay for food, pheromone, and danger in EnvironmentGrid with configurable rates.
- [x] (2025-12-10 07:20Z) Updated World step ordering to apply agent lifecycle, field injections from actions, then diffuse/decay; adjusted AI weighting to consider fields.
- [x] (2025-12-10 07:11Z) Add/adjust unit tests and docs to cover new field behavior and AI weighting; run test suite.
- [x] (2025-12-10 07:12Z) Finalize plan outcomes and summarize results.

## Surprises & Discoveries

- Added a fallback to use a random escape vector when danger concentration lacks a spatial gradient so agents still flee high-danger tiles.

## Decision Log

- Decision: Use dictionary-backed scalar fields per cell with diffusion computed by decaying value then spreading a fraction to the four orthogonal neighbors, retaining the remainder to avoid O(N²) scans.
  Rationale: Maintains locality and determinism while honoring design constraints for performance.
  Date/Author: 2024-06-03 / assistant

## Outcomes & Retrospective

- Added diffusing food/pheromone/danger fields with decay plus per-group pheromones and event-driven deposits.
- World ticks now apply lifecycle first, then inject field events from births/deaths/flee states before diffusing/decaying fields.
- Tests cover food regeneration, danger diffusion, pheromone diffusion, and agent flee behavior from danger fields; all tests pass on .NET 8.

## Context and Orientation

- Key files: `src/Sim/Environment.cs` (EnvironmentGrid fields and tick), `src/Sim/Configs.cs` (environment parameters), `src/Sim/World.cs` (agent step order and AI decisions), `tests/SimTests` for simulation tests, `docs` for design notes.
- Simulation and visualization remain separated; only simulation core will change.
- Neighbor interactions rely on SpatialGrid to avoid O(N²); field diffusion operates locally on neighbor cells only.
- Long-run stability depends on capped resources, decay of signals, and deterministic RNG seeded via config.

## Plan of Work

Describe, in prose, the sequence of edits and additions.
1. Expand EnvironmentConfig with per-field diffusion and decay rates plus initial/default values for food, pheromone, and danger fields.
2. Refactor EnvironmentGrid to store food, pheromone, and danger scalar fields per cell, supporting sampling, addition, consumption, and a Tick method that regenerates food where applicable and applies diffusion/decay for all fields using preallocated buffers.
3. Update World step to follow the required order: move/lifecycle agents, then apply field updates driven by actions (birth pheromone, death food, danger increment), then call field diffusion/decay. Adjust agent decision weights to favor food-rich cells, prefer own-group pheromones, and avoid danger when computing desired velocity.
4. Extend or add unit tests validating diffusion/decay for fields and AI weighting impacts, and update docs to describe new environment fields and tick order. Run the required test suite.

## Concrete Steps

- Edit `src/Sim/Configs.cs` to add diffusion/decay parameters and defaults for food, pheromone, and danger fields.
- Modify `src/Sim/Environment.cs` to manage three scalar fields with sampling/add/consume APIs and implement diffusion/decay per tick while keeping regeneration deterministic and avoiding per-tick allocations in tight loops.
- Adjust `src/Sim/World.cs` to inject field updates after lifecycle effects, integrate fields into AI decision weighting, and ensure Tick order matches the requested sequence.
- Update `tests/SimTests` to cover field diffusion/decay and agent behavior with fields; adjust docs (e.g., README or design notes) to reflect new environment fields.
- Run `dotnet test tests/SimTests/SimTests.csproj` from repo root and capture results.

## Validation and Acceptance

- Deterministic smoke run: World initialized with seed should tick with stable population metrics; metrics should remain deterministic given the same seed.
- Field diffusion/decay: unit tests should show that food/pheromone/danger values diffuse to neighboring cells and decay over ticks with configured rates.
- AI weighting: tests should demonstrate agents move toward higher food/pheromone and away from danger when comparing resulting positions or state choices.
- Performance: field operations use local neighbor diffusion and buffered dictionaries to avoid O(N²) and minimize allocations; expect handling of hundreds of agents with millisecond ticks.
- Sim/View separation: changes confined to simulation core; no rendering dependencies added.

## Idempotence and Recovery

- Text edits are reversible via git; EnvironmentGrid Reset remains usable for repeated runs. Tests can be rerun safely.

## Artifacts and Notes

- Capture relevant logs from tests after execution.

## Interfaces and Dependencies

- EnvironmentGrid should expose methods to sample and mutate food/pheromone/danger fields and a Tick method that updates regeneration and diffusion/decay per field.
- World depends on SpatialGrid for neighbor lookup; new field influences must not introduce global scans.
