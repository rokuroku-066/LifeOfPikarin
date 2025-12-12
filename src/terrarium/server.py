from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import SimulationConfig
from .world import World


class SimulationController:
    def __init__(self, config: SimulationConfig, broadcast_interval: int = 1):
        self.config = config
        self.world = World(config)
        self.broadcast_interval = max(1, broadcast_interval)
        self.running = False
        self.tick = 0
        self.speed_multiplier = 1.0
        self.clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._broadcast_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._broadcast_task is None:
            self._broadcast_task = asyncio.create_task(self._loop())
        self.running = True

    async def stop(self) -> None:
        self.running = False

    async def reset(self) -> None:
        async with self._lock:
            self.world.reset()
            self.tick = 0
        await self._broadcast_snapshot()

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.config.time_step / self.speed_multiplier)
            if not self.running:
                continue
            async with self._lock:
                self.world.step(self.tick)
                self.tick += 1
            if self.tick % self.broadcast_interval == 0:
                await self._broadcast_snapshot()

    async def _broadcast_snapshot(self) -> None:
        if not self.clients:
            return
        snapshot = self.world.snapshot(self.tick)
        payload = json.dumps(
            {
                "tick": snapshot.tick,
                "metrics": asdict(snapshot.metrics),
                "agents": snapshot.agents,
            }
        )
        stale: Set[WebSocket] = set()
        for client in self.clients:
            try:
                await client.send_text(payload)
            except WebSocketDisconnect:
                stale.add(client)
        for client in stale:
            self.clients.discard(client)


app = FastAPI(title="Terrarium Web Simulation")
controller = SimulationController(SimulationConfig())
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
async def _startup() -> None:
    await controller.start()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/status")
async def status() -> JSONResponse:
    snapshot = controller.world.snapshot(controller.tick)
    return JSONResponse(
        {
            "running": controller.running,
            "tick": controller.tick,
            "population": len(controller.world.agents),
            "metrics": asdict(snapshot.metrics),
        }
    )


@app.post("/api/control/start")
async def start_simulation() -> JSONResponse:
    controller.running = True
    return JSONResponse({"running": True})


@app.post("/api/control/stop")
async def stop_simulation() -> JSONResponse:
    controller.running = False
    return JSONResponse({"running": False})


@app.post("/api/control/reset")
async def reset_simulation() -> JSONResponse:
    await controller.reset()
    return JSONResponse({"running": controller.running, "tick": controller.tick})


@app.post("/api/control/speed")
async def set_speed(payload: dict) -> JSONResponse:
    speed = float(payload.get("multiplier", 1.0))
    controller.speed_multiplier = max(0.1, min(5.0, speed))
    return JSONResponse({"multiplier": controller.speed_multiplier})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    controller.clients.add(websocket)
    await controller._broadcast_snapshot()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        controller.clients.discard(websocket)


__all__ = ["app", "controller"]
