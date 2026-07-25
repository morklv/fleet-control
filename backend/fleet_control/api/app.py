from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from fleet_control.domain import Job, Position

from .runtime import build_demo_coordinator
from .schemas import JobCreate
from .serialization import serialize_state


async def _simulation_loop(application: FastAPI) -> None:
    while True:
        if application.state.running:
            application.state.coordinator.tick()
            await application.state.broadcast()
        await asyncio.sleep(0.45)


def create_app(*, start_simulation: bool = True) -> FastAPI:
    sockets: set[WebSocket] = set()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.coordinator = build_demo_coordinator()
        application.state.running = True
        application.state.sockets = sockets

        async def broadcast() -> None:
            payload = serialize_state(application.state.coordinator)
            disconnected: list[WebSocket] = []
            for socket in sockets:
                try:
                    await socket.send_json(payload)
                except (RuntimeError, WebSocketDisconnect):
                    disconnected.append(socket)
            for socket in disconnected:
                sockets.discard(socket)

        application.state.broadcast = broadcast
        task = (
            asyncio.create_task(_simulation_loop(application))
            if start_simulation
            else None
        )
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    application = FastAPI(
        title="Fleet Control",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "operational"}

    @application.get("/api/state")
    def state() -> dict:
        return serialize_state(application.state.coordinator)

    @application.post("/api/jobs", status_code=201)
    async def create_job(payload: JobCreate) -> dict:
        coordinator = application.state.coordinator
        job = Job(
            id=f"J-{uuid4().hex[:6].upper()}",
            pickup=Position(payload.pickup.x, payload.pickup.y),
            dropoff=Position(payload.dropoff.x, payload.dropoff.y),
            priority=payload.priority,
        )
        try:
            coordinator.submit_job(job)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        await application.state.broadcast()
        return {"id": job.id, "state": job.state.value}

    @application.post("/api/robots/{robot_id}/fail")
    async def fail_robot(robot_id: str) -> dict[str, str]:
        coordinator = application.state.coordinator
        if robot_id not in coordinator.robots:
            raise HTTPException(status_code=404, detail="robot not found")
        try:
            coordinator.fail_robot(robot_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        await application.state.broadcast()
        return {"id": robot_id, "state": "failed"}

    @application.post("/api/robots/{robot_id}/recover")
    async def recover_robot(robot_id: str) -> dict[str, str]:
        coordinator = application.state.coordinator
        if robot_id not in coordinator.robots:
            raise HTTPException(status_code=404, detail="robot not found")
        try:
            coordinator.recover_robot(robot_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        await application.state.broadcast()
        return {"id": robot_id, "state": "recovering"}

    @application.post("/api/simulation/toggle")
    async def toggle_simulation() -> dict[str, bool]:
        application.state.running = not application.state.running
        await application.state.broadcast()
        return {"running": application.state.running}

    @application.post("/api/simulation/reset")
    async def reset_simulation() -> dict[str, bool]:
        application.state.coordinator = build_demo_coordinator()
        application.state.running = True
        await application.state.broadcast()
        return {"reset": True}

    @application.websocket("/ws/fleet")
    async def fleet_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        sockets.add(websocket)
        await websocket.send_json(serialize_state(application.state.coordinator))
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            sockets.discard(websocket)

    return application


app = create_app()
