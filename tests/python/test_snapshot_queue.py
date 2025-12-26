import asyncio

from terrarium.app.server import SimulationController
from terrarium.sim.core.config import SimulationConfig


def test_snapshot_queue_ack_cleanup() -> None:
    controller = SimulationController(SimulationConfig())

    async def exercise() -> None:
        controller.tick = 1
        await controller._broadcast_snapshot()
        controller.tick = 2
        await controller._broadcast_snapshot()
        async with controller._queue_lock:
            queued_ticks = [item.tick for item in controller._snapshot_queue]
        assert queued_ticks == [1, 2]
        await controller.acknowledge(1)
        async with controller._queue_lock:
            remaining_ticks = [item.tick for item in controller._snapshot_queue]
        assert remaining_ticks == [2]

    asyncio.run(exercise())
