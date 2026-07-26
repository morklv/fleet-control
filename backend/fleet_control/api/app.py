from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from fleet_control.application import compare_schedulers
from fleet_control.domain import Job, Position, RecurringMission

from .runtime import build_demo_coordinator
from .persistence import SQLiteStateStore
from .schemas import JobCreate, MissionCreate
from .serialization import serialize_state


async def _simulation_loop(application: FastAPI) -> None:
    while True:
        if application.state.running:
            application.state.coordinator.tick()
            _advance_demo(application)
            await application.state.broadcast()
        await asyncio.sleep(0.45)


def _advance_demo(application: FastAPI) -> None:
    demo = application.state.demo
    if demo is None:
        return
    coordinator = application.state.coordinator
    elapsed = coordinator.tick_number - demo["started_tick"]
    if not demo["failed_robot_id"] and elapsed >= 7:
        active = sorted(
            (
                robot
                for robot in coordinator.robots.values()
                if robot.current_job_id is not None
            ),
            key=lambda robot: robot.id,
        )
        if active:
            coordinator.fail_robot(active[0].id)
            demo["failed_robot_id"] = active[0].id
            demo["failed_tick"] = coordinator.tick_number
    elif (
        demo["failed_robot_id"]
        and not demo["recovered"]
        and coordinator.tick_number - demo["failed_tick"] >= 8
    ):
        coordinator.recover_robot(demo["failed_robot_id"])
        demo["recovered"] = True


def create_app(
    *,
    start_simulation: bool = True,
    database_path: str | None = None,
) -> FastAPI:
    sockets: set[WebSocket] = set()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.coordinator = build_demo_coordinator()
        application.state.running = True
        application.state.demo = None
        application.state.sockets = sockets
        application.state.store = (
            SQLiteStateStore(database_path) if database_path is not None else None
        )
        if application.state.store is not None:
            restored_running = application.state.store.restore(
                application.state.coordinator
            )
            if restored_running is not None:
                application.state.running = restored_running

        async def broadcast() -> None:
            if application.state.store is not None:
                application.state.store.save(
                    application.state.coordinator,
                    running=application.state.running,
                )
            payload = serialize_state(
                application.state.coordinator,
                running=application.state.running,
            )
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
        return serialize_state(
            application.state.coordinator,
            running=application.state.running,
        )

    @application.get("/api/benchmarks/schedulers")
    def scheduler_benchmark() -> dict[str, object]:
        return compare_schedulers()

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

    @application.post("/api/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str) -> dict[str, str]:
        coordinator = application.state.coordinator
        if job_id not in coordinator.jobs:
            raise HTTPException(status_code=404, detail="job not found")
        try:
            coordinator.cancel_job(job_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        await application.state.broadcast()
        return {"id": job_id, "state": "cancelled"}

    @application.post("/api/missions", status_code=201)
    async def create_mission(payload: MissionCreate) -> dict[str, str]:
        coordinator = application.state.coordinator
        mission = RecurringMission(
            id=f"M-{uuid4().hex[:6].upper()}",
            robot_id=payload.robot_id,
            pickup=Position(payload.pickup.x, payload.pickup.y),
            dropoff=Position(payload.dropoff.x, payload.dropoff.y),
            priority=payload.priority,
        )
        try:
            coordinator.add_mission(mission)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        await application.state.broadcast()
        return {"id": mission.id, "state": "active"}

    @application.post("/api/missions/{mission_id}/stop")
    async def stop_mission(mission_id: str) -> dict[str, str]:
        coordinator = application.state.coordinator
        if mission_id not in coordinator.missions:
            raise HTTPException(status_code=404, detail="mission not found")
        coordinator.stop_mission(mission_id)
        await application.state.broadcast()
        return {"id": mission_id, "state": "stopped"}

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

    @application.post("/api/simulation/step")
    async def step_simulation() -> dict[str, int]:
        if application.state.running:
            raise HTTPException(
                status_code=409,
                detail="pause the simulation before stepping",
            )
        application.state.coordinator.tick()
        _advance_demo(application)
        await application.state.broadcast()
        return {"tick": application.state.coordinator.tick_number}

    @application.post("/api/simulation/reset")
    async def reset_simulation() -> dict[str, bool]:
        application.state.coordinator = build_demo_coordinator()
        application.state.running = True
        application.state.demo = None
        await application.state.broadcast()
        return {"reset": True}

    @application.post("/api/simulation/demo")
    async def run_demo() -> dict[str, bool]:
        coordinator = build_demo_coordinator()
        for job in (
            Job("DEMO-01", Position(2, 1), Position(15, 10), priority=9),
            Job("DEMO-02", Position(15, 1), Position(2, 10), priority=6),
            Job("DEMO-03", Position(2, 6), Position(15, 6), priority=3),
        ):
            coordinator.submit_job(job)
        coordinator._emit(
            "demo_started",
            "Automated demonstration started with three jobs.",
        )
        application.state.coordinator = coordinator
        application.state.running = True
        application.state.demo = {
            "started_tick": coordinator.tick_number,
            "failed_robot_id": None,
            "failed_tick": None,
            "recovered": False,
        }
        await application.state.broadcast()
        return {"demo": True}

    @application.websocket("/ws/fleet")
    async def fleet_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        sockets.add(websocket)
        await websocket.send_json(
            serialize_state(
                application.state.coordinator,
                running=application.state.running,
            )
        )
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            sockets.discard(websocket)

    return application


app = create_app(
    database_path=os.environ.get("FLEET_CONTROL_DB", "fleet-control.db")
)
