from __future__ import annotations

from fleet_control.application import FleetCoordinator
from fleet_control.domain import Position


def serialize_position(position: Position) -> dict[str, int]:
    return {"x": position.x, "y": position.y}


def serialize_state(coordinator: FleetCoordinator) -> dict:
    return {
        "tick": coordinator.tick_number,
        "warehouse": {
            "width": coordinator.warehouse.width,
            "height": coordinator.warehouse.height,
            "obstacles": [
                serialize_position(position)
                for position in sorted(coordinator.warehouse.obstacles)
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
            }
            for job in sorted(coordinator.jobs.values(), key=lambda item: item.id)
        ],
        "events": [
            {
                "tick": event.tick,
                "kind": event.kind,
                "message": event.message,
                "robot_id": event.robot_id,
                "job_id": event.job_id,
            }
            for event in coordinator.events[-40:]
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
        },
    }
