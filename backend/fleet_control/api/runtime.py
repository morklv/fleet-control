from __future__ import annotations

from fleet_control.application import FleetCoordinator
from fleet_control.domain import Position, Robot, WarehouseMap


def build_demo_coordinator() -> FleetCoordinator:
    shelf_cells = {
        Position(x, y)
        for x in (4, 5, 8, 9, 12, 13)
        for y in range(2, 10)
        if y not in (5, 6)
    }
    warehouse = WarehouseMap(
        width=18,
        height=12,
        obstacles=frozenset(shelf_cells),
    )
    robots = [
        Robot("R-01", Position(1, 1)),
        Robot("R-02", Position(16, 1)),
        Robot("R-03", Position(1, 10)),
        Robot("R-04", Position(16, 10)),
    ]
    return FleetCoordinator(warehouse, robots)
