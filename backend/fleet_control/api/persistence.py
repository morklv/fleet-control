from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fleet_control.application import FleetCoordinator, FleetEvent
from fleet_control.domain import (
    Job,
    JobState,
    Position,
    RecurringMission,
    RobotState,
)

from .serialization import serialize_state


class SQLiteStateStore:
    """Persist the authoritative simulator snapshot in a small SQLite database."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS fleet_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save(self, coordinator: FleetCoordinator, *, running: bool) -> None:
        payload = json.dumps(
            serialize_state(coordinator, running=running, event_limit=None),
            separators=(",", ":"),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO fleet_state (id, payload, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (payload,),
            )

    def restore(self, coordinator: FleetCoordinator) -> bool | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM fleet_state WHERE id = 1"
            ).fetchone()
        if row is None:
            return None

        payload = json.loads(row[0])
        coordinator.tick_number = payload["tick"]
        coordinator.jobs = {
            data["id"]: Job(
                id=data["id"],
                pickup=Position(**data["pickup"]),
                dropoff=Position(**data["dropoff"]),
                priority=data["priority"],
                state=JobState(data["state"]),
                assigned_robot_id=data["assigned_robot_id"],
                created_tick=data.get("created_tick", 0),
                assigned_tick=data.get("assigned_tick"),
                started_tick=data.get("started_tick"),
                completed_tick=data.get("completed_tick"),
                cancelled_tick=data.get("cancelled_tick"),
                required_robot_id=data.get("required_robot_id"),
                mission_id=data.get("mission_id"),
            )
            for data in payload["jobs"]
        }
        coordinator.missions = {
            data["id"]: RecurringMission(
                id=data["id"],
                robot_id=data["robot_id"],
                pickup=Position(**data["pickup"]),
                dropoff=Position(**data["dropoff"]),
                priority=data["priority"],
                active=data["active"],
                cycles_completed=data["cycles_completed"],
                current_job_id=data["current_job_id"],
            )
            for data in payload.get("missions", [])
        }
        for data in payload["robots"]:
            robot = coordinator.robots[data["id"]]
            robot.position = Position(**data["position"])
            robot.state = RobotState(data["state"])
            robot.current_job_id = data["current_job_id"]
            robot.path = [Position(**position) for position in data["path"]]
            robot.wait_ticks = data["wait_ticks"]
            robot.battery_level = data.get("battery_level", robot.battery_capacity)
            robot.battery_capacity = data.get(
                "battery_capacity", robot.battery_capacity
            )
            robot.charging_station = (
                Position(**data["charging_station"])
                if data.get("charging_station")
                else None
            )
            if robot.state in {
                RobotState.MOVING_TO_CHARGER,
                RobotState.CHARGING,
            }:
                robot.resume_state = (
                    RobotState.MOVING_TO_DROPOFF
                    if robot.current_job_id
                    and coordinator.jobs[robot.current_job_id].state
                    is JobState.IN_PROGRESS
                    else RobotState.MOVING_TO_PICKUP
                    if robot.current_job_id
                    else None
                )
        coordinator.events = [
            FleetEvent(
                tick=data["tick"],
                kind=data["kind"],
                message=data["message"],
                robot_id=data["robot_id"],
                job_id=data["job_id"],
            )
            for data in payload["events"]
        ]
        return payload.get("running", True)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)
