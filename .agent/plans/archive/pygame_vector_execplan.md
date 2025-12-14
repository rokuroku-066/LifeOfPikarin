# Replace custom Vec2 with pygame.math.Vector2

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

This plan follows `.agent/PLANS.md` and must restate the simulation constraints: the simulation and visualization remain separated; no O(N²) all-pairs logic (neighbor interactions stay constrained to the SpatialGrid); long-run stability depends on negative feedback loops; determinism requires seedable, fixed-timestep processing; Phase 1 uses cube instancing and avoids per-agent GameObjects.

## Purpose / Big Picture

We will remove the custom `terrarium.vector.Vec2` implementation and switch the simulation to use `pygame.math.Vector2` directly. This simplifies maintenance by relying on a battle-tested vector class while keeping simulation behavior deterministic and efficient. Users should be able to run the Python simulation and tests with pygame installed and observe identical agent motion and neighbor queries using the standard vector type.

## Progress

- [x] (2024-05-19 00:00Z) Drafted initial ExecPlan before edits.
- [x] (2024-05-19 00:30Z) Implemented pygame Vector2 replacement across simulation modules and tests.
- [x] (2024-05-19 00:35Z) Ran validation (`pytest tests/python`) after installing pygame dependency.

## Surprises & Discoveries

- None yet.

## Decision Log

- Decision: Use helper functions alongside `pygame.math.Vector2` to preserve safe normalization and magnitude clamping semantics.
  Rationale: `Vector2.normalize()` can raise on zero-length vectors; helpers keep previous zero-safe behavior and deterministic magnitudes.
  Date/Author: 2024-05-19 Codex Agent.

## Outcomes & Retrospective

Completed replacement of the custom vector class with `pygame.math.Vector2`, adding safe normalization and clamp helpers to preserve prior behavior. Unit tests for the simulation (`pytest tests/python`) now run successfully with the pygame dependency installed, indicating spatial grid queries and world updates remain stable.

## Context and Orientation

Relevant files:
- `src/python/terrarium/vector.py` currently defines `Vec2` with normalization and clamp helpers plus `ZERO` constant.
- `src/python/terrarium/world.py` uses vector normalization and clamp length during steering logic.
- Other modules (`agent.py`, `environment.py`, `rng.py`, `spatial_grid.py`) and tests import `Vec2` from `terrarium.vector`.
- Dependencies are listed in `requirements.txt`; pygame is not yet included.

## Plan of Work

1. Introduce pygame dependency by updating `requirements.txt` and installing via pip to ensure `pygame.math.Vector2` is available.
2. Replace imports of `terrarium.vector.Vec2`/`ZERO` with `pygame.math.Vector2`, adding local zero constants where needed.
3. Provide utility helpers (e.g., safe normalization and clamp magnitude) in `world.py` to match previous semantics without relying on the removed module.
4. Remove `src/python/terrarium/vector.py` entirely, adjusting tests to use `Vector2` directly.
5. Run `pytest tests/python` to confirm behavior remains stable.

## Concrete Steps

- From the repo root, edit `requirements.txt` to add pygame.
- Install dependencies: `pip install -r requirements.txt`.
- Update Python modules to import `pygame.math.Vector2` and apply helper functions in `world.py` for normalization and length clamping.
- Delete `src/python/terrarium/vector.py` and update tests to construct `Vector2` from pygame.
- Run validation: `pytest tests/python`.

## Validation and Acceptance

Acceptance criteria:
- Running `pytest tests/python` completes without failures using pygame vectors.
- Simulation math uses `pygame.math.Vector2` exclusively; no references to `terrarium.vector` remain.
- Vector normalization and speed limiting behave identically to prior behavior (zero vectors stay zero; magnitudes clamp to configured limits).

Validation steps:
- Deterministic smoke run: not automated here; rely on unit tests focused on spatial grid behavior to ensure deterministic neighbor queries.
- Performance sanity: ensure vector operations remain O(1); no new O(N²) loops introduced.
- Long-run stability: steering and clamping logic still enforce acceleration and speed limits; negative feedback systems remain unchanged.
- Sim/View separation: changes are confined to simulation math types; no rendering dependencies introduced.

## Idempotence and Recovery

- Dependency installation can be rerun safely with `pip install -r requirements.txt`.
- Code edits are standard git-tracked changes; revert with `git checkout -- <files>` if needed.
- Removing the module is reversible by restoring `src/python/terrarium/vector.py` from version control if necessary.

## Artifacts and Notes

- Validation: `pytest tests/python` (pass).

## Interfaces and Dependencies

- Use `pygame.math.Vector2` for all 2D vector math in the simulation modules and tests.
- Ensure helper functions in `world.py` expose safe normalization and clamp magnitude behavior compatible with prior `Vec2` methods.
