# Size-Scaled Group Splitting

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Make group splitting more likely as local group size grows so densely packed colonies bud into smaller clusters instead of remaining monolithic. Outcome should remain deterministic (seeded RNG) and respect SpatialGrid locality, promoting visible colony fission without O(N2) scans.

## Progress

- [x] (2025-12-13 22:05Z) Drafted plan.
- [x] (2025-12-13 22:24Z) Implemented size-scaled split probability in config + world; added size-based stress boost while keeping locality/determinism.
- [x] (2025-12-13 22:32Z) Added unit test for size-driven split; ran `pytest tests/python` (all passed).
- [x] (2025-12-13 22:36Z) Updated README grouping note and recorded outcomes.
- [x] (2025-12-14 06:10Z) Baseline headless run `--steps 5000 --seed 42` → groups peaked at 72, dropped to 1 at tick 150, ended at 8; trend shows early collapse toward a dominant group despite size-based split bonus.
- [x] (2025-12-14 06:15Z) Implemented merge cooldown + minority guard + recruit-on-split; added three unit tests, updated README, reran `pytest tests/python` (22 passed), and headless `--steps 12000 --seed 42` (avg groups last 500 ticks ≈ 42.6, no post-warmup collapse).

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence (short logs, measurements, or repro steps).

- (2025-12-14) Headless baseline (`artifacts/headless_baseline.csv`, seed 42) showed groups briefly hit 1 at tick 150 despite max 72 earlier; average groups in last 500 ticks ≈ 8.8, indicating splits form but are reabsorbed over time.
- (2025-12-14) After cooldown/guard changes, 12k-step headless run (`artifacts/group_split_guard.csv`, seed 42) kept group count high (mid-run avg ≈ 49.5, last 500 ticks avg ≈ 42.6); longest single/zero-group run limited to warmup window (151 ticks).

## Decision Log

Record every decision made while working on the plan in the format:
- Decision: …
  Rationale: …
  Date/Author: …

- Decision: Add `group_split_size_bonus_per_neighbor`, `group_split_chance_max`, and `group_split_size_stress_weight`; compute split chance as base + size bonus capped, and count same-group neighbors toward an effective stress gate.
  Rationale: Ensures larger local groups both meet the stress gate sooner and face higher split probability without needing global counts or O(N2) scans; keeps determinism via existing RNG.
  Date/Author: 2025-12-13 / Codex
- Decision: Add a merge cooldown + minority guard so agents with nearby allies ignore majority adoption for a short window; when a split creates a new group, recruit a few nearby allies to seed the colony.
  Rationale: Current splits spawn solo agents that get instantly reabsorbed by the nearby majority, leading to single-group dominance in long runs; guarding adoption and seeding a cluster should let colonies persist while staying local.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

- Size scaling is config-driven and deterministic; large local clusters hit the stress gate and split more readily, while default caps keep probability modest (base 0.02 + 0.01 per ally above threshold, capped at 0.15).
- Pytest run: 22 passed in ~0.6s on this machine (`.venv\Scripts\python -m pytest tests/python`).
- No regressions observed; behavior remains local (SpatialGrid neighbors only) and View untouched; new tests cover split recruitment, adoption guard, and cooldown decay.
- Split recruitment + adoption guard keep colonies from collapsing into a single dominant group in 12k-step headless smoke (seed 42): groups stay >30 after warmup; cooldown prevents immediate reabsorption of breakaway clusters.

## Context and Orientation

- Repo rules to restate: strict Sim/View separation (View only reads snapshots), no O(N2) all-pairs (SpatialGrid neighbors only), maintain negative feedback loops for stability, determinism via seeded RNG + fixed Δt, Phase 1 uses cube instancing only.
- Key files: `src/terrarium/world.py` (group membership + split), `src/terrarium/config.py` (feedback knobs), `tests/python/test_world.py` (group behavior coverage), `README.md` (user-facing parameter list), `docs/DESIGN.md` (design constraints).
- Locality assurance: use existing neighbor list (`_neighbor_agents` with SpatialGrid) and same-group counts; avoid global scans.

## Plan of Work

1) Harden split outcomes: when a split succeeds, peel off a few nearest same-group neighbors into the new group (configurable count, within cohesion radius) and apply a merge cooldown so they are not immediately re-adopted.
2) Add adoption guard/cooldown knobs to `FeedbackConfig` and thread them through `_update_group_membership` so agents with nearby allies or in cooldown ignore majority adoption; keep all logic local to neighbor lists.
3) Update tests to cover split recruitment + cooldown behavior (deterministic, local) and extend README grouping notes with the new parameters.
4) Validation: `pytest tests/python` (required) and a headless run (e.g., `--steps 12000 --seed 42 --log artifacts/group_split_guard.csv`) to confirm groups stay >1 in late ticks.

## Concrete Steps

- Worktree: `c:\LifeOfPikarin`
- Commands:
  - `.\.venv\Scripts\python -m pytest tests/python`
  - `.\.venv\Scripts\python -m terrarium.headless --steps 12000 --seed 42 --log artifacts/group_split_guard.csv`

## Validation and Acceptance

- With default settings, behavior stays deterministic and O(N2)-free; large local groups have higher split probability proportional to nearby same-group count, capped by config.
- New test passes showing size bonus path; all existing pytest suites still pass.
- Performance sanity: locality-only math keeps tick duration roughly unchanged (expect similar ~10-12 ms per tick with ~240 agents on this machine).
- Long-run stability: negative feedback (density stress, disease, soft caps) unchanged; splits reduce overcrowding risk.
- Sim/View separation preserved; boundary rules unchanged.

## Idempotence and Recovery

- Config-driven; setting bonus to 0 or max below base reverts to prior behavior. Seeded RNG ensures reproducibility. No persistent side effects; headless logs under `artifacts/` can be deleted.

## Artifacts and Notes

Populate with pytest/headless snippets after runs.

- `pytest tests/python` (2025-12-14): 22 passed.
- Headless: `.venv\Scripts\python -m terrarium.headless --steps 12000 --seed 42 --log artifacts/group_split_guard.csv` (avg groups last 500 ticks ≈ 42.6; max groups 146).

## Interfaces and Dependencies

- Expose knobs in `FeedbackConfig`: base split chance (existing), size bonus per same-group neighbor above threshold, and a max split chance clamp.
- World split logic consumes these knobs; tests rely on `World._try_split_group` via `step`.
