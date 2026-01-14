# Add per-agent genetic appearance colors

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is stored at `.agent/plans/appearance-genetics.md` and must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

This change makes agent body colors derive from per-agent genetic appearance values in the simulation rather than group-derived colors. View-side color will read appearance values from snapshots and apply existing energy/pulse/speed modifiers without affecting simulation behavior. The user-visible result is that colors slowly diversify via birth-time mutation while the simulation remains deterministic and stable.

## Progress

- [x] (2025-12-25 06:43Z) Draft ExecPlan with scope, validation, and steps.
- [x] (2025-12-25 06:43Z) Inspect current sim, snapshot, and viewer color pipeline to locate touch points.
- [x] (2025-12-25 06:43Z) Implement appearance genetics in simulation data (agent/world/lifecycle/config) and snapshot output.
- [x] (2025-12-25 06:43Z) Update viewer color logic to use appearance fields.
- [x] (2025-12-25 06:46Z) Update tests and docs, then run required test commands.
- [ ] (2025-12-25 06:46Z) Capture manual verification notes for sim determinism and viewer sanity checks.

## Surprises & Discoveries

None yet.

## Decision Log

- Decision: Keep appearance mutation confined to birth events and use a dedicated deterministic RNG stream derived from the world seed.
  Rationale: Preserves Phase 1 determinism and avoids shifting RNG consumption in existing systems.
  Date/Author: 2025-02-14 / Codex

## Outcomes & Retrospective

Pending.

## Context and Orientation

The simulation core lives under `src/terrarium/` and emits agent snapshots consumed by the static web viewer under `static/` or `src/terrarium/static`. Agent state is defined in `src/terrarium/agent.py`, lifecycle and reproduction in `src/terrarium/lifecycle.py`, and world state plus snapshot generation in `src/terrarium/world.py`. Viewer color is computed in the frontend script `src/terrarium/static/app.js` (or similar) where instanced mesh colors are derived from snapshot data. Configuration defaults live in `src/terrarium/config.py`.

Appearance genetics means adding per-agent HSL fields in the sim, copying them on birth, optionally mutating them with a dedicated RNG stream, and sending them through snapshots to the viewer. The viewer must only read these values, preserving Sim/View separation and determinism.

## Plan of Work

Implement new appearance fields on the agent model with defaults, wire an appearance RNG on the world object (seeded from the primary seed plus a constant salt), and apply inheritance/mutation rules during reproduction in lifecycle code. Extend snapshot generation to include appearance values and update the viewer color computation to use them as the base hue/saturation/lightness while retaining existing energy/pulse/speed adjustments. Add configuration parameters for mutation chance and delta magnitude. Update tests to cover deterministic appearance inheritance/mutation and snapshot fields, and update Phase 2 design docs to describe genetic coloring.

## Concrete Steps

Run commands from the repository root.

1) Inspect relevant files.

    rg "computeColor|appearance|snapshot|Agent" src/terrarium
    rg "color" src/terrarium/static

2) Implement simulation changes.

    - Edit `src/terrarium/agent.py` to add `appearance_h`, `appearance_s`, `appearance_l` fields with default values.
    - Edit `src/terrarium/config.py` to add appearance mutation config values.
    - Edit `src/terrarium/world.py` to add `_appearance_rng` with a derived seed and include appearance fields in `_agent_snapshot()`.
    - Edit `src/terrarium/lifecycle.py` to copy parent appearance on birth and apply mutation using `_appearance_rng` at birth only.

3) Update viewer and docs.

    - Edit `src/terrarium/static/app.js` (or current viewer entry) to compute base color from appearance values.
    - Edit `docs/DESIGN_PHASE2.md` to note genetic coloring pipeline.

4) Update tests.

    - Update/add tests in `tests/python` to confirm appearance fields in snapshots and deterministic mutation.
    - Update/add JS tests (e.g., `tests/js/color.test.js`) to ensure computeColor uses appearance.

5) Run required validation.

    pip install -r requirements.txt
    pytest tests/python
    (Add any JS test command once discovered.)

Expected outputs include pytest passing and deterministic logs for appearance fields in snapshots.

## Validation and Acceptance

Deterministic smoke run: run a fixed-seed simulation for N steps and log a small sample of agent appearance HSL values to confirm they remain stable across runs and only change at births. Expect identical outputs across multiple runs with the same seed.

Visual sanity check: run the viewer and confirm that body colors vary by agent according to appearance, while energy/pulse/speed adjustments still apply. The fixed oblique camera should show a stable scene with smooth motion and varied colors.

Performance sanity: verify tick time and neighbor checks remain consistent with baseline for a typical population size (e.g., 200 agents) and that no all-pairs behavior appears. This can be done by existing performance counters or logs.

Long-run stability: observe population metrics over an extended run to ensure feedback loops still prevent runaway growth or extinction. Appearance changes should not affect these metrics.

No O(N^2) note: ensure any appearance logic is per-agent at birth only and does not add pairwise scans.

Sim/View separation: ensure appearance is computed in Sim and only read by View via snapshots.

## Idempotence and Recovery

All changes are deterministic and can be re-applied safely. If tests fail after changes, revert modified files or reset the branch to HEAD, then re-apply step-by-step.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

Simulation:
- `src/terrarium/agent.py`: Agent appearance fields.
- `src/terrarium/world.py`: `_appearance_rng`, `_agent_snapshot()` emits appearance.
- `src/terrarium/lifecycle.py`: birth inheritance/mutation.
- `src/terrarium/config.py`: appearance mutation parameters.

Viewer:
- `src/terrarium/static/app.js`: computeColor uses appearance HSL.

Docs/Tests:
- `docs/DESIGN_PHASE2.md` update.
- `tests/python/*` for appearance and determinism.
- `tests/js/*` for color calculation.
