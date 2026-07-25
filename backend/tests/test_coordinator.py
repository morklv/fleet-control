from fleet_control.application import FleetCoordinator
from fleet_control.domain import (
    Job,
    JobState,
    Position,
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
