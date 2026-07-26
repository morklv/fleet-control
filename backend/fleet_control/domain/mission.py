from __future__ import annotations

from dataclasses import dataclass

from .position import Position


@dataclass(slots=True)
class RecurringMission:
    id: str
    robot_id: str
    pickup: Position
    dropoff: Position
    priority: int = 5
    active: bool = True
    cycles_completed: int = 0
    current_job_id: str | None = None
