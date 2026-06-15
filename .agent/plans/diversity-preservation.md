# Preserve agent and group diversity without losing flock identity

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows `.agent/PLANS.md` from the repository root.

## Purpose / Big Picture

The current simulation can visually and genetically collapse toward similar agents because initial appearance values are identical, pair inheritance uses only parent averages plus small symmetric mutation, and social groups have no persistent visual signature beyond a weak sign-based hue bias. After this change, new worlds start with visible individual variation, child traits retain more parent-side variation instead of always shrinking toward the mean, and every group receives a deterministic appearance anchor so group members drift toward a recognizable local palette while the whole terrarium remains diverse.

The observable result is that the viewer receives varied `appearance_h`, `appearance_s`, and `appearance_l` values from the simulation snapshot. Agents in the same group should look related, but different groups should not all converge to the same yellow body color.

## Progress

- [x] (2026-06-15 00:00Z) Read repository instructions, design docs, current world/lifecycle/group implementation, and relevant tests.
- [x] (2026-06-15 00:05Z) Identify the three convergence causes: bootstrap appearance uses one constant HSL value, pair inheritance averages every trait and HSL component, and group hue bias is only a small plus/minus sign with no persistent group palette.
- [x] (2026-06-15 00:10Z) Draft this ExecPlan before implementation because the task changes simulation rules, tests, and docs.
- [x] (2026-06-15 00:30Z) Implement deterministic initial appearance sampling, trait inheritance segregation/jitter, and group hue anchors.
- [x] (2026-06-15 00:40Z) Add tests for bootstrap appearance diversity, group hue anchors, trait variance preservation, and determinism.
- [x] (2026-06-15 00:45Z) Update design documentation and README notes.
- [x] (2026-06-15 00:50Z) Run required Python tests and deterministic headless smoke check.

## Surprises & Discoveries

The initial traits were already sampled deterministically from clamp ranges, so the “initial values are the same” problem is primarily visible appearance rather than all inherited traits. The existing group hue bias used `world._group_wind_sign`, which can only push hue in two directions and cannot create many persistent group palettes.

## Decision Log

- Decision: Keep all diversity logic inside the simulation core and continue sending only snapshot fields to the viewer.
  Rationale: This preserves Sim/View separation; the View remains a renderer of genetic appearance values rather than a driver of simulation state.
  Date/Author: 2026-06-15 / Codex.

- Decision: Use deterministic, config-driven appearance sampling at bootstrap and deterministic group hue anchors derived from group id.
  Rationale: This gives reproducible diversity without adding nondeterministic sources or global all-pairs analysis.
  Date/Author: 2026-06-15 / Codex.

- Decision: Replace pure trait averaging with per-trait Mendelian-style segregation around the mid-parent value, followed by existing mutation and clamps.
  Rationale: Parent averages halve variance every generation; choosing a deterministic side of the parent interval plus bounded jitter preserves family similarity while avoiding collapse.
  Date/Author: 2026-06-15 / Codex.

## Outcomes & Retrospective

The implemented change should make initial snapshots visibly varied, keep families coherent through inherited values, and make groups visually legible through group anchors. The change does not add O(N²) loops, does not let the View affect the Sim, and keeps existing density/resource negative feedback untouched.

## Context and Orientation

The simulation core lives under `src/terrarium/sim`. `src/terrarium/sim/core/world.py` owns bootstrap, inheritance helpers, snapshot serialization, and deterministic RNG streams. `src/terrarium/sim/core/config.py` defines config dataclasses. `src/terrarium/sim/systems/groups.py` registers group bases and updates group membership. `src/terrarium/sim/systems/lifecycle.py` calls the inheritance helpers when a child is born. The browser viewer reads `appearance_h`, `appearance_s`, and `appearance_l` from snapshots; it must not compute or feed back simulation genetics.

A group anchor means a deterministic hue target associated with a social group id. It is not a new population control rule. It only biases inherited appearance so same-group children share a palette.

Repository constraints restated: Simulation and Visualization are strictly separated; View never drives Sim. No O(N²) all-pairs logic is allowed; neighbor interactions continue to use `SpatialGrid`. Long-run stability remains handled by density stress, disease, food/energy, reproduction suppression, and death hazards. Determinism matters: all new randomness must come from existing deterministic RNG streams or stable hashes. Phase 2 viewer constraints remain unchanged; body color is still derived from snapshot appearance and rendered with instancing.

## Plan of Work

First, add appearance diversity configuration fields in `AppearanceConfig`: initial hue/saturation/lightness jitter and group anchor strength. Add evolution inheritance fields in `EvolutionConfig` to control trait segregation and drift.

Second, update `World` to maintain `_group_appearance_hues`, clear it on reset, create a group anchor when `groups.register_group_base` is called, and expose helper methods used by group code. Bootstrap agents will call a new `_sample_initial_appearance` helper using `_appearance_rng`, rather than assigning the same base HSL to everyone.

Third, update `_inherit_traits_pair` so each trait starts from the mid-parent value plus a bounded random offset within the parent interval. This retains family coherence because values remain between or near the parents before mutation, and it retains global diversity because repeated averaging no longer collapses variance as aggressively. Existing mutation and clamp logic remains the final step.

Fourth, update `_inherit_appearance_pair_with_group` and `_inherit_appearance` so inherited hue is pulled partly toward a group anchor when a valid group exists. The pull is configurable and modest so same-group members cohere without making every member identical. Unaffiliated agents continue using parent inheritance plus mutation.

Fifth, add Python tests for deterministic initial appearance variation, deterministic group anchor creation, and trait variance preservation. Update docs to describe the new diversity mechanism and validation commands.

## Concrete Steps

Run from `/workspace/LifeOfPikarin`:

    python --version
    pip install -r requirements.txt
    pytest tests/python

After edits, repeat:

    pytest tests/python
    python -m terrarium.app.headless --steps 500 --seed 42 --log tests/artifacts/diversity_metrics.csv --log-format detailed --summary tests/artifacts/diversity_summary.json

Expected test transcript includes all Python tests passing. Expected headless behavior is a finite population, nonzero or stable metrics fields, bounded tick times, and no crashes.

## Validation and Acceptance

Acceptance is met when a seeded initial world has multiple distinct appearance hues in the first snapshot, when repeated child trait inheritance between dissimilar parents produces more than a single mid-point value while staying inside clamps, and when group children are biased toward a deterministic group palette. A deterministic smoke run with seed 42 for 500 steps must finish and produce a summary JSON.

Performance sanity check: with the default maximum population of 700, no new per-agent all-pairs logic is introduced. Tick time is measured by `TickMetrics.tick_time_ms` in the headless detailed log.

Long-run stability check: the existing resource, density, energy, disease, reproduction, and hazard feedback loops remain in lifecycle code. Observe headless logs for population not instantly exploding above `max_population` and not crashing to invalid values.

No O(N²) note: group anchors are looked up by group id in dictionaries, and inheritance uses only the two parents. Neighbor discovery remains in `SpatialGrid.collect_neighbors_precomputed`.

Sim/View separation note: the simulation writes appearance values into snapshots; the View only consumes those values for instanced rendering.

Visual sanity check recipe: if a browser is available, run `uvicorn terrarium.app.server:app --reload --port 8000`, open `http://localhost:8000`, and observe that Pikarin bodies show individual color variety while nearby group members share related palettes.

## Idempotence and Recovery

The test and headless commands are safe to repeat. If tests fail after code changes, use `git diff` to inspect the failing area and rerun only the relevant test before the full suite. If the new behavior destabilizes population, reduce only diversity-specific config strengths first; do not disable density or energy feedback loops.

## Artifacts and Notes

Important expected code locations:

    src/terrarium/sim/core/config.py       new config knobs
    src/terrarium/sim/core/world.py        bootstrap, inheritance, group anchors
    src/terrarium/sim/systems/groups.py    group anchor registration hook
    tests/python/test_world.py             deterministic diversity tests
    docs/DESIGN.md and README.md           behavior documentation

## Interfaces and Dependencies

The final code must provide `World._sample_initial_appearance`, `World._ensure_group_appearance_anchor`, and `World._group_appearance_hue` helpers. Config loading must continue to accept YAML through `load_config`, with default values keeping existing setups valid. No new third-party libraries are required.
