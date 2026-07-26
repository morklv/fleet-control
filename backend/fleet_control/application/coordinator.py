from __future__ import annotations

from dataclasses import dataclass

from fleet_control.domain import (
    Job,
    JobState,
    Position,
    RecurringMission,
    Robot,
    RobotState,
)
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
        charging_stations: tuple[Position, ...] = (),
        scheduling_strategy: str = "optimized",
    ) -> None:
        self.warehouse = warehouse
        self.robots = {robot.id: robot for robot in robots}
        self.jobs: dict[str, Job] = {}
        self.missions: dict[str, RecurringMission] = {}
        self.charging_stations = charging_stations
        if scheduling_strategy not in {"nearest", "optimized"}:
            raise ValueError("unknown scheduling strategy")
        self.scheduling_strategy = scheduling_strategy
        self.tick_number = 0
        self.events: list[FleetEvent] = []

        positions = [robot.position for robot in robots]
        if len(positions) != len(set(positions)):
            raise ValueError("robots must start in unique cells")
        if any(not warehouse.is_traversable(station) for station in charging_stations):
            raise ValueError("charging stations must be traversable")

    def submit_job(self, job: Job) -> None:
        if job.id in self.jobs:
            raise ValueError(f"job {job.id} already exists")
        if not self.warehouse.is_traversable(job.pickup):
            raise ValueError("job pickup must be traversable")
        if not self.warehouse.is_traversable(job.dropoff):
            raise ValueError("job dropoff must be traversable")
        if job.required_robot_id and job.required_robot_id not in self.robots:
            raise ValueError("required robot does not exist")
        job.created_tick = self.tick_number
        self.jobs[job.id] = job
        self._emit("job_queued", f"Job {job.id} entered the queue.", job_id=job.id)

    def add_mission(self, mission: RecurringMission) -> None:
        if mission.id in self.missions:
            raise ValueError(f"mission {mission.id} already exists")
        if mission.robot_id not in self.robots:
            raise ValueError("robot does not exist")
        if any(
            existing.active and existing.robot_id == mission.robot_id
            for existing in self.missions.values()
        ):
            raise ValueError(f"robot {mission.robot_id} already has an active mission")
        if mission.pickup == mission.dropoff:
            raise ValueError("mission pickup and dropoff must differ")
        if not self.warehouse.is_traversable(mission.pickup):
            raise ValueError("mission pickup must be traversable")
        if not self.warehouse.is_traversable(mission.dropoff):
            raise ValueError("mission dropoff must be traversable")
        self.missions[mission.id] = mission
        self._emit(
            "mission_started",
            f"Recurring mission {mission.id} assigned to {mission.robot_id}.",
            robot_id=mission.robot_id,
        )

    def stop_mission(self, mission_id: str) -> None:
        mission = self.missions[mission_id]
        mission.active = False
        if mission.current_job_id:
            job = self.jobs[mission.current_job_id]
            if job.state not in {JobState.COMPLETED, JobState.CANCELLED}:
                self.cancel_job(job.id)
        mission.current_job_id = None
        self._emit(
            "mission_stopped",
            f"Recurring mission {mission.id} stopped.",
            robot_id=mission.robot_id,
        )

    def cancel_job(self, job_id: str) -> None:
        job = self.jobs[job_id]
        if job.state in {JobState.COMPLETED, JobState.CANCELLED, JobState.FAILED}:
            raise ValueError(f"job {job.id} cannot be cancelled")

        robot_id = job.assigned_robot_id
        if robot_id is not None:
            self.robots[robot_id].release_job()
        job.cancel(tick=self.tick_number)
        if job.mission_id is not None:
            self.missions[job.mission_id].current_job_id = None
        self._emit(
            "job_cancelled",
            f"Job {job.id} was cancelled.",
            robot_id=robot_id,
            job_id=job.id,
        )

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
        self._manage_energy()
        self._prepare_recurring_jobs()
        self._schedule_jobs()
        self._advance_non_movement_states()
        self._move_robots()

    def _manage_energy(self) -> None:
        if not self.charging_stations:
            return
        for robot in sorted(self.robots.values(), key=lambda item: item.id):
            if robot.state is RobotState.CHARGING:
                previous = robot.battery_level
                robot.battery_level = min(
                    robot.battery_capacity,
                    robot.battery_level + robot.charge_rate,
                )
                if robot.battery_level == robot.battery_capacity:
                    resume_state = robot.resume_state
                    robot.resume_state = None
                    robot.charging_station = None
                    if robot.current_job_id is None:
                        robot.transition_to(RobotState.IDLE)
                    else:
                        job = self._current_job(robot)
                        target = (
                            job.dropoff
                            if resume_state is RobotState.MOVING_TO_DROPOFF
                            else job.pickup
                        )
                        robot.path = find_path(
                            self.warehouse, robot.position, target
                        )[1:]
                        if resume_state is RobotState.MOVING_TO_DROPOFF:
                            robot.transition_to(RobotState.MOVING_TO_DROPOFF)
                            if not robot.path:
                                robot.transition_to(RobotState.UNLOADING)
                        else:
                            robot.transition_to(RobotState.MOVING_TO_PICKUP)
                            if not robot.path:
                                robot.transition_to(RobotState.LOADING)
                    self._emit(
                        "charging_completed",
                        f"Robot {robot.id} charged to 100% and resumed work.",
                        robot_id=robot.id,
                        job_id=robot.current_job_id,
                    )
                elif previous != robot.battery_level:
                    self._emit(
                        "robot_charging",
                        f"Robot {robot.id} battery reached {robot.battery_percent}%.",
                        robot_id=robot.id,
                        job_id=robot.current_job_id,
                    )
                continue

            if robot.state in {
                RobotState.MOVING_TO_CHARGER,
                RobotState.FAILED,
                RobotState.RECOVERING,
            }:
                continue

            if robot.state in {
                RobotState.MOVING_TO_PICKUP,
                RobotState.MOVING_TO_DROPOFF,
            }:
                job = self._current_job(robot)
                target = (
                    job.pickup
                    if robot.state is RobotState.MOVING_TO_PICKUP
                    else job.dropoff
                )
                post_leg_distance = self._distance_to_nearest_charger(target)
                required = (
                    len(robot.path) + post_leg_distance
                ) * robot.move_cost + 2
                if robot.battery_level < required:
                    self._route_to_charger(robot, resume_state=robot.state)
            elif robot.is_available:
                distance = self._distance_to_nearest_charger(robot.position)
                if robot.battery_level <= distance * robot.move_cost + 20:
                    self._route_to_charger(robot, resume_state=None)

    def _distance_to_nearest_charger(self, position: Position) -> int:
        return min(
            len(find_path(self.warehouse, position, station)) - 1
            for station in self.charging_stations
        )

    def _route_to_charger(
        self,
        robot: Robot,
        *,
        resume_state: RobotState | None,
    ) -> None:
        route, station = min(
            [
                (
                find_path(self.warehouse, robot.position, station),
                station,
                )
                for station in self.charging_stations
            ],
            key=lambda item: (len(item[0]), item[1]),
        )
        robot.resume_state = resume_state
        robot.charging_station = station
        robot.path = route[1:]
        robot.transition_to(
            RobotState.MOVING_TO_CHARGER
            if robot.path
            else RobotState.CHARGING
        )
        self._emit(
            "charging_required",
            (
                f"Robot {robot.id} reserved {len(robot.path)} moves to charger "
                f"with {robot.battery_level} units remaining."
            ),
            robot_id=robot.id,
            job_id=robot.current_job_id,
        )

    def _prepare_recurring_jobs(self) -> None:
        for mission in sorted(self.missions.values(), key=lambda item: item.id):
            if not mission.active or mission.current_job_id is not None:
                continue
            job_id = f"{mission.id}-{mission.cycles_completed + 1:04d}"
            job = Job(
                id=job_id,
                pickup=mission.pickup,
                dropoff=mission.dropoff,
                priority=mission.priority,
                required_robot_id=mission.robot_id,
                mission_id=mission.id,
            )
            self.submit_job(job)
            mission.current_job_id = job_id

    def _schedule_jobs(self) -> None:
        mission_robot_ids = {
            mission.robot_id
            for mission in self.missions.values()
            if mission.active
        }
        queued = sorted(
            (job for job in self.jobs.values() if job.state is JobState.QUEUED),
            key=lambda job: (-job.priority, job.id),
        )

        for job in queued:
            available = [
                robot
                for robot in self.robots.values()
                if robot.is_available
                and (
                    (
                        job.required_robot_id is None
                        and robot.id not in mission_robot_ids
                    )
                    or robot.id == job.required_robot_id
                )
            ]
            if not available:
                continue
            robot = min(available, key=lambda candidate: self._assignment_score(candidate, job))
            job.assign_to(robot.id, tick=self.tick_number)
            robot.current_job_id = job.id
            robot.transition_to(RobotState.ASSIGNED)
            self._emit(
                "job_assigned",
                (
                    f"Job {job.id} assigned to {robot.id} by the "
                    f"{self.scheduling_strategy} scheduler."
                ),
                robot_id=robot.id,
                job_id=job.id,
            )

    def _assignment_score(self, robot: Robot, job: Job) -> tuple[float, str]:
        pickup_distance = len(
            find_path(self.warehouse, robot.position, job.pickup)
        ) - 1
        if self.scheduling_strategy == "nearest":
            return pickup_distance, robot.id

        delivery_distance = len(
            find_path(self.warehouse, job.pickup, job.dropoff)
        ) - 1
        charger_after_delivery = (
            self._distance_to_nearest_charger(job.dropoff)
            if self.charging_stations
            else 0
        )
        required_energy = (
            pickup_distance + delivery_distance + charger_after_delivery + 2
        ) * robot.move_cost
        charging_penalty = 0.0
        if robot.battery_level < required_energy and self.charging_stations:
            charger_route, charger = min(
                [
                    (
                        find_path(self.warehouse, robot.position, station),
                        station,
                    )
                    for station in self.charging_stations
                ],
                key=lambda item: (len(item[0]), item[1]),
            )
            charger_distance = len(charger_route) - 1
            charger_to_pickup = len(
                find_path(self.warehouse, charger, job.pickup)
            ) - 1
            charge_ticks = max(
                0,
                robot.battery_capacity - robot.battery_level,
            ) / robot.charge_rate
            charging_penalty = (
                charger_distance
                + charge_ticks
                + charger_to_pickup
                - pickup_distance
            )

        planned_cells = {
            position
            for other in self.robots.values()
            if other.id != robot.id
            for position in other.path[:6]
        }
        route_to_pickup = find_path(
            self.warehouse, robot.position, job.pickup
        )
        congestion_penalty = sum(
            position in planned_cells for position in route_to_pickup
        ) * 2
        return (
            pickup_distance + charging_penalty + congestion_penalty,
            robot.id,
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
                if job.started_tick is None:
                    job.started_tick = self.tick_number
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
                job.completed_tick = self.tick_number
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
                if job.mission_id is not None:
                    mission = self.missions[job.mission_id]
                    mission.cycles_completed += 1
                    mission.current_job_id = None
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
            RobotState.MOVING_TO_CHARGER,
        }
        occupied = {robot.position for robot in self.robots.values()}
        reserved: set[Position] = set()
        reserved_edges: set[tuple[Position, Position]] = set()
        yielded_this_tick: set[str] = set()
        processed_this_tick: set[str] = set()

        candidates = sorted(
            (
                robot
                for robot in self.robots.values()
                if robot.state in moving_states and robot.path
            ),
            key=lambda robot: (
                -(
                    (
                        self.jobs[robot.current_job_id].priority
                        if robot.current_job_id is not None
                        else 10
                    )
                    + min(robot.wait_ticks, 10)
                ),
                robot.id,
            ),
        )
        planned_positions = {
            position for candidate in candidates for position in candidate.path
        }

        for robot in candidates:
            if robot.id in yielded_this_tick:
                continue
            next_position = robot.path[0]
            blocker = next(
                (
                    other
                    for other in self.robots.values()
                    if other.position == next_position and other.id != robot.id
                ),
                None,
            )
            head_on = (
                blocker is not None
                and blocker.id not in processed_this_tick
                and blocker.state in moving_states
                and bool(blocker.path)
                and blocker.path[0] == robot.position
            )
            if head_on:
                horizontal_conflict = blocker.position.y == robot.position.y
                escape = next(
                    (
                        position
                        for position in self.warehouse.neighbors(blocker.position)
                        if position not in occupied
                        and position not in reserved
                        and position not in {robot.position, next_position}
                        and (
                            position.x == blocker.position.x
                            if horizontal_conflict
                            else position.y == blocker.position.y
                        )
                    ),
                    None,
                )
                if escape is not None:
                    occupied.remove(blocker.position)
                    blocker.position = escape
                    blocker.battery_level = max(
                        0, blocker.battery_level - blocker.move_cost
                    )
                    occupied.add(escape)
                    blocker.wait_ticks += 1
                    yielded_this_tick.add(blocker.id)
                    self._replan_around_traffic(blocker, occupied | reserved)
                    self._emit(
                        "robot_yielded",
                        f"Robot {blocker.id} pulled aside and yielded to {robot.id}.",
                        robot_id=blocker.id,
                        job_id=blocker.current_job_id,
                    )

            if blocker is not None and blocker.is_available:
                escape = next(
                    (
                        position
                        for position in self.warehouse.neighbors(blocker.position)
                        if position not in occupied
                        and position not in reserved
                        and position not in planned_positions
                    ),
                    None,
                )
                if escape is not None:
                    occupied.remove(blocker.position)
                    blocker.position = escape
                    occupied.add(escape)
                    self._emit(
                        "robot_repositioned",
                        f"Robot {blocker.id} cleared the route for {robot.id}.",
                        robot_id=blocker.id,
                    )

            if (
                next_position in occupied
                or next_position in reserved
                or (next_position, robot.position) in reserved_edges
            ):
                robot.wait_ticks += 1
                self._emit(
                    "robot_waiting",
                    f"Robot {robot.id} yielded to avoid a collision.",
                    robot_id=robot.id,
                    job_id=robot.current_job_id,
                )
                if robot.wait_ticks >= 3:
                    self._replan_around_traffic(robot, occupied | reserved)
                processed_this_tick.add(robot.id)
                continue

            previous_position = robot.position
            occupied.remove(robot.position)
            reserved.add(next_position)
            reserved_edges.add((previous_position, next_position))
            robot.position = next_position
            robot.battery_level = max(
                0, robot.battery_level - robot.move_cost
            )
            robot.path.pop(0)
            robot.wait_ticks = 0
            processed_this_tick.add(robot.id)

            if not robot.path:
                if robot.state is RobotState.MOVING_TO_CHARGER:
                    robot.transition_to(RobotState.CHARGING)
                    self._emit(
                        "charger_arrived",
                        f"Robot {robot.id} arrived at a charging station.",
                        robot_id=robot.id,
                        job_id=robot.current_job_id,
                    )
                elif robot.state is RobotState.MOVING_TO_PICKUP:
                    robot.transition_to(RobotState.LOADING)
                else:
                    robot.transition_to(RobotState.UNLOADING)

    def _replan_around_traffic(
        self,
        robot: Robot,
        blocked: set[Position],
    ) -> None:
        job = (
            self._current_job(robot)
            if robot.current_job_id is not None
            else None
        )
        if robot.state is RobotState.MOVING_TO_CHARGER:
            if robot.charging_station is None:
                return
            goal = robot.charging_station
        elif robot.state is RobotState.MOVING_TO_PICKUP:
            if job is None:
                return
            goal = job.pickup
        else:
            if job is None:
                return
            goal = job.dropoff
        try:
            alternative = find_path(
                self.warehouse,
                robot.position,
                goal,
                blocked=frozenset(blocked - {robot.position, goal}),
            )[1:]
        except PathNotFound:
            return
        if alternative != robot.path:
            robot.path = alternative
            self._emit(
                "robot_replanned",
                f"Robot {robot.id} replanned around traffic.",
                robot_id=robot.id,
                job_id=job.id if job is not None else None,
            )

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
