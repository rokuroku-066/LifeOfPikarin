# Clamp diffusion fields to world bounds and keep pheromones finite

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

Ticks slow down as the simulation runs because the pheromone field grows without bound: diffusion walks off the world edges and never decays, so the dictionary size and per-tick work rise steadily. The goal is to keep diffusion fields bounded to the world area and ensure pheromone trails fade, restoring stable per-tick cost while preserving determinism and long-run stability (population feedbacks stay intact).

## Progress

- [x] (2025-12-13 10:20Z) Reproduced slowdown; pheromone keys grew from 0 → ~7k by tick 3000 with default config.
- [x] (2025-12-13 10:40Z) Implement field key clamping and pheromone decay to bound growth.
- [x] (2025-12-13 10:50Z) Add regression tests for bounded diffusion/decay.
- [x] (2025-12-13 11:05Z) Run `pytest tests/python` and headless smoke (`--steps 3000`) to confirm tick time stays flat.
- [x] (2025-12-13 11:15Z) Update README/DESIGN notes if config defaults change; record outcomes.

## Surprises & Discoveries

- Pheromone field size increased to 7017 keys by tick 3000 with default settings (world size 100, cell 2.5, pheromone decay 0), far exceeding the 1600 in-world cells and correlating with tick duration climbing to ~80 ms.
- `src/terrarium/config.py` contained null/garbled bytes and fields packed onto single commented lines, which stripped most dataclass attributes at runtime. Rewrote it in plain UTF-8 with explicit per-field lines while keeping the same defaults (plus the new pheromone decay).
- With population capped at 500 and initial 120, pheromone keys used to climb past 15k and tick_ms past 100 ms; after pruning to active groups they plateaued ~2.5–3k keys and tick_ms stayed ~40 ms.

## Decision Log

- Decision: Bound diffusion steps to the world grid and introduce a small default pheromone decay so old group trails evaporate instead of accumulating forever.  
  Rationale: Keeps per-tick work proportional to in-world cells and active groups; prevents unbounded dict growth without changing Sim/View separation or locality guarantees.  
  Date/Author: 2025-12-13 / Codex
- Decision: Prune pheromone layers for groups no longer present (including pending births) before diffusion each tick.  
  Rationale: Active group count is small even at max population; dropping stale group layers caps key count and stabilizes tick time.  
  Date/Author: 2025-12-13 / Codex

## Outcomes & Retrospective

- Headless default config (initial 10, max 200): tick_duration_ms held ~25–40 ms through 3000 steps; pheromone keys plateaued ~2.5k despite ~20 active groups.  
- Heavy run (initial 120, max 500) logged to `artifacts/metrics_after_heavy.csv`: tick_ms checkpoints [0: 5.7 ms, 1000: 17.1 ms, 2000: 40.6 ms, 2999: 40.8 ms], max tick_ms 52.8; pheromone keys capped ~3k (down from ~16k before pruning).  
- Pytest suite passes (17/17). Docs updated to note clamped diffusion and non-zero default pheromone decay.

## Context and Orientation

- Relevant files: `src/terrarium/environment.py` (diffusion and decay for food/danger/pheromone), `src/terrarium/config.py` (default decay rates), `tests/python/test_world.py` (simulation determinism), potential new test file for environment diffusion.
- Current behavior: `_diffuse_field` uses `_add_key` that can step outside world bounds and has zero decay for pheromones by default, so keys and work grow each tick.
- Constraints to honor (from AGENTS.md): Sim and View stay separated; no O(N²) (SpatialGrid remains the locality mechanism); maintain negative feedbacks for population stability; determinism with fixed timestep and seed.

## Plan of Work

1) Environment diffusion safety: modify `_add_key` in `environment.py` to clamp the first two coordinates to `[0, max_index-1]` so diffusion cannot generate off-world keys for food/danger/pheromone.  
2) Pheromone finiteness: set a small positive default `pheromone_decay_rate` in `EnvironmentConfig` and ensure `_diffuse_field` still prunes near-zero entries, so trails fade without exploding key count even with many groups.  
3) Tests: add a regression that deposits pheromone near a corner, ticks the field, and asserts keys stay within bounds and shrink to zero over time with decay > 0.  
4) Docs: note the new decay default and bounded diffusion in README (and/or DESIGN) so operators know why trails fade and how to configure it.  
5) Validation: run `pytest tests/python`; run headless `python -m terrarium.headless --steps 3000 --seed 42 --initial 120 --max 500 --log artifacts/metrics_after.csv` and confirm tick times plateau and pheromone keys ≤ in-world cell count per active group.

## Concrete Steps

- Workspace root; ensure venv is active: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- Implement code changes in `src/terrarium/environment.py` and `src/terrarium/config.py`.
- Add/adjust tests under `tests/python/` (new file if needed).
- Run: `.\.venv\Scripts\python.exe -m pytest tests/python`
- Run headless smoke: `.\.venv\Scripts\python.exe -m terrarium.headless --steps 3000 --seed 42 --initial 120 --max 500 --log artifacts/metrics_after.csv`

Expected transcripts: pytest passes; headless CSV shows `tick_ms` not rising monotonically past ~25 ms at tick 3000 and neighbor_checks stable (~1500) with bounded pheromone keys.

## Validation and Acceptance

- Deterministic smoke: the headless run above completes without tick time blow-up; repeated runs with same seed yield similar metrics.  
- Performance sanity: with ~300 agents at steady state, `tick_duration_ms` remains roughly flat (no steady upward drift) across ticks 0–3000.  
- Field bounds: inspecting the environment after the run shows `len(_pheromone_field) <= max_index**2 * active_groups` and no negative/out-of-range cell indices.  
- Stability: population respects `max_population`, and negative feedbacks remain (birth/death balance unchanged).  
- Sim/View separation: only Sim touched; View unchanged.

## Idempotence and Recovery

- Changes are confined to Python code and tests; rerunning the plan is safe after reverting or applying patches.  
- If decay feels too aggressive, adjusting `pheromone_decay_rate` in config is deterministic and bounded by the same clamping logic.  
- If pytest/headless fails, revert the code edits and re-run to return to prior behavior.

## Artifacts and Notes

- Baseline observation: pheromone keys 0→7017 by tick 3000; tick_ms climbed to ~80 ms with config defaults.  
- Post-change we will capture `artifacts/metrics_after.csv` for comparison.

## Interfaces and Dependencies

- Environment diffusion helpers remain internal; public touch points are `EnvironmentConfig.pheromone_decay_rate` and `EnvironmentGrid.tick/add_pheromone`.  
- No new external dependencies; relies on existing `pygame.Vector2` and dataclasses.  
- SpatialGrid and World APIs remain unchanged to preserve O(N) per-agent locality.
