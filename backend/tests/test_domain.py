import pytest

from fleet_control.domain import (
    InvalidRobotTransition,
    Job,
    JobState,
    Position,
    Robot,
    RobotState,
    WarehouseMap,
)


def test_manhattan_distance() -> None:
    assert Position(1, 2).manhattan_distance(Position(4, 6)) == 7


def test_warehouse_filters_boundaries_and_obstacles() -> None:
    warehouse = WarehouseMap(
        width=3,
        height=3,
        obstacles=frozenset({Position(1, 0)}),
    )

    assert warehouse.neighbors(Position(0, 0)) == (Position(0, 1),)


def test_robot_accepts_valid_state_transition() -> None:
    robot = Robot(id="R-01", position=Position(0, 0))

    robot.transition_to(RobotState.ASSIGNED)
    robot.transition_to(RobotState.PLANNING)

    assert robot.state is RobotState.PLANNING


def test_robot_rejects_invalid_state_transition() -> None:
    robot = Robot(id="R-01", position=Position(0, 0))

    with pytest.raises(InvalidRobotTransition):
        robot.transition_to(RobotState.MOVING_TO_DROPOFF)


def test_job_cannot_be_assigned_twice() -> None:
    job = Job(
        id="J-01",
        pickup=Position(1, 1),
        dropoff=Position(2, 2),
    )

    job.assign_to("R-01")

    assert job.state is JobState.ASSIGNED
    with pytest.raises(ValueError):
        job.assign_to("R-02")

