# Strengthen agent collision avoidance

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Reference: maintain this plan per `.agent/PLANS.md` rules.

## Purpose / Big Picture

Tighten agent spacing so cubes rarely overlap or clip by boosting short-range repulsion while preserving smooth group motion. The outcome should keep agents from entering each other's personal space without breaking cohesion or destabilizing long-run population dynamics.

## Progress

- [x] (2025-12-16 10:29Z) Drafted ExecPlan with goals, constraints, and validation approach.
- [x] (2025-12-16 10:42Z) Adjusted separation mechanics/config to amplify near-contact repulsion and added positional overlap correction.
- [x] (2025-12-16 10:44Z) Ran pytest suite and captured spacing sanity metrics from a 600-tick headless run.
- [x] (2025-12-16 10:46Z) Updated plan with results/decisions and noted follow-up knobs.

## Surprises & Discoveries

- Steering-only scaling was insufficient; adding a soft positional overlap correction (averaged push up to half the min separation) materially increased observed spacing.
- Headless probe (600 ticks, default seed) now reports min_distance about 0.038 across the run and last_tick_min_distance about 0.421 (baseline before changes was about 0.001 / 0.046). Early ticks can still show brief close passes.
- The distance probe takes roughly 12s; PowerShell invocations need a command timeout of at least 20s to avoid premature termination.

## Decision Log

- Decision: Allow separation to keep magnitude (clamped) and scale by closest neighbor, plus add positional overlap correction using existing neighbor offsets before reflection.
  Rationale: Normalizing separation erased proximity information; scaling and small positional pushes reduce interpenetration without new O(N^2) work.
  Date/Author: 2025-12-16 / assistant
- Decision: Raise spacing defaults (personal space radius/weight, separation weights, min separation distance/weight) and spawn offspring at max(0.5, min_separation_distance).
  Rationale: Larger buffers and birth offsets reduce immediate overlaps and give the new steering more room to act while staying deterministic.
  Date/Author: 2025-12-16 / assistant

## Outcomes & Retrospective

Pytest suite passes after the spacing changes. The 600-tick probe shows higher closest distances (min_distance about 0.038 overall, last_tick_min_distance about 0.421) while keeping performance steady (tests about 0.7s here). Overlaps are rarer but still possible immediately after spawn; further tuning could raise the min separation distance or slow agents when extremely close if visuals still show clipping.

## Context and Orientation

- Simulation core and steering live in `src/terrarium/world.py`; config defaults in `src/terrarium/config.py`.
- Visualization reads snapshots only; Sim/View separation must remain intact.
- Spatial queries use `SpatialGrid`; avoid any O(N^2) pair scans in the sim loop.
- Long-run stability relies on density stress, metabolism, and reproduction throttles; changes must not remove these negative feedbacks.
- Determinism: fixed timestep with seedable `DeterministicRng`; new logic must stay deterministic.
- Phase 1 visuals are instanced cubes; we only adjust simulation forces.

## Plan of Work

1. Inspect existing separation and personal space steering to identify why close contacts persist (normalization removing magnitude, thresholds too small).
2. Strengthen separation by preserving magnitude information (clamped) so very close neighbors push harder than distant ones, without exceeding per-tick acceleration limits.
3. Bump default spacing-related config (min separation distance/weight, inter- and intra-group separation weights, personal space radius if needed) to enlarge no-overlap buffer.
4. Keep neighbor access via `SpatialGrid` only; avoid new allocations in the per-agent loop.
5. Validate via pytest and a short deterministic headless run that reports minimum inter-agent distance and ensures spacing improves while population/group metrics remain healthy.

## Concrete Steps

- Modify `src/terrarium/world.py` separation steering to return a clamped magnitude vector instead of always normalizing, so nearer agents exert stronger repulsion.
- Tune spacing defaults in `src/terrarium/config.py` (min separation distance/weight, separation weights; adjust personal space radius/weight if required).
- (Done) Add soft positional overlap correction using existing neighbor offsets before boundary reflection.
- (Manual sanity) Run a 600-tick headless sim and log the minimum neighbor distance observed; confirm it trends upward. PowerShell helper (needs about 12s, set timeout >= 20s):

    $code = @'
    import sys, math
    sys.path.insert(0, r"c:\\LifeOfPikarin")
    from terrarium.config import SimulationConfig
    from terrarium.world import World
    cfg = SimulationConfig()
    world = World(cfg)
    min_dist = 1e9
    for t in range(600):
        world.step(t)
        for agent in world.agents:
            neighbors = []
            offsets = []
            world._grid.collect_neighbors_precomputed(
                agent.position,
                world._vision_cell_offsets,
                world._vision_radius_sq,
                neighbors,
                offsets,
                exclude_id=agent.id,
            )
            for off in offsets:
                d2 = off.length_squared()
                if d2 > 1e-12:
                    md = math.sqrt(d2)
                    if md < min_dist:
                        min_dist = md
    print(f"min_distance={min_dist:.3f}")
    '@
    $p = Join-Path $env:TEMP "min_check.py"
    Set-Content -Path $p -Value $code -Encoding ascii
    python $p
    Remove-Item $p

Expected command transcript:
  - `pytest tests/python`

## Validation and Acceptance

- `pytest tests/python` passes.
- Manual 600-tick run (default seed) reports global `min_distance` around 0.038 and `last_tick_min_distance` around 0.42; target is last-tick >= 0.35 with visibly reduced cube overlap in the viewer.
- Performance sanity: average tick time in long-run tests should stay within existing targets (<=35ms for about 200 agents); no O(N^2) logic introduced.
- Stability: population remains within configured bounds, groups persist (5-10 after warmup), and determinism holds with fixed seed/timestep.
- Sim/View separation explicitly preserved: only simulation forces are changed, no viewer logic touched.

## Idempotence and Recovery

Changes are standard code edits; rerunning tests is safe. Git can revert specific files if tuning overshoots. No data migrations.

## Artifacts and Notes

- Key files: `src/terrarium/world.py`, `src/terrarium/config.py`.
- Keep new forces deterministic and bounded (clamp vectors, no random components).

## Interfaces and Dependencies

- Maintain existing public behavior of `World.step` and config dataclasses.
- Spatial grid remains the only neighbor source; no additional dependencies introduced.
