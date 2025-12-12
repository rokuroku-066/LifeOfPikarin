# Remove legacy C# implementation and references

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Remove the legacy C# implementation and all documentation references so the project is Python-only. The outcome is a repository without C# source, Unity scaffolding, or C# testing instructions; only the Python simulation, server, and web viewer remain, with updated documentation and dependencies.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”). Use timestamps.

- [x] (2025-05-03 00:00Z) Drafted ExecPlan for removing C# implementation and docs.
- [x] (2025-05-03 00:20Z) Delete C#/Unity source, solution, and tests; prune toolchain files.
- [x] (2025-05-03 00:45Z) Update README and docs to describe Python-only workflow and remove C# mentions.
- [x] (2025-05-03 00:55Z) Clean dependencies/scripts referencing C#; validate Python tests.
- [x] (2025-05-03 01:00Z) Final verification and retrospective.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

- Removed legacy C#/Unity sources, solution, and Windows helper script; repository is Python-only. (2025-05-03, assistant)
- Updated AGENTS/README to focus on Python workflow and pytest validation; all Python tests passing. (2025-05-03, assistant)

## Context and Orientation

The repository currently contains both Python and legacy C# implementations. The C# core and Unity integration live under `src/Sim/`, `src/SimRunner/`, and `src/Unity/`, with a solution file `Terrarium.sln` and C# tests in `tests/SimTests/`. Documentation (README, AGENTS) references both language tracks. Python code lives under `src/python/` with FastAPI server, headless runner, and tests in `tests/python/`.

Constraints to restate from PLANS.md and AGENTS.md:
- Simulation and visualization must stay separated; the view only consumes snapshots and never drives simulation.
- Neighbor interactions must avoid O(N²); the SpatialGrid enforces local 3×3 cell queries.
- Long-run stability requires negative feedback loops (resource limits, reproduction suppression, etc.).
- Determinism: seedable, fixed timestep, reproducible runs.
- Phase 1 visuals are cube/2D web canvas only; keep simulation timing independent from rendering.

## Plan of Work

1. Remove C# artifacts: delete `Terrarium.sln`, `src/Sim/`, `src/SimRunner/`, `src/Unity/`, and `tests/SimTests/`. Ensure any C#-specific config files are removed (e.g., .csproj, appsettings) and update `.gitignore` if relevant.
2. Clean Python packaging/deps: ensure `requirements.txt`/`pyproject.toml` contain only Python needs and remove .NET instructions or dependencies.
3. Update documentation: rewrite `README.md` (and any other docs) to describe only the Python simulation, server, and tests. Remove references to C# tooling, Unity, or dotnet commands; keep validation steps for Python tests and headless runs.
4. Sanity-check scripts: update or remove `setup_windows_env.bat` or other helper scripts if they reference dotnet/Unity.
5. Run Python tests (`pytest tests/python`) to confirm functionality after deletions; document the absence of dotnet tests.

## Concrete Steps

State the exact commands to run and where to run them (working directory). When a command generates output, show a short expected transcript so the reader can compare. This section must be updated as work proceeds.

- Delete legacy directories and files: `rm -rf src/Sim src/SimRunner src/Unity tests/SimTests Terrarium.sln`.
- Review dependency files: edit `requirements.txt` and `pyproject.toml` to ensure no C#/dotnet tooling references remain.
- Update docs: edit `README.md` and any other documents mentioning C# to reflect Python-only workflow.
- Run tests: `pytest tests/python` from repo root; expect all tests to pass.

## Validation and Acceptance

- Repository contains only Python simulation/server/viewer code; no C# or Unity directories remain.
- Documentation describes Python setup, headless run, server/WebSocket viewer, and pytest validation; no dotnet/Unity commands are referenced.
- `pytest tests/python` passes after cleanup.
- SpatialGrid/locality and deterministic seed behaviors remain unchanged in Python code; no O(N²) interactions introduced.
- Long-run stability mechanisms remain in Python world config (energy/resource feedbacks) and are documented.

## Idempotence and Recovery

File deletions are irreversible once committed; if removed mistakenly, recover from git history before committing. Documentation edits can be reverted via git checkout of the original files prior to commit.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, and interfaces/types that must exist at the end.

- Python package remains defined via `pyproject.toml` with FastAPI/uvicorn, numpy, and pytest in development dependencies.
- `terrarium` Python package continues to expose simulation primitives (`terrarium.environment.Environment`, `terrarium.world.World`, `terrarium.server` for WebSocket snapshots, `terrarium.headless` for CLI runs).
