from __future__ import annotations

from fleet_control.application import FleetCoordinator
from fleet_control.domain import Position


def serialize_position(position: Position) -> dict[str, int]:
    return {"x": position.x, "y": position.y}


def serialize_state(
    coordinator: FleetCoordinator,
    *,
    running: bool = True,
    event_limit: int | None = 40,
) -> dict:
    events = (
        coordinator.events[-event_limit:]
        if event_limit is not None
        else coordinator.events
    )
    return {
        "tick": coordinator.tick_number,
        "running": running,
        "warehouse": {
            "width": coordinator.warehouse.width,
            "height": coordinator.warehouse.height,
            "obstacles": [
                serialize_position(position)
                for position in sorted(coordinator.warehouse.obstacles)
            ],
            "charging_stations": [
                serialize_position(position)
                for position in coordinator.charging_stations
            ],
        },
        "robots": [
            {
                "id": robot.id,
                "position": serialize_position(robot.position),
                "state": robot.state.value,
                "current_job_id": robot.current_job_id,
                "path": [serialize_position(position) for position in robot.path],
                "wait_ticks": robot.wait_ticks,
                "battery_level": robot.battery_level,
                "battery_capacity": robot.battery_capacity,
                "battery_percent": robot.battery_percent,
                "moves_to_charger": (
                    len(robot.path)
                    if robot.state.value == "moving_to_charger"
                    else coordinator._distance_to_nearest_charger(robot.position)
                    if coordinator.charging_stations
                    else None
                ),
                "charging_station": (
                    serialize_position(robot.charging_station)
                    if robot.charging_station is not None
                    else None
                ),
            }
            for robot in sorted(coordinator.robots.values(), key=lambda item: item.id)
        ],
        "jobs": [
            {
                "id": job.id,
                "pickup": serialize_position(job.pickup),
                "dropoff": serialize_position(job.dropoff),
                "priority": job.priority,
                "state": job.state.value,
                "assigned_robot_id": job.assigned_robot_id,
                "created_tick": job.created_tick,
                "assigned_tick": job.assigned_tick,
                "started_tick": job.started_tick,
                "completed_tick": job.completed_tick,
                "cancelled_tick": job.cancelled_tick,
                "required_robot_id": job.required_robot_id,
                "mission_id": job.mission_id,
                "elapsed_ticks": (
                    (job.completed_tick or job.cancelled_tick or coordinator.tick_number)
                    - job.created_tick
                ),
            }
            for job in sorted(coordinator.jobs.values(), key=lambda item: item.id)
        ],
        "missions": [
            {
                "id": mission.id,
                "robot_id": mission.robot_id,
                "pickup": serialize_position(mission.pickup),
                "dropoff": serialize_position(mission.dropoff),
                "priority": mission.priority,
                "active": mission.active,
                "cycles_completed": mission.cycles_completed,
                "current_job_id": mission.current_job_id,
            }
            for mission in sorted(
                coordinator.missions.values(), key=lambda item: item.id
            )
        ],
        "events": [
            {
                "tick": event.tick,
                "kind": event.kind,
                "message": event.message,
                "robot_id": event.robot_id,
                "job_id": event.job_id,
            }
            for event in events
        ],
        "metrics": {
            "completed_jobs": sum(
                job.state.value == "completed" for job in coordinator.jobs.values()
            ),
            "queued_jobs": sum(
                job.state.value == "queued" for job in coordinator.jobs.values()
            ),
            "active_robots": sum(
                robot.state.value not in {"idle", "failed"}
                for robot in coordinator.robots.values()
            ),
            "failed_robots": sum(
                robot.state.value == "failed"
                for robot in coordinator.robots.values()
            ),
            "active_missions": sum(
                mission.active for mission in coordinator.missions.values()
            ),
            "robots_charging": sum(
                robot.state.value in {"moving_to_charger", "charging"}
                for robot in coordinator.robots.values()
            ),
            "average_battery": round(
                sum(robot.battery_percent for robot in coordinator.robots.values())
                / len(coordinator.robots)
            ),
            "average_delivery_ticks": round(
                sum(
                    job.completed_tick - job.created_tick
                    for job in coordinator.jobs.values()
                    if job.completed_tick is not None
                )
                / max(
                    1,
                    sum(
                        job.completed_tick is not None
                        for job in coordinator.jobs.values()
                    ),
                ),
                1,
            ),
        },
    }
