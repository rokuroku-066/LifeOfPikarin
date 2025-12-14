# Wide-Spread Group Split to New Colony

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

When a grouped agent drifts without close same-group allies for several seconds, it should bud off into a new group (instead of becoming ungrouped) to seed a fresh colony. This should trigger only when the group is spatially spread out, remain deterministic, and keep overlap avoidance intact.

## Progress

- [x] (2025-12-13 21:05Z) Drafted plan.
- [x] (2025-12-13 21:28Z) Implemented split-to-new-group path with config knob.
- [x] (2025-12-13 21:33Z) Added unit test and README note; ran pytest and headless smoke.
- [x] (2025-12-13 21:40Z) Recorded outcomes/retrospective and artifacts.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- (2025-12-13 21:32Z) With `group_detach_new_group_chance=1.0`, a lone grouped agent splits to a new group on the first qualifying tick; no overlap issues observed because separation/personal_space unchanged.

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: Add `group_detach_new_group_chance` (default 0.6) and branch lonely grouped agents to a new group when switch-to-majority fails and group formation is allowed.
  Rationale: Promote budding into fresh colonies when a group is spatially stretched, instead of leaving agents ungrouped; keeps determinism and locality.
  Date/Author: 2025-12-13 / Codex

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

- Lonely grouped agents can now bud into new groups with deterministic probability; default keeps behavior mild (0.6) but preserves negative feedback via unchanged separation/personal-space.
- Headless smoke (seed 42, 400 steps) remained stable: final population 110, groups 21, avg energy 17.6, tick_ms ~11–13 on this machine; no runaway growth or overlap observed.
- Future tuning: expose per-group cap? Not needed now; behavior meets goal with local-only logic.
## Context and Orientation

- Repo rules: strict Sim/View separation (View only reads snapshots), no O(N²) scans (SpatialGrid neighbor queries only), determinism via seeded RNG and fixed Δt, maintain negative feedback to avoid explosion/extinction, Phase 1 cubes only.
- Key files: `src/terrarium/world.py` (group detach/split logic), `src/terrarium/config.py` (feedback parameters), `tests/python/test_world.py` (group behavior tests), `docs/DESIGN.md` (grouping rules), `src/terrarium/headless.py` (metrics).
- Locality: the change must rely only on existing neighbor lists (cell + adjacent cells) and timers; no global scans.

## Plan of Work

1) Add a `group_detach_new_group_chance` knob to `FeedbackConfig` to control whether lonely grouped agents spawn a new group instead of going ungrouped.
2) Extend `_update_group_membership` in `world.py`: when `group_lonely_seconds` exceeds the detach timer and close-allies remain below threshold, allow branching to a new group (gated by warmup/can_form_groups and the new chance). Keep existing switch-to-majority behavior unchanged.
3) Tests: add a deterministic unit test that forces the new branch (switch chance 0, new-group chance 1, detach timer short) and asserts a new group ID is assigned without going ungrouped.
4) Docs: brief README note about the budding behavior; keep mention of personal-space preventing overlap.
5) Validation: run `pytest tests/python`; optionally run a short headless smoke (seed 42, ~400 steps) to ensure stability.

## Concrete Steps

- `.\\.venv\\Scripts\\python -m pytest tests/python`
- `.\\.venv\\Scripts\\python -m terrarium.headless --steps 400 --seed 42 --log artifacts/wide_split_smoke.csv` (optional sanity)

## Validation and Acceptance

- Lonely grouped agents (few close allies for longer than `group_detach_after_seconds`) create a new group with probability `group_detach_new_group_chance` when group formation is allowed; they no longer default to ungrouped in that branch.
- Determinism preserved for a given seed; no O(N²) logic introduced; existing separation/personal-space prevents overlaps.
- Tests pass; headless smoke shows stable population and group counts >1.

## Idempotence and Recovery

- Config-driven; reruns with the same seed reproduce trajectories. Revert the new knob or set chance to 0 to disable.
- No persistent side effects; headless log files in `artifacts/` can be removed safely.

## Artifacts and Notes

Populate with pytest/headless snippets after runs.

- Pytest: 18 passed in ~1.2s.
- Headless smoke log: `artifacts/wide_split_smoke.csv` (seed 42, 400 steps; final groups 21).

## Interfaces and Dependencies

- `FeedbackConfig.group_detach_new_group_chance` plumbed through SimulationConfig unchanged.
- `World._update_group_membership` uses existing neighbor list and RNG; no Sim/View coupling.
- `tests/python/test_world.py` includes a deterministic case for the new behavior.
