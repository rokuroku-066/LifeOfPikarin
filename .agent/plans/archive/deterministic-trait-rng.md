# Add deterministic trait RNG stream for bootstrap traits

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

This plan follows `.agent/PLANS.md` and must be maintained accordingly.

## Purpose / Big Picture

The goal is to make initial AgentTraits randomized in a deterministic, reproducible way without altering the main RNG stream that drives simulation rules. This provides reproducible variation in bootstrap traits while keeping existing deterministic sequences intact. Users should be able to see consistent initial trait variation across runs with the same seed.

## Progress

- [x] (2025-09-26 09:45Z) Inspect current trait bootstrap and RNG usage in the simulation core.
- [x] (2025-09-26 09:47Z) Implement a dedicated deterministic trait RNG stream and sampling helper for bootstrap traits in `src/terrarium/sim/core/world.py`.
- [x] (2025-09-26 09:49Z) Update tests to lock the trait RNG stream expectations in `tests/python/test_world.py`.
- [x] (2025-09-26 09:50Z) Update documentation to note deterministic randomized initial traits in `docs/DESIGN.md`.
- [x] (2025-09-26 09:54Z) Run required Python version check, dependency install, and `pytest tests/python`.

## Surprises & Discoveries

None so far.

## Decision Log

- Decision: Use a separate RNG stream salted from the world seed to avoid perturbing the main RNG sequence.
  Rationale: Keeps core simulation determinism intact while enabling random-but-reproducible initial traits.
  Date/Author: 2025-09-26 / Codex

## Outcomes & Retrospective

Bootstrap traits now use a dedicated deterministic RNG stream, tests lock the expected sampling sequence, and documentation calls out the randomized-but-reproducible initialization.

## Context and Orientation

The simulation core lives under `src/terrarium/sim/core/`. The `World` class in `src/terrarium/sim/core/world.py` owns RNG state and bootstraps the initial population in `_bootstrap_population`. `AgentTraits` is defined in `src/terrarium/sim/core/agent.py`. Tests for world behavior live in `tests/python/test_world.py`. Design documentation is in `docs/DESIGN.md`.

Determinism is critical: the simulation must be seedable and reproducible with fixed timesteps. View code must never drive simulation, and no O(N^2) logic should be introduced. Long-run stability mechanisms must remain intact. We will only adjust bootstrap traits and the RNG used for them.

## Plan of Work

We will add a dedicated trait RNG stream in `World`, seeded from the world seed with a fixed salt, and a helper `_sample_initial_traits()` that samples each trait from its clamp range using that RNG. `_bootstrap_population` will use this helper so initial traits are randomized but deterministic and do not consume from the main RNG. Tests in `tests/python/test_world.py` will be extended to assert the trait sampling sequence. `docs/DESIGN.md` will be updated to describe deterministic randomized initial traits.

## Concrete Steps

Run commands from the repository root:

    python --version
    pip install -r requirements.txt
    pytest tests/python

These commands should complete successfully. If the environment blocks them, capture the error and document it in the commit and PR description.

## Validation and Acceptance

Deterministic smoke run: create a world with a fixed seed and bootstrap population, then assert the initial traits match a fixed, expected sequence and remain within clamp ranges. Expect tests to pass with the new trait RNG stream.

Visual sanity check: not required for this change because it is simulation-only; no viewer updates are expected.

Performance sanity check: ensure no per-agent O(N^2) logic is introduced; the trait sampling is per-agent and constant-time. Measure no change in tick time for typical N (e.g., 200 agents) if run manually.

Long-run stability check: unchanged; existing negative feedback loops remain intact. Confirm by running the existing tests and ensuring no new dynamics are introduced.

No O(N^2) note: trait sampling occurs per agent during bootstrap only; no neighbor scanning is involved. SpatialGrid usage is unchanged.

Sim/View separation note: the change is limited to simulation initialization and does not affect rendering or data flow.

## Idempotence and Recovery

The changes are safe to reapply. If needed, revert the commit to restore the previous deterministic behavior.

## Artifacts and Notes

No artifacts yet.

## Interfaces and Dependencies

`World` will expose a private `_trait_rng` seeded from the world seed and `_TRAIT_RNG_SALT` constant. `_sample_initial_traits()` will return an `AgentTraits` instance with fields sampled from the clamp ranges. Tests in `tests/python/test_world.py` will validate trait sampling against the trait RNG stream. No new external dependencies are introduced.
