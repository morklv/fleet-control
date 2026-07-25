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


@dataclass(slots=True)
class Job:
    id: str
    pickup: Position
    dropoff: Position
    priority: int = 0
    state: JobState = JobState.QUEUED
    assigned_robot_id: str | None = None

    def assign_to(self, robot_id: str) -> None:
        if self.state is not JobState.QUEUED or self.assigned_robot_id is not None:
            raise ValueError(f"job {self.id} is not available for assignment")
        self.assigned_robot_id = robot_id
        self.state = JobState.ASSIGNED

    def requeue(self) -> None:
        self.assigned_robot_id = None
        self.state = JobState.QUEUED

