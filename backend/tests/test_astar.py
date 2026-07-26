import pytest

from fleet_control.domain import Position, WarehouseMap
from fleet_control.planning import PathNotFound, find_path


def test_astar_finds_direct_shortest_path() -> None:
    warehouse = WarehouseMap(width=5, height=5)

    path = find_path(warehouse, Position(0, 0), Position(3, 0))

    assert path == [
        Position(0, 0),
        Position(1, 0),
        Position(2, 0),
        Position(3, 0),
    ]


def test_astar_routes_around_obstacles() -> None:
    warehouse = WarehouseMap(
        width=5,
        height=3,
        obstacles=frozenset({Position(1, 0), Position(2, 0)}),
    )

    path = find_path(warehouse, Position(0, 0), Position(3, 0))

    assert path[0] == Position(0, 0)
    assert path[-1] == Position(3, 0)
    assert len(path) == 6
    assert not set(path) & warehouse.obstacles


def test_astar_returns_single_position_when_already_at_goal() -> None:
    warehouse = WarehouseMap(width=2, height=2)

    assert find_path(warehouse, Position(1, 1), Position(1, 1)) == [
        Position(1, 1)
    ]


def test_astar_raises_when_goal_is_blocked() -> None:
    goal = Position(1, 1)
    warehouse = WarehouseMap(width=3, height=3, obstacles=frozenset({goal}))

    with pytest.raises(PathNotFound):
        find_path(warehouse, Position(0, 0), goal)


def test_astar_raises_when_destination_is_unreachable() -> None:
    warehouse = WarehouseMap(
        width=3,
        height=3,
        obstacles=frozenset(
            {Position(0, 1), Position(1, 1), Position(2, 1)}
        ),
    )

    with pytest.raises(PathNotFound):
        find_path(warehouse, Position(0, 0), Position(2, 2))


def test_astar_can_avoid_temporary_traffic_cells() -> None:
    warehouse = WarehouseMap(width=3, height=3)

    path = find_path(
        warehouse,
        Position(0, 1),
        Position(2, 1),
        blocked=frozenset({Position(1, 1)}),
    )

    assert Position(1, 1) not in path
    assert len(path) == 5
