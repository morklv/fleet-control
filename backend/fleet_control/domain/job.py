from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .position import Position


class JobState(StrEnum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Job:
    id: str
    pickup: Position
    dropoff: Position
    priority: int = 0
    state: JobState = JobState.QUEUED
    assigned_robot_id: str | None = None
    created_tick: int = 0
    assigned_tick: int | None = None
    started_tick: int | None = None
    completed_tick: int | None = None
    cancelled_tick: int | None = None
    required_robot_id: str | None = None
    mission_id: str | None = None

    def assign_to(self, robot_id: str, *, tick: int | None = None) -> None:
        if self.state is not JobState.QUEUED or self.assigned_robot_id is not None:
            raise ValueError(f"job {self.id} is not available for assignment")
        self.assigned_robot_id = robot_id
        self.assigned_tick = tick
        self.state = JobState.ASSIGNED

    def requeue(self) -> None:
        self.assigned_robot_id = None
        self.assigned_tick = None
        self.started_tick = None
        self.state = JobState.QUEUED

    def cancel(self, *, tick: int) -> None:
        if self.state in {JobState.COMPLETED, JobState.CANCELLED}:
            raise ValueError(f"job {self.id} cannot be cancelled")
        self.state = JobState.CANCELLED
        self.cancelled_tick = tick
