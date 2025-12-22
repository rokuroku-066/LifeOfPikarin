# Food-limited population waves (no global population pressure)

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

Make population dynamics primarily constrained by food availability (including deterministic “climate” regen noise), without relying on a global population death-pressure term. The visible outcome is that headless metrics show population rising/falling in response to food supply and local density feedback, rather than sticking to a hard ceiling.

## Progress

- [x] (2025-12-18 08:00Z) Baseline run showed runaway without constraints (too many agents -> slow ticks).
- [x] (2025-12-18 09:00Z) Removed global population pressure and disabled free group-food spawning.
- [x] (2025-12-18 10:00Z) Iterated config via repeated headless smoke runs until population is food-limited without exploding/extincting.
- [x] (2025-12-18 10:10Z) Added a configurable reproduction base chance to tune birth “burstiness” under scarcity.
- [x] (2025-12-18 10:15Z) Ran unit tests (`pytest tests/python`).

## Surprises & Discoveries

- Disabling global population pressure alone caused runaway growth; “free energy” sources (notably group-food spawning) can dominate and mask true food scarcity.
- Aggressive climate noise amplitude (allowing regen multiplier to reach ~0) can push the system toward extinction if baseline food supply is not high enough.
- Some artifact CSVs can be locked by external processes; use unique filenames during tuning and clean up before committing.

## Decision Log

- Decision: Set `global_population_pressure_slope=0.0`.
  Rationale: Remove explicit global cap; carrying capacity should emerge from resources and local density feedback.
  Date/Author: 2025-12-18 / Codex
- Decision: Set `group_food_spawn_chance=0.0`.
  Rationale: Group-food spawning injects energy and makes “food scarcity” tuning ambiguous.
  Date/Author: 2025-12-18 / Codex
- Decision: Add `FeedbackConfig.reproduction_base_chance` and read it in `World._apply_life_cycle`.
  Rationale: With scarcity, births can become too bursty; a dedicated knob is safer than reintroducing global pressure.
  Date/Author: 2025-12-18 / Codex
- Decision: Cap groups via `max_groups=20` and `post_peak_max_groups=20`.
  Rationale: Keep group count within the intended long-run band during tuning.
  Date/Author: 2025-12-18 / Codex

## Outcomes & Retrospective

The defaults now remove global population pressure and make food availability the primary limiter. A deterministic headless smoke run (`python -m terrarium.headless --steps 5000 --seed 42 --log <csv>`) shows population waves and avoids runaway-to-thousands behavior, while staying within reasonable tick time.

Remaining trade-off: Because food regen noise is stochastic (but seed-deterministic), some seeds can produce longer “drought” stretches; tuning should be verified on a small set of seeds if this becomes a concern.

## Context and Orientation

Repository constraints (must remain true):
- Simulation vs View separation is strict; rendering does not control simulation.
- No O(N²) all-pairs logic; neighbors must be queried via the spatial grid.
- Long-run stability must include negative feedback loops; avoid runaway growth and avoid extinction as the only attractor.
- Determinism matters: seedable, fixed timestep schedule, reproducible.

Key files:
- `src/terrarium/config.py`: all default knobs for environment + feedback loops.
- `src/terrarium/world.py`: simulation stepper; applies food regen multiplier and handles births/deaths.
- `src/terrarium/headless.py`: deterministic smoke runner and CSV logging.

## Plan of Work

1) Establish baseline by running a headless simulation and inspecting population, births/deaths, and tick time.
2) Remove global population pressure and ensure no free-energy source dominates the budget.
3) Tune food supply (max per cell, regen per second, death recycling, diffusion) plus climate noise (amplitude/interval/smoothing).
4) If births become too bursty, tune the base reproduction chance rather than adding global population pressure.
5) Keep group counts bounded with `max_groups` so long-run behavior stays legible.
6) Run `pytest tests/python` after changes.

## Concrete Steps

- Smoke run:
  - `python -m terrarium.headless --steps 5000 --seed 42 --log artifacts/metrics_smoke.csv`
- Quick stats:
  - `python -c "import csv,statistics; rows=list(csv.DictReader(open('artifacts/metrics_smoke.csv'))); p=[int(r['population']) for r in rows]; print('min',min(p),'max',max(p),'avg',round(statistics.mean(p),2),'final',p[-1])"`
- Unit tests (required):
  - `pytest tests/python`

## Validation and Acceptance

Acceptance is behavioral:
- Population is not pinned to a hard global pressure “ceiling”; it responds to food supply/noise.
- Over 5k ticks (seeded), population does not explode to thousands and does not collapse to extinction.
- Tick time remains within Phase 1 expectations (spot-check `tick_ms` in the smoke CSV).
- No changes violate Sim/View separation or introduce O(N²) behavior.

## Idempotence and Recovery

- Headless runs are deterministic per seed and can be rerun safely; output CSVs can be overwritten.
- If tuning destabilizes, revert `src/terrarium/config.py` and rerun the smoke recipe to confirm recovery.

## Interfaces and Dependencies

- Public API remains the same; one new config field exists: `FeedbackConfig.reproduction_base_chance`.
- `World` uses that field when computing reproduction probability.
