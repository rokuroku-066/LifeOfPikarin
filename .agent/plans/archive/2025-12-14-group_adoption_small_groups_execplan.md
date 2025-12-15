# Small groups recruit nearby agents more easily

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated. Follow `.agent/PLANS.md`.

## Purpose / Big Picture

Make under-populated groups easier to join: relax the neighbor threshold and boost adoption chance for small groups while keeping determinism, spatial-grid locality (no O(N²)), Sim/View separation, and Phase 1 cube scope intact.

## Progress

- [x] (2025-12-14 14:05Z) Drafted plan
- [x] (2025-12-14 14:40Z) Implemented config + world logic + tests + docs
- [x] (2025-12-14 14:52Z) Run `pytest tests/python`
- [x] (2025-12-14 14:54Z) Review results & update plan

## Surprises & Discoveries

- TBD

## Decision Log

- Decision: Bias adoption by group size—threshold becomes `min(base_threshold, group_size)` and probability scales with `group_adoption_small_group_bonus / group_size`.
  Rationale: Lets small groups recover without making big groups over-dominant; uses only local neighbor counts plus cached group sizes so O(N²) is avoided.
  Date/Author: 2025-12-14 / Codex

## Outcomes & Retrospective

- TBD

## Context and Orientation

- Core files: `src/terrarium/world.py` (group membership: `_update_group_membership`, `_try_adopt_group`), `src/terrarium/config.py` (feedback knobs), `tests/python/test_world.py` (group adoption/switching cases), `docs/DESIGN.md` (group rules).
- Constraints (repo non-negotiables):
  - Sim (fixed timestep, deterministic RNG) and View are strictly separated; View reads state only.
  - All neighbor logic uses spatial grid; no O(N²) scans.
  - Long-run stability via feedback (density stress, disease, reproduction penalties) must remain.
  - Phase 1 visuals: cubes with instancing; no per-agent GameObjects/FBX.

## Plan of Work

1) Track live group sizes each tick (cache on grid insert) to reuse in adoption logic.
2) Update `_try_adopt_group`:
   - Effective neighbor threshold = `min(group_adoption_neighbor_threshold, group_size)` (floor 1).
   - Adoption chance = `group_adoption_chance * (1 + group_adoption_small_group_bonus / group_size)` clamped to 1.
   - Keep cooldown/guard rules unchanged.
3) Add config knob `group_adoption_small_group_bonus` with a sensible default.
4) Tests:
   - Adjust existing threshold test to still cover non-adoption when group is large but local neighbors are few.
   - Add test proving small groups can adopt with relaxed threshold.
5) Docs: note size-aware adoption in the group section.
6) Validation: run `pytest tests/python`; note deterministic smoke and long-run sanity.

## Concrete Steps

- Edit `src/terrarium/world.py`: cache `_group_sizes` in `step`, use it in `_try_adopt_group` for threshold/probability.
- Edit `src/terrarium/config.py`: add `group_adoption_small_group_bonus`.
- Edit `tests/python/test_world.py`: adjust neighbor-threshold test; add small-group adoption test.
- Edit `docs/DESIGN.md`: document size-aware adoption.
- Run from repo root: `pytest tests/python`

## Validation and Acceptance

- Tests: `pytest tests/python` must pass.
- Behavior: lone member near a 1-agent group can join even when base threshold > 1; large groups still require meeting the base threshold when local neighbors are insufficient.
- Performance: no new O(N²); group sizes cached once per tick; per-tick allocations unchanged materially.
- Stability: existing density/negative feedback untouched; determinism preserved (DeterministicRng).

## Idempotence and Recovery

- Re-running edits is safe; cached group size map is rebuilt each tick.
- If adoption becomes too aggressive, lower `group_adoption_small_group_bonus` or raise `group_adoption_neighbor_threshold`; changes are config-only.

## Artifacts and Notes

- New config field: `group_adoption_small_group_bonus` in `FeedbackConfig`.
- New tests covering size-aware adoption.

## Interfaces and Dependencies

- `World._group_sizes: Dict[int, int]` rebuilt per tick.
- `FeedbackConfig.group_adoption_small_group_bonus: float` (default 1.5).
- `_try_adopt_group` uses cached group size for threshold/probability; respects `group_adoption_guard_min_allies` and `group_merge_cooldown_seconds`.
