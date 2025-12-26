# Add snapshot queueing with ACK cleanup for single viewer

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If a PLANS.md file is checked into the repo, reference the path to that file here from the repository root and note that this document must be maintained in accordance with PLANS.md.

## Purpose / Big Picture

The viewer should be able to fall behind without breaking ordering, while the simulation continues to generate snapshots at a fixed pace. The server will keep snapshots in an in-memory FIFO queue and remove them when the client acknowledges rendering. The client will render snapshots strictly in order and send ACKs when it advances. The behavior will be visible by running the viewer and observing that the sim continues to advance even if rendering lags, while server memory does not retain old snapshots once they are acknowledged.

## Progress

- [x] (2025-09-27 09:18Z) Draft plan and enumerate files, protocol updates, tests, and docs.
- [x] (2025-09-27 09:26Z) Update server snapshot queueing, ACK handling, and WebSocket protocol.
- [x] (2025-09-27 09:27Z) Update client render queue logic and ACK sending on frame advance.
- [x] (2025-09-27 09:28Z) Add/adjust tests for queue cleanup and update docs for the protocol.
- [x] (2025-09-27 09:30Z) Run required Python tests and capture verification steps.

## Surprises & Discoveries

Pytest emits existing FastAPI `on_event` deprecation warnings from `src/terrarium/app/server.py`.

## Decision Log

- Decision: Proceed with a per-connection last-sent tick state to avoid resending snapshots while keeping a single-viewer assumption.
  Rationale: Keeps queue removal based on ACK while still ensuring ordered delivery without duplicates.
  Date/Author: 2025-09-27 / Codex

## Outcomes & Retrospective

Implemented server-side snapshot queueing with ACK cleanup and client-side render queueing/ACK sending. Added a unit test for ACK cleanup and documented the protocol in `docs/snapshot.md`. Pytest passed with existing FastAPI deprecation warnings unrelated to this change.

## Context and Orientation

The simulation server lives at `src/terrarium/app/server.py`. It owns `SimulationController`, which advances the deterministic world and broadcasts snapshots over WebSockets. The viewer at `src/terrarium/app/static/app.js` currently interpolates between `prevSnapshot` and `nextSnapshot` based on message arrival times. Snapshot schemas are documented in `docs/snapshot.md`. The task adds an in-memory FIFO queue on the server, a client-side render queue, and an ACK protocol to delete rendered snapshots.

A “snapshot” refers to the JSON payload of the simulation state for a given tick.

Constraints to restate:

Simulation and Visualization must remain strictly separated so the View never drives the Sim. No O(N^2) logic should be introduced; neighbor interactions must remain in the SpatialGrid. The simulation must stay deterministic with fixed timesteps. Long-run stability mechanisms must remain intact.

## Plan of Work

I will add a FIFO deque to `SimulationController` that stores serialized snapshot messages with their tick. The server will enqueue every snapshot regardless of rendering and send queued snapshots in order without dropping them, while tracking the last-sent tick per connection. The WebSocket handler will parse client messages, accept `{"type":"ack","tick":N}` payloads, and delete snapshots up to that tick. Reset will clear the queue and reset per-client send state.

On the client side in `src/terrarium/app/static/app.js`, I will introduce a `renderQueue` to buffer snapshots, populate `prevSnapshot`/`nextSnapshot` from that queue, and emit ACKs when the renderer advances from `prev` to `next`. The new server → client protocol will wrap snapshots as `{"type":"snapshot","tick":N,"payload":{...}}` and the client will unpack that payload.

I will add a Python unit test to assert that queued snapshots are removed on ACK and that the FIFO preserves order. I will update `docs/snapshot.md` to document the new protocol and ACK behavior.

## Concrete Steps

1. Edit `src/terrarium/app/server.py` to add a snapshot queue, ACK handling, and ordered send logic.
2. Edit `src/terrarium/app/static/app.js` to enqueue snapshots, update interpolation to use the queue, and send ACKs.
3. Add a test under `tests/python/` for queue cleanup behavior.
4. Update `docs/snapshot.md` with the new WebSocket protocol details.
5. Run `python --version`, `pip install -r requirements.txt`, and `pytest tests/python` from the repo root.

Expected outputs include a passing pytest run and WebSocket messages containing the new `type` and `payload` fields.

## Validation and Acceptance

Deterministic smoke run: run the headless sim in the existing test suite (`pytest tests/python`) and confirm the metrics-related tests continue to pass. Expect tests to report stable population counts and deterministic behavior consistent with current fixtures.

Visual sanity check: run the server and viewer, open the web UI, and observe that agents continue to move smoothly even if the tab is backgrounded or throttled. The viewer should render snapshots in order, and ACKs should cause server-side queue cleanup (validated by temporary logging or inspection).

Performance sanity check: verify tick time and neighbor checks remain in expected ranges by observing `TickMetrics` output in tests; no new O(N^2) logic is introduced.

Long-run stability check: confirm existing long-run tests still pass and the sim continues to show births/deaths and group behavior.

Explicit no O(N^2) note: this change does not add any new per-agent neighbor scanning; it only changes snapshot delivery logic.

Sim/View separation note: the View sends ACKs that only affect server-side queue cleanup and never alter simulation timing or state.

## Idempotence and Recovery

Edits are repeatable. If WebSocket delivery or ACK handling misbehaves, revert the server/client changes and remove the new test to restore the prior broadcast behavior. Queue cleanup can be safely retried by resending an ACK with the last rendered tick.

## Artifacts and Notes

None yet.

## Interfaces and Dependencies

- `SimulationController` in `src/terrarium/app/server.py` will expose methods for enqueueing snapshots, sending queued snapshots, and acknowledging ticks.
- The WebSocket protocol will use JSON messages with `type: "snapshot"` and `type: "ack"`.
- The viewer in `src/terrarium/app/static/app.js` will maintain a `renderQueue` array and send ACKs over the existing WebSocket connection.
- Tests will use `pytest` under `tests/python/`.
