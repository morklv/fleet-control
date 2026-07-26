from fleet_control.application import FleetCoordinator
from fleet_control.domain import (
    Job,
    JobState,
    Position,
    RecurringMission,
    Robot,
    RobotState,
    WarehouseMap,
)


def run_until(
    coordinator: FleetCoordinator,
    predicate,
    *,
    maximum_ticks: int = 100,
) -> None:
    for _ in range(maximum_ticks):
        coordinator.tick()
        if predicate():
            return
    raise AssertionError("condition was not reached before tick limit")


def test_nearest_available_robot_receives_job() -> None:
    coordinator = FleetCoordinator(
        WarehouseMap(width=8, height=4),
        [
            Robot("R-1", Position(0, 0)),
            Robot("R-2", Position(7, 3)),
        ],
    )
    job = Job("J-1", Position(1, 0), Position(5, 0))
    coordinator.submit_job(job)

    coordinator.tick()

    assert job.assigned_robot_id == "R-1"


def test_robot_completes_pickup_and_delivery() -> None:
    robot = Robot("R-1", Position(0, 0))
    coordinator = FleetCoordinator(
        WarehouseMap(width=6, height=3),
        [robot],
    )
    job = Job("J-1", Position(1, 0), Position(4, 0))
    coordinator.submit_job(job)

    run_until(coordinator, lambda: job.state is JobState.COMPLETED)

    assert robot.position == Position(4, 0)
    assert robot.state is RobotState.IDLE
    assert robot.current_job_id is None


def test_two_robots_never_occupy_same_cell() -> None:
    coordinator = FleetCoordinator(
        WarehouseMap(width=5, height=3),
        [
            Robot("R-1", Position(0, 0)),
            Robot("R-2", Position(4, 0)),
        ],
    )
    coordinator.submit_job(Job("J-1", Position(1, 0), Position(3, 0)))
    coordinator.submit_job(Job("J-2", Position(3, 0), Position(1, 0)))

    for _ in range(12):
        coordinator.tick()
        positions = [robot.position for robot in coordinator.robots.values()]
        assert len(positions) == len(set(positions))


def test_failure_requeues_job_for_another_robot() -> None:
    first = Robot("R-1", Position(0, 0))
    second = Robot("R-2", Position(7, 2))
    coordinator = FleetCoordinator(
        WarehouseMap(width=8, height=3),
        [first, second],
    )
    job = Job("J-1", Position(1, 0), Position(6, 0))
    coordinator.submit_job(job)
    coordinator.tick()
    assert job.assigned_robot_id == first.id

    coordinator.fail_robot(first.id)
    run_until(coordinator, lambda: job.state is JobState.COMPLETED)

    assert job.assigned_robot_id == second.id
    assert first.state is RobotState.FAILED
    assert any(event.kind == "job_requeued" for event in coordinator.events)


def test_failed_robot_can_recover_to_idle() -> None:
    robot = Robot("R-1", Position(0, 0))
    coordinator = FleetCoordinator(
        WarehouseMap(width=3, height=3),
        [robot],
    )
    coordinator.fail_robot(robot.id)

    coordinator.recover_robot(robot.id)
    coordinator.tick()

    assert robot.state is RobotState.IDLE


def test_idle_robot_clears_occupied_delivery_station() -> None:
    delivering = Robot("R-1", Position(0, 0))
    blocker = Robot("R-2", Position(2, 0))
    coordinator = FleetCoordinator(
        WarehouseMap(width=3, height=2),
        [delivering, blocker],
    )
    job = Job("J-1", Position(1, 0), Position(2, 0))
    coordinator.submit_job(job)

    run_until(coordinator, lambda: job.state is JobState.COMPLETED)

    assert delivering.position == Position(2, 0)
    assert blocker.position == Position(2, 1)
    assert any(event.kind == "robot_repositioned" for event in coordinator.events)


def test_assigned_job_can_be_cancelled_and_releases_robot() -> None:
    robot = Robot("R-1", Position(0, 0))
    coordinator = FleetCoordinator(
        WarehouseMap(width=4, height=2),
        [robot],
    )
    job = Job("J-1", Position(1, 0), Position(3, 0))
    coordinator.submit_job(job)
    coordinator.tick()

    coordinator.cancel_job(job.id)

    assert job.state is JobState.CANCELLED
    assert robot.state is RobotState.IDLE
    assert robot.current_job_id is None
    assert robot.path == []


def test_recurring_mission_repeats_for_specific_robot() -> None:
    first = Robot("R-1", Position(0, 0))
    second = Robot("R-2", Position(4, 1))
    coordinator = FleetCoordinator(
        WarehouseMap(width=5, height=2),
        [first, second],
    )
    mission = RecurringMission(
        "M-1",
        robot_id=second.id,
        pickup=Position(3, 1),
        dropoff=Position(1, 1),
        priority=7,
    )
    coordinator.add_mission(mission)

    run_until(coordinator, lambda: mission.cycles_completed >= 2)

    mission_jobs = [
        job for job in coordinator.jobs.values() if job.mission_id == mission.id
    ]
    assert len(mission_jobs) == 2
    assert all(job.assigned_robot_id == second.id for job in mission_jobs)
    assert first.state is RobotState.IDLE


def test_job_priority_controls_right_of_way() -> None:
    high_priority = Robot("R-1", Position(0, 1))
    low_priority = Robot("R-2", Position(2, 1))
    coordinator = FleetCoordinator(
        WarehouseMap(width=3, height=3),
        [high_priority, low_priority],
    )
    coordinator.submit_job(
        Job("J-HIGH", Position(1, 1), Position(1, 0), priority=9)
    )
    coordinator.submit_job(
        Job("J-LOW", Position(1, 1), Position(1, 2), priority=1)
    )

    coordinator.tick()
    coordinator.tick()

    assert high_priority.position == Position(1, 1)
    assert low_priority.position == Position(2, 1)
    assert low_priority.wait_ticks == 1


def test_head_on_robot_pulls_aside_for_higher_priority_robot() -> None:
    high_priority = Robot("R-1", Position(1, 1))
    low_priority = Robot("R-2", Position(2, 1))
    coordinator = FleetCoordinator(
        WarehouseMap(width=4, height=3),
        [high_priority, low_priority],
    )
    coordinator.submit_job(
        Job(
            "J-HIGH",
            Position(2, 1),
            Position(3, 1),
            priority=9,
            required_robot_id=high_priority.id,
        )
    )
    coordinator.submit_job(
        Job(
            "J-LOW",
            Position(1, 1),
            Position(0, 1),
            priority=1,
            required_robot_id=low_priority.id,
        )
    )

    coordinator.tick()
    coordinator.tick()

    assert high_priority.position == Position(2, 1)
    assert low_priority.position in {Position(2, 0), Position(2, 2)}
    assert any(event.kind == "robot_yielded" for event in coordinator.events)


def test_robot_charges_and_resumes_delivery_before_battery_is_unsafe() -> None:
    robot = Robot(
        "R-1",
        Position(2, 0),
        battery_capacity=20,
        battery_level=8,
        charge_rate=10,
    )
    coordinator = FleetCoordinator(
        WarehouseMap(width=8, height=2),
        [robot],
        charging_stations=(Position(0, 0),),
    )
    job = Job(
        "J-ENERGY",
        pickup=Position(3, 0),
        dropoff=Position(7, 0),
        required_robot_id=robot.id,
    )
    coordinator.submit_job(job)

    run_until(
        coordinator,
        lambda: job.state is JobState.COMPLETED,
        maximum_ticks=80,
    )

    assert robot.position == job.dropoff
    assert robot.battery_level > 0
    assert any(event.kind == "charging_required" for event in coordinator.events)
    assert any(event.kind == "charging_completed" for event in coordinator.events)
