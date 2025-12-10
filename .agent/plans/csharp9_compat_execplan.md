# C#9 compatibility refactor for Unity 6

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Update the terrarium simulation and related Unity integration code to avoid C# 10+ syntax so the code compiles under Unity 6 (C# 9 /.NET Standard 2.1). Behavior and public APIs stay the same; only compatibility syntax changes are allowed.

## Progress

- [x] (2025-01-05 00:00Z) Drafted ExecPlan.
- [x] (2025-01-05 00:00Z) Convert file-scoped namespaces to block namespaces across Sim, Unity, and tests.
- [x] (2025-01-05 00:00Z) Replace records/init/with usages with C#9-compatible classes and copy logic.
- [x] (2025-01-05 00:00Z) Add explicit usings as needed for C#9 without implicit globals.
- [x] (2025-12-10 20:38Z) Run existing test suite to confirm behavior matches (.NET 8.416 on Windows; all SimTests passing).

## Surprises & Discoveries

- dotnet CLI was initially unavailable; now verified on Windows with .NET 8.416 and all SimTests passing.

## Decision Log

- Decision: Use classes with explicit equality implementations where record value equality was relied upon.
  Rationale: Preserves test expectations while removing record syntax.
  Date/Author: 2025-01-05 Codex

## Outcomes & Retrospective

- All file-scoped namespaces, records, and init-only setters were migrated to C#9-friendly constructs; deterministic behavior and public APIs stayed the same.
- Verified on Windows with .NET SDK 8.416: `dotnet test tests/SimTests/SimTests.csproj` passes, confirming compatibility and determinism after the refactor.

## Context and Orientation

Key files to touch:
- `src/Sim/*.cs` (Simulation core types, currently using file-scoped namespaces, records, init-only setters).
- `src/Unity/AgentViewMapper.cs` (Unity view mapping and AgentSnapshot record).
- `tests/SimTests/WorldTests.cs` (uses with-expressions on TickMetrics for equality checks).
- `src/SimRunner/Program.cs` (RunnerOptions record for headless runner CLI).

Constraints to keep in mind:
- Simulation and visualization remain separated; Unity view should read-only from sim outputs.
- Avoid O(N²) behavior; neighbor interactions stay via `SpatialGrid` lookups only.
- Maintain determinism: seeded RNG + fixed timestep should reproduce metrics.
- Phase 1 visuals are cube-based; do not introduce GameObject-per-agent behavior.

## Plan of Work

Describe, in prose, the sequence of edits and additions.
1. Convert every file-scoped namespace to block form and indent contents accordingly.
2. Replace record/record struct declarations with sealed classes or structs that preserve existing public members. Add constructors and equality overrides where value semantics are used (e.g., TickMetrics).
3. Change `init` accessors to `set`, adding constructors only when necessary to retain default initialization patterns.
4. Rewrite `with` expressions into manual copy/compare code, ensuring tests still compare metrics ignoring tick duration appropriately.
5. Add explicit `using` directives for `System`, `System.Collections.Generic`, or `System.IO` where implicit usings were previously relied upon so C#9 compilers succeed.

## Concrete Steps

State the exact commands to run and where to run them (working directory).
- Working dir: repository root.
- After edits, run: `dotnet test tests/SimTests/SimTests.csproj`
- Inspect `git status` to ensure only expected files changed.

## Validation and Acceptance

Behavioral acceptance:
- All unit tests under `tests/SimTests` pass with `dotnet test`.
- Deterministic run test still shows matching metrics after adjusting comparisons.
- No new public API names are changed; simulation behavior unchanged (population bounds, resource/hazard dynamics intact).

Deterministic smoke run:
- Command: `dotnet test tests/SimTests/SimTests.csproj`
- Expect all tests to pass; WorldTests covers deterministic metrics for 120 ticks with seed 42.

Performance sanity check:
- Core loop unchanged; expect existing tests to complete within prior timings (no additional allocations in per-tick loops).

Long-run stability check:
- WorldTests `PopulationRemainsBoundedWithFeedback` continues to assert bounded population after 500 steps, indicating negative feedback still active.

No O(N²) note:
- Spatial interactions remain via `SpatialGrid` neighbor queries; no all-pairs loops introduced.

Sim/View separation note:
- Changes are syntax-only; Unity `AgentViewMapper` continues to read from `Agent` snapshots without affecting simulation state.

## Idempotence and Recovery

Edits are mechanical; rerunning the steps is safe. If issues arise, revert with `git checkout -- <file>` for affected files or `git reset --hard` to discard changes.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

- `Terrarium.Sim.World`, `Agent`, `TickMetrics`, `SimulationConfig`, and related config classes must remain with the same public members.
- `AgentSnapshot` class remains the Unity-facing snapshot type with existing properties.
- CLI runner keeps parsing options and invoking `HeadlessRunner.Run` with `SimulationConfig` built from parsed arguments.
