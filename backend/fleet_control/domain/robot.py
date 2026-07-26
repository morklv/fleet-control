from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .position import Position


class RobotState(StrEnum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    PLANNING = "planning"
    MOVING_TO_PICKUP = "moving_to_pickup"
    LOADING = "loading"
    MOVING_TO_DROPOFF = "moving_to_dropoff"
    MOVING_TO_CHARGER = "moving_to_charger"
    CHARGING = "charging"
    UNLOADING = "unloading"
    FAILED = "failed"
    RECOVERING = "recovering"


ACTIVE_STATES = frozenset(
    {
        RobotState.ASSIGNED,
        RobotState.PLANNING,
        RobotState.MOVING_TO_PICKUP,
        RobotState.LOADING,
        RobotState.MOVING_TO_DROPOFF,
        RobotState.MOVING_TO_CHARGER,
        RobotState.CHARGING,
        RobotState.UNLOADING,
    }
)

ALLOWED_TRANSITIONS: dict[RobotState, frozenset[RobotState]] = {
    RobotState.IDLE: frozenset(
        {RobotState.ASSIGNED, RobotState.MOVING_TO_CHARGER, RobotState.CHARGING, RobotState.FAILED}
    ),
    RobotState.ASSIGNED: frozenset(
        {RobotState.IDLE, RobotState.PLANNING, RobotState.FAILED}
    ),
    RobotState.PLANNING: frozenset(
        {RobotState.IDLE, RobotState.MOVING_TO_PICKUP, RobotState.FAILED}
    ),
    RobotState.MOVING_TO_PICKUP: frozenset(
        {RobotState.IDLE, RobotState.LOADING, RobotState.MOVING_TO_CHARGER, RobotState.FAILED}
    ),
    RobotState.LOADING: frozenset(
        {RobotState.IDLE, RobotState.MOVING_TO_DROPOFF, RobotState.FAILED}
    ),
    RobotState.MOVING_TO_DROPOFF: frozenset(
        {RobotState.IDLE, RobotState.UNLOADING, RobotState.MOVING_TO_CHARGER, RobotState.FAILED}
    ),
    RobotState.MOVING_TO_CHARGER: frozenset(
        {RobotState.CHARGING, RobotState.IDLE, RobotState.FAILED}
    ),
    RobotState.CHARGING: frozenset(
        {
            RobotState.IDLE,
            RobotState.PLANNING,
            RobotState.MOVING_TO_PICKUP,
            RobotState.MOVING_TO_DROPOFF,
            RobotState.FAILED,
        }
    ),
    RobotState.UNLOADING: frozenset({RobotState.IDLE, RobotState.FAILED}),
    RobotState.FAILED: frozenset({RobotState.RECOVERING}),
    RobotState.RECOVERING: frozenset({RobotState.IDLE, RobotState.FAILED}),
}


class InvalidRobotTransition(ValueError):
    pass


@dataclass(slots=True)
class Robot:
    id: str
    position: Position
    state: RobotState = RobotState.IDLE
    current_job_id: str | None = None
    path: list[Position] = field(default_factory=list)
    wait_ticks: int = 0
    battery_capacity: int = 100
    battery_level: int = 100
    move_cost: int = 1
    charge_rate: int = 15
    resume_state: RobotState | None = None
    charging_station: Position | None = None

    @property
    def battery_percent(self) -> int:
        return round(100 * self.battery_level / self.battery_capacity)

    @property
    def is_available(self) -> bool:
        return self.state is RobotState.IDLE and self.current_job_id is None

    def transition_to(self, next_state: RobotState) -> None:
        if next_state not in ALLOWED_TRANSITIONS[self.state]:
            raise InvalidRobotTransition(
                f"robot {self.id} cannot transition from "
                f"{self.state.value} to {next_state.value}"
            )
        self.state = next_state

    def fail(self) -> None:
        if self.state is not RobotState.FAILED:
            self.transition_to(RobotState.FAILED)
        self.path.clear()
        self.wait_ticks = 0
        self.resume_state = None
        self.charging_station = None

    def release_job(self) -> None:
        if self.state in ACTIVE_STATES:
            self.transition_to(RobotState.IDLE)
        self.current_job_id = None
        self.path.clear()
        self.wait_ticks = 0
        self.resume_state = None
        self.charging_station = None
