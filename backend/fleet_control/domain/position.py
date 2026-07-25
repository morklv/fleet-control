from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True, slots=True)
class Position:
    """An immutable cell in the warehouse coordinate system."""

    x: int
    y: int

    def manhattan_distance(self, other: Position) -> int:
        """Return four-directional grid distance without considering obstacles."""

        return abs(self.x - other.x) + abs(self.y - other.y)

