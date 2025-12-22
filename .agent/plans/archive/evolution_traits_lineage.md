# Introduce deterministic lineage traits and evolution hooks

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Introduce heritable agent traits and lineage identifiers without breaking determinism or existing behavior when evolution is disabled. The simulation should allow small, clamped mutations at birth under deterministic RNG, expose lineage and representative traits to snapshots/viewer for visualization, and ensure validation covers trait bounds and deterministic reproducibility with evolution toggled on or off.

## Progress

- [x] (2024-06-04 00:00Z) Drafted initial plan and gathered code context.
- [x] (2024-06-04 01:20Z) Implemented lineage/trait propagation, viewer tinting, docs/tests updates; validated with `pytest tests/python`.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Model traits as speed/metabolism/disease_resistance/fertility multipliers with clamp ranges and default 1.0, mutating only when evolution is enabled to preserve baseline determinism.
  Rationale: Keeps prior behavior unchanged when disabled while enabling balanced tradeoffs (speed costs metabolism; resistance dampens reproduction).
  Date/Author: 2024-06-04 / Codex
- Decision: Use lineage_id to seed color hue offsets and trait_speed to modulate saturation/lightness in the viewer without affecting simulation timing.
  Rationale: Makes evolutionary drift visible while keeping Sim→View one-way and deterministic.
  Date/Author: 2024-06-04 / Codex

## Outcomes & Retrospective

Evolution features implemented with deterministic toggling, viewer cues added, and pytest suite passing. Long-run/headless validation remains to be exercised manually by users as needed.

## Context and Orientation

Key files:
- `src/terrarium/agent.py`: simple Agent dataclass with id, generation, group_id, position/velocity, energy, age, state, and group-related timers. No genetic traits yet.
- `src/terrarium/config.py`: defines SimulationConfig with species/environment/feedback sections; no evolution config or trait defaults.
- `src/terrarium/world.py`: handles simulation loop, life cycle, reproduction, and snapshots. Child agents inherit group via `_mutate_group`, and `_agent_snapshot` outputs species_id=0 and appearance_seed=id; metabolism uses speed and energy terms only; disease probability based on neighbor count; movement capped by species.base_speed.
- `src/terrarium/static/app.js` and `static/color.js`: viewer color/scale logic keyed on group hue, energy, age, reproduction desire; no trait-based coloring.
- Tests live under `tests/python`; current deterministic coverage expects identical sequences for fixed seeds.

Repository constraints to honor (repeated from `.agent/PLANS.md` and root AGENTS):
- Simulation/View separation: world produces snapshots; viewer consumes only. No coupling from view to sim.
- No O(N²): neighbor interactions use `SpatialGrid`; keep any trait effects local without all-pairs scans.
- Long-run stability: maintain negative feedback (metabolism, density, disease); trait benefits must have costs.
- Determinism: seedable fixed timestep; evolution must use DeterministicRng only and preserve RNG consumption when disabled.
- Phase 1 visuals: cube instancing only; no per-agent GameObjects.

## Plan of Work

Describe edits in sequence:
1. **Agent traits data model** (`src/terrarium/agent.py`): add `AgentTraits` dataclass with bounded fields (e.g., speed_multiplier, metabolism_multiplier, disease_resistance, reproduction_penalty_factor) and defaults. Add `lineage_id` and `traits` (default_factory) to Agent, ensuring backward-compatible defaults for existing tests.
2. **Config extension** (`src/terrarium/config.py`): introduce `EvolutionConfig` with `enabled` (default False) plus parameters such as `mutation_strength`, `clamp` bounds per trait, `lineage_mutation_chance`, and per-trait mutation weights. Extend `SimulationConfig` to include evolution, ensure `load_config` reads `raw.get("evolution", {})` but when disabled, preserves prior RNG consumption behavior (no additional draws).
3. **World reproduction hooks** (`src/terrarium/world.py`):
   - During bootstrap and reproduction, assign lineage_id (initial unique per agent or seeded constant) and traits with defaults.
   - On child creation, if evolution disabled, inherit parent traits/lineage with zero RNG drift; if enabled, use DeterministicRng to mutate traits with small noise scaled by `mutation_strength`, clamp to config bounds, and probabilistically start a new lineage using `lineage_mutation_chance`. Keep RNG sequence identical to previous behavior when disabled.
   - Update metabolism calculation to include trait tradeoffs: speed multiplier increases metabolism; disease resistance reduces disease probability but increases reproduction cost/threshold; ensure traits interact to avoid runaway speed/immortality (e.g., higher speed raises metabolism and hazard or lowers reproduction chance).
   - Adjust max velocity cap using speed trait; integrate trait modifiers into disease probability and reproduction probability with balancing penalties.
4. **Snapshots and viewer** (`src/terrarium/world.py`, `src/terrarium/static/app.js`): modify `_agent_snapshot` to expose `lineage_id`, representative trait(s) (e.g., speed), and generation; replace `species_id` with lineage_id and keep `appearance_seed` stable. In viewer, adjust color mapping to include trait_speed as saturation/lightness influence while retaining group hue basis.
5. **Tests** (`tests/python`): add deterministic tests for evolution enabled/disabled ensuring same sequence for fixed seeds; add trait clamp test verifying mutations stay within bounds and tradeoffs affect metabolism/reproduction deterministically. Update existing snapshot expectations if needed.
6. **Docs/validation notes** (`docs` if necessary or inline comments): update configuration docs to mention EvolutionConfig and validation steps.

## Concrete Steps

- Environment: ensure Python 3.11+ (`python --version`).
- Install dependencies: `pip install -r requirements.txt`.
- Implement code changes per plan sections above.
- Run full test suite: `pytest tests/python`.
- If viewer changes are made, optionally run headless snapshot script (`python -m src.terrarium.headless --ticks 5`) to ensure no runtime errors; document if cannot run.

## Validation and Acceptance

- Deterministic smoke: run `pytest tests/python` with evolution disabled (default) and verify deterministic seed tests unchanged.
- New deterministic coverage: add/execute tests that run world for fixed ticks with evolution enabled and assert identical metrics/trait sequences for fixed seed and config.
- Trait bounds: tests confirm all trait values within configured clamp range after multiple births.
- Stability/performance sanity: note that neighbor interactions remain spatial-grid based; no O(N²) loops introduced. Expect similar tick duration for ~200 agents; verify no per-tick allocations in hot loops.
- Visual sanity (if possible): run viewer/headless to confirm snapshots contain lineage_id/trait_speed and colors vary subtly; ensure sim not driven by view.

## Idempotence and Recovery

- Applying plan is repeatable; resetting git working tree restores prior state.
- RNG determinism preserved by conditioning mutation logic on `evolution.enabled`; if issues arise, disable evolution to recover baseline behavior.

## Artifacts and Notes

To be populated with key transcripts (test runs) and notable diffs as work proceeds.

## Interfaces and Dependencies

- New `EvolutionConfig` in `src/terrarium/config.py` with fields: `enabled`, `mutation_strength`, `lineage_mutation_chance`, `clamp` bounds per trait, and mutation weights.
- `AgentTraits` in `src/terrarium/agent.py` with default factory; Agent gains `lineage_id` and `traits`.
- `World` uses `DeterministicRng` for mutations and lineage generation; reproduction logic respects evolution config.
- Snapshots include `lineage_id`, `generation`, and `trait_speed` (or similar) for viewer; viewer color logic reads these fields without influencing simulation.
