from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count

from fleet_control.domain import Position, WarehouseMap


@dataclass(frozen=True, slots=True)
class PathNotFound(ValueError):
    start: Position
    goal: Position

    def __str__(self) -> str:
        return f"no traversable path from {self.start} to {self.goal}"


def _reconstruct_path(
    came_from: dict[Position, Position],
    current: Position,
) -> list[Position]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def find_path(
    warehouse: WarehouseMap,
    start: Position,
    goal: Position,
) -> list[Position]:
    """Return the shortest traversable path, including start and goal."""
    if not warehouse.is_traversable(start) or not warehouse.is_traversable(goal):
        raise PathNotFound(start, goal)
    if start == goal:
        return [start]

    sequence = count()
    frontier: list[tuple[int, int, Position]] = []
    heappush(frontier, (start.manhattan_distance(goal), next(sequence), start))

    came_from: dict[Position, Position] = {}
    cost_to_reach = {start: 0}

    while frontier:
        _, _, current = heappop(frontier)

        if current == goal:
            return _reconstruct_path(came_from, current)

        for neighbor in warehouse.neighbors(current):
            candidate_cost = cost_to_reach[current] + 1
            if candidate_cost >= cost_to_reach.get(neighbor, candidate_cost + 1):
                continue

            cost_to_reach[neighbor] = candidate_cost
            came_from[neighbor] = current
            estimated_total = candidate_cost + neighbor.manhattan_distance(goal)
            heappush(frontier, (estimated_total, next(sequence), neighbor))

    raise PathNotFound(start, goal)
