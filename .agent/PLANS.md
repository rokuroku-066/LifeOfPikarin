# Codex Execution Plans (ExecPlans) — rules for this repository

This document defines how to write and maintain an “ExecPlan” for this repository.
An ExecPlan is a self-contained, living specification that a coding agent can follow to deliver a working feature or system change.

Treat the reader as a complete beginner to this repo: they only have the current working tree and the ExecPlan file.

(These rules are based on OpenAI’s Codex ExecPlans guidance and are intentionally strict.)

---

## When to use an ExecPlan
You MUST author an ExecPlan before implementing if any of the following are true:
- The task will likely take > 30 minutes.
- The task touches more than 2 files or introduces new files.
- The task changes simulation rules, data layout, determinism, or performance characteristics.
- The task modifies rendering strategy (instancing, batching, interpolation).
- The task changes how agents find neighbors (SpatialGrid / hashing).
- The task affects long-run stability (population feedback loops).

For small, single-file, obviously-scoped edits, you may proceed without an ExecPlan, but still include verification steps.

---

## Non‑negotiable requirements for every ExecPlan
1) Self-contained: In its current form, it contains all knowledge and instructions needed for a novice to succeed.
2) Living document: It MUST be updated as progress is made, discoveries occur, and decisions are finalized.
3) Demonstrably working outcome: The plan must result in observable behavior, not just “code that compiles”.
4) Plain language: Define any term of art you introduce, or do not use it.
5) Validation is mandatory: Include commands/steps to verify behavior and expected outputs.
6) Idempotence and recovery: Steps should be repeatable; include safe retry/rollback paths if needed.

---

## Repository‑specific constraints that every ExecPlan must restate
Because this is a long-run terrarium:
- Simulation and Visualization are strictly separated; View never drives Sim.
- No O(N²) all-pairs logic; neighbor interactions use SpatialGrid only.
- Long-run stability requires negative feedback loops to avoid explosion/extinction.
- Determinism matters: seedable, fixed timestep, reproducible runs.
- Phase 1 scope is cubes + GPU instancing; avoid per-agent GameObjects where possible.

Even if these are in `docs/DESIGN.md`, repeat the relevant constraints in the ExecPlan.
Do not assume the reader will open other docs.

---

## Formatting rules for ExecPlans
- If you include an ExecPlan inline (e.g., in chat), write it as ONE single fenced code block labeled `md`.
- Do NOT nest additional triple-backtick fences inside that block.
  - When you need to show code/commands/transcripts/diffs, use indented blocks instead.
- Use proper Markdown headings (#, ##, ###) and use two newlines after every heading.
- If you are writing an ExecPlan to a `.md` file where the entire file content is the plan, you should omit the outer triple-backticks.

(Reason: nested fences often break parsing and make plans non-executable.)

---

## Style rules
- Prefer sentences over lists in narrative sections.
- Avoid tables and long enumerations unless they increase clarity.
- Checklists are mandatory ONLY in the `Progress` section.
- Acceptance criteria must be phrased as behavior a human can verify.

---

## Milestones
- Use milestones when there are unknowns or significant risk.
- Each milestone must be independently verifiable and should incrementally deliver part of the final behavior.
- If a prototype/spike is needed, label it explicitly as prototyping and define promote/discard criteria.

---

## The ExecPlan skeleton (copy this)

```md
# <Short, action-oriented description>

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Explain in a few sentences what someone gains after this change and how they can see it working. State the user-visible behavior you will enable.

## Progress

Use a list with checkboxes to summarize granular steps. Every stopping point must be documented here, even if it requires splitting a partially completed task into two (“done” vs. “remaining”).
Use timestamps.

- [ ] (YYYY-MM-DD HH:MMZ) Example step.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation.
Provide concise evidence (short logs, measurements, or repro steps).

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

## Context and Orientation

Describe the current state relevant to this task as if the reader knows nothing.
Name the key files and modules by full path.
Define any non-obvious term you will use.

## Plan of Work

Describe, in prose, the sequence of edits and additions.
For each edit, name the file and location (function, module) and what to insert or change.

## Concrete Steps

State the exact commands to run and where to run them (working directory).
When a command generates output, show a short expected transcript so the reader can compare.
This section must be updated as work proceeds.

## Validation and Acceptance

Describe how to start or exercise the system and what to observe.
Phrase acceptance as behavior, with specific inputs and outputs.

Include:
- a deterministic “smoke run” recipe (seed/config/timestep)
- what metrics/log lines to expect
- a visual sanity check recipe (overhead camera, long-run, group behaviors visible)

## Idempotence and Recovery

If steps can be repeated safely, say so.
If a step is risky, provide a safe retry or rollback path.

## Artifacts and Notes

Include the most important transcripts, diffs, or snippets as indented examples.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, and interfaces/types that must exist at the end.
Prefer stable names and repo-relative paths.
````

---

## Extra acceptance checklist (repo-specific)

Every ExecPlan must include:

* A performance sanity check (what N agents you expect to handle in Phase 1, and how you measure tick time).
* A long-run stability check (what prevents runaway growth/extinction; what you will observe to confirm).
* A “no O(N²)” explicit note (which subsystem enforces locality and how).
* A “Sim/View separation” explicit note (how data flows one-way).

---

## Notes on using Codex for long tasks

* Codex works better with smaller, focused steps and explicit verification recipes.
* Keep the plan updated at every stopping point; do not ask the user for “next steps”—continue to the next milestone.
