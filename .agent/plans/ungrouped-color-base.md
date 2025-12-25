# Fix viewer base color for ungrouped agents and hue rotation for groups

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

This plan is governed by `.agent/PLANS.md` and will be maintained accordingly.

## Purpose / Big Picture

The viewer will render ungrouped agents with a fixed base color of #FFF2AA and will derive all group hues by rotating from that base hue. The change should be visible immediately in the web viewer and preserve the simulation/view separation.

## Progress

- [x] (2025-09-27 03:05Z) Capture current color logic, tests, and documentation references.
- [x] (2025-09-27 03:08Z) Update color utilities and viewer shader inputs to use the new base hue and fixed ungrouped color.
- [x] (2025-09-27 03:11Z) Update tests and docs to match the new hue baseline.
- [x] (2025-09-27 03:18Z) Run required Python tests and JS tests; collect results.

## Surprises & Discoveries

- npm `test:js` failed because Node did not expand the `tests/js/**/*.js` glob; running `node --test tests/js/color.test.js` succeeded.

## Decision Log

- Decision: Use HSL(50°, 100%, 83%) as the base for ungrouped agents and offset group hues from that base.
  Rationale: Matches the requested #FFF2AA baseline while keeping group hues deterministic.
  Date/Author: 2025-09-27 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

The viewer color logic lives in `src/terrarium/app/static/color.js` and `src/terrarium/app/static/app.js`. `computeGroupHue` derives per-group hues and `computeColor` builds per-agent colors. JavaScript tests in `tests/js/color.test.js` validate `computeGroupHue`. Phase 2 viewer documentation references color handling in `docs/DESIGN_PHASE2.md` and `docs/DESIGN.md`.

Key constraints to restate here:

The simulation and visualization are strictly separated; view logic must not influence sim timing or behavior. Group interactions must not introduce O(N²) logic, and determinism must be preserved. Phase 2 viewer uses GPU instancing and avoids per-frame allocations beyond instanced buffers. Long-run stability and negative feedback loops remain in the simulation and must be untouched.

## Plan of Work

I will first update `computeGroupHue` in `src/terrarium/app/static/color.js` to anchor group hues to a 50° base hue and ensure ungrouped ids resolve to that base. Then I will adjust `computeColor` in `src/terrarium/app/static/app.js` to return a fixed HSL color for ungrouped agents and use the new hue baseline for grouped agents. Next, I will update `tests/js/color.test.js` to reflect the new hue calculation and adjust `docs/DESIGN_PHASE2.md` and `docs/DESIGN.md` to document the ungrouped base color and hue baseline. Finally, I will run the required Python setup/tests and JS tests to validate.

## Concrete Steps

Run commands from the repository root.

1) Inspect current color logic and tests.
   Expected: `computeGroupHue` is used in `app.js` and tested in `tests/js/color.test.js`.

2) Edit `src/terrarium/app/static/color.js` to introduce a base hue constant (50°) and make ungrouped ids return that base hue while grouped ids offset from it.

3) Edit `src/terrarium/app/static/app.js` to apply a fixed HSL color for ungrouped agents and keep grouped agents using the updated hue baseline.

4) Update `tests/js/color.test.js` expected values based on the new base hue logic.

5) Update `docs/DESIGN_PHASE2.md` and `docs/DESIGN.md` to mention the ungrouped fixed color and hue baseline.

6) Run required tests:
   - `python --version`
   - `pip install -r requirements.txt`
   - `pytest tests/python`
   - `npm run test:js`

## Validation and Acceptance

Validation includes a deterministic smoke run, visual sanity check, and performance check in accordance with repo expectations. The change must not alter simulation behavior.

Acceptance criteria:

Ungrouped agents render with a fixed #FFF2AA color and do not vary with energy or other traits. Grouped agents display hue-shifted colors derived from a 50° base hue while preserving existing lightness and saturation behaviors. The viewer continues to render smoothly with instanced meshes, and all required tests pass.

A manual visual check should confirm that ungrouped agents share the same pale yellow color and groups show distinct hue rotations relative to that base.

## Idempotence and Recovery

Edits are localized to viewer color utilities, tests, and documentation; reapplying changes is safe. If a mistake is found, revert the specific files or restore the previous `computeGroupHue` logic from version control.

## Artifacts and Notes

No artifacts yet.

## Interfaces and Dependencies

The change relies on `computeGroupHue` in `src/terrarium/app/static/color.js`, `computeColor` in `src/terrarium/app/static/app.js`, and JS tests in `tests/js/color.test.js`. The viewer uses Three.js and the instanced color buffer in `instancedBody.instanceColor` for per-agent coloring.
