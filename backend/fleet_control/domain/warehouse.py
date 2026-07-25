from __future__ import annotations

from dataclasses import dataclass, field

from .position import Position


CARDINAL_OFFSETS = ((1, 0), (0, 1), (-1, 0), (0, -1))


@dataclass(frozen=True, slots=True)
class WarehouseMap:
    width: int
    height: int
    obstacles: frozenset[Position] = field(default_factory=frozenset)

    def contains(self, position: Position) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height

    def is_traversable(self, position: Position) -> bool:
        return self.contains(position) and position not in self.obstacles

    def neighbors(self, position: Position) -> tuple[Position, ...]:
        candidates = (
            Position(position.x + dx, position.y + dy)
            for dx, dy in CARDINAL_OFFSETS
        )
        return tuple(candidate for candidate in candidates if self.is_traversable(candidate))

