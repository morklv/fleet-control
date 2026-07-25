from __future__ import annotations

from dataclasses import dataclass

from fleet_control.domain import Job, JobState, Position, Robot, RobotState
from fleet_control.domain import WarehouseMap
from fleet_control.planning import PathNotFound, find_path


@dataclass(frozen=True, slots=True)
class FleetEvent:
    tick: int
    kind: str
    message: str
    robot_id: str | None = None
    job_id: str | None = None


class FleetCoordinator:
    """Owns scheduling and advances the deterministic fleet simulation."""

    def __init__(
        self,
        warehouse: WarehouseMap,
        robots: list[Robot],
    ) -> None:
        self.warehouse = warehouse
        self.robots = {robot.id: robot for robot in robots}
        self.jobs: dict[str, Job] = {}
        self.tick_number = 0
        self.events: list[FleetEvent] = []

        positions = [robot.position for robot in robots]
        if len(positions) != len(set(positions)):
            raise ValueError("robots must start in unique cells")

    def submit_job(self, job: Job) -> None:
        if job.id in self.jobs:
            raise ValueError(f"job {job.id} already exists")
        if not self.warehouse.is_traversable(job.pickup):
            raise ValueError("job pickup must be traversable")
        if not self.warehouse.is_traversable(job.dropoff):
            raise ValueError("job dropoff must be traversable")
        self.jobs[job.id] = job
        self._emit("job_queued", f"Job {job.id} entered the queue.", job_id=job.id)

    def fail_robot(self, robot_id: str) -> None:
        robot = self.robots[robot_id]
        job_id = robot.current_job_id
        robot.fail()
        robot.current_job_id = None

        if job_id is not None:
            self.jobs[job_id].requeue()
            self._emit(
                "job_requeued",
                f"Job {job_id} was requeued after {robot_id} failed.",
                robot_id=robot_id,
                job_id=job_id,
            )
        self._emit(
            "robot_failed",
            f"Robot {robot_id} is unavailable.",
            robot_id=robot_id,
            job_id=job_id,
        )

    def recover_robot(self, robot_id: str) -> None:
        robot = self.robots[robot_id]
        if robot.state is not RobotState.FAILED:
            raise ValueError(f"robot {robot_id} is not failed")
        robot.transition_to(RobotState.RECOVERING)
        self._emit(
            "robot_recovering",
            f"Robot {robot_id} entered recovery.",
            robot_id=robot_id,
        )

    def tick(self) -> None:
        self.tick_number += 1
        self._schedule_jobs()
        self._advance_non_movement_states()
        self._move_robots()

    def _schedule_jobs(self) -> None:
        queued = sorted(
            (job for job in self.jobs.values() if job.state is JobState.QUEUED),
            key=lambda job: (-job.priority, job.id),
        )

        for job in queued:
            available = [robot for robot in self.robots.values() if robot.is_available]
            if not available:
                return
            robot = min(
                available,
                key=lambda candidate: (
                    candidate.position.manhattan_distance(job.pickup),
                    candidate.id,
                ),
            )
            job.assign_to(robot.id)
            robot.current_job_id = job.id
            robot.transition_to(RobotState.ASSIGNED)
            self._emit(
                "job_assigned",
                f"Job {job.id} assigned to {robot.id}.",
                robot_id=robot.id,
                job_id=job.id,
            )

    def _advance_non_movement_states(self) -> None:
        for robot in self.robots.values():
            if robot.state is RobotState.ASSIGNED:
                robot.transition_to(RobotState.PLANNING)
                continue

            if robot.state is RobotState.PLANNING:
                job = self._current_job(robot)
                try:
                    robot.path = find_path(
                        self.warehouse, robot.position, job.pickup
                    )[1:]
                except PathNotFound:
                    job.state = JobState.FAILED
                    robot.current_job_id = None
                    robot.fail()
                    self._emit(
                        "planning_failed",
                        f"No route exists for job {job.id}.",
                        robot_id=robot.id,
                        job_id=job.id,
                    )
                    continue
                robot.transition_to(RobotState.MOVING_TO_PICKUP)
                if not robot.path:
                    robot.transition_to(RobotState.LOADING)
                continue

            if robot.state is RobotState.LOADING:
                job = self._current_job(robot)
                job.state = JobState.IN_PROGRESS
                try:
                    robot.path = find_path(
                        self.warehouse, robot.position, job.dropoff
                    )[1:]
                except PathNotFound:
                    job.state = JobState.FAILED
                    robot.current_job_id = None
                    robot.fail()
                    continue
                robot.transition_to(RobotState.MOVING_TO_DROPOFF)
                if not robot.path:
                    robot.transition_to(RobotState.UNLOADING)
                continue

            if robot.state is RobotState.UNLOADING:
                job = self._current_job(robot)
                job.state = JobState.COMPLETED
                job.assigned_robot_id = robot.id
                robot.current_job_id = None
                robot.path.clear()
                robot.transition_to(RobotState.IDLE)
                self._emit(
                    "job_completed",
                    f"Robot {robot.id} completed job {job.id}.",
                    robot_id=robot.id,
                    job_id=job.id,
                )
                continue

            if robot.state is RobotState.RECOVERING:
                robot.transition_to(RobotState.IDLE)
                self._emit(
                    "robot_recovered",
                    f"Robot {robot.id} returned to service.",
                    robot_id=robot.id,
                )

    def _move_robots(self) -> None:
        moving_states = {
            RobotState.MOVING_TO_PICKUP,
            RobotState.MOVING_TO_DROPOFF,
        }
        occupied = {robot.position for robot in self.robots.values()}
        reserved: set[Position] = set()

        candidates = sorted(
            (
                robot
                for robot in self.robots.values()
                if robot.state in moving_states and robot.path
            ),
            key=lambda robot: (-robot.wait_ticks, robot.id),
        )

        for robot in candidates:
            next_position = robot.path[0]
            if next_position in occupied or next_position in reserved:
                robot.wait_ticks += 1
                self._emit(
                    "robot_waiting",
                    f"Robot {robot.id} yielded to avoid a collision.",
                    robot_id=robot.id,
                    job_id=robot.current_job_id,
                )
                continue

            occupied.remove(robot.position)
            reserved.add(next_position)
            robot.position = next_position
            robot.path.pop(0)
            robot.wait_ticks = 0

            if not robot.path:
                if robot.state is RobotState.MOVING_TO_PICKUP:
                    robot.transition_to(RobotState.LOADING)
                else:
                    robot.transition_to(RobotState.UNLOADING)

    def _current_job(self, robot: Robot) -> Job:
        if robot.current_job_id is None:
            raise RuntimeError(f"robot {robot.id} has no active job")
        return self.jobs[robot.current_job_id]

    def _emit(
        self,
        kind: str,
        message: str,
        *,
        robot_id: str | None = None,
        job_id: str | None = None,
    ) -> None:
        self.events.append(
            FleetEvent(
                tick=self.tick_number,
                kind=kind,
                message=message,
                robot_id=robot_id,
                job_id=job_id,
            )
        )
