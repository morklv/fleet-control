from __future__ import annotations

from statistics import mean

from fleet_control.domain import Job, JobState, Position, Robot, WarehouseMap

from .coordinator import FleetCoordinator


BENCHMARK_JOBS = (
    ("B-01", Position(2, 1), Position(15, 10), 9),
    ("B-02", Position(15, 1), Position(2, 10), 8),
    ("B-03", Position(2, 10), Position(15, 1), 7),
    ("B-04", Position(15, 10), Position(2, 1), 6),
    ("B-05", Position(2, 6), Position(15, 6), 5),
    ("B-06", Position(15, 6), Position(2, 6), 4),
)


def run_scheduler_benchmark(strategy: str) -> dict[str, int | float | str]:
    shelves = {
        Position(x, y)
        for x in (4, 5, 8, 9, 12, 13)
        for y in range(2, 10)
        if y not in (5, 6)
    }
    coordinator = FleetCoordinator(
        WarehouseMap(18, 12, frozenset(shelves)),
        [
            Robot("R-01", Position(1, 1)),
            Robot("R-02", Position(3, 1)),
            Robot("R-03", Position(1, 10)),
            Robot("R-04", Position(16, 10)),
        ],
        charging_stations=(Position(0, 6), Position(17, 6)),
        scheduling_strategy=strategy,
    )
    for robot, battery in zip(
        coordinator.robots.values(),
        (30, 45, 70, 100),
        strict=True,
    ):
        robot.battery_level = battery
    maximum_ticks = 400
    pending = list(BENCHMARK_JOBS)
    for _ in range(maximum_ticks):
        active = any(
            job.state not in {JobState.COMPLETED, JobState.FAILED}
            for job in coordinator.jobs.values()
        )
        if pending and not active:
            job_id, pickup, dropoff, priority = pending.pop(0)
            coordinator.submit_job(
                Job(job_id, pickup, dropoff, priority=priority)
            )
        coordinator.tick()
        if not pending and all(
            job.state in {JobState.COMPLETED, JobState.FAILED}
            for job in coordinator.jobs.values()
        ):
            break

    completed = [
        job for job in coordinator.jobs.values()
        if job.state is JobState.COMPLETED
    ]
    delivery_times = [
        job.completed_tick - job.created_tick
        for job in completed
        if job.completed_tick is not None
    ]
    waits = sum(event.kind == "robot_waiting" for event in coordinator.events)
    charging_stops = sum(
        event.kind == "charging_required" for event in coordinator.events
    )
    return {
        "strategy": strategy,
        "completed_jobs": len(completed),
        "total_ticks": coordinator.tick_number,
        "average_delivery_ticks": round(mean(delivery_times), 1)
        if delivery_times
        else 0,
        "waiting_events": waits,
        "charging_stops": charging_stops,
        "throughput": round(
            len(completed) * 100 / max(1, coordinator.tick_number),
            2,
        ),
    }


def compare_schedulers() -> dict[str, object]:
    baseline = run_scheduler_benchmark("nearest")
    optimized = run_scheduler_benchmark("optimized")

    def efficiency_score(result: dict[str, int | float | str]) -> float:
        throughput = float(result["throughput"]) / float(baseline["throughput"])
        delivery = (
            float(baseline["average_delivery_ticks"])
            / float(result["average_delivery_ticks"])
        )
        waiting = (
            float(baseline["waiting_events"]) + 10
        ) / (float(result["waiting_events"]) + 10)
        charging = (
            float(baseline["charging_stops"]) + 5
        ) / (float(result["charging_stops"]) + 5)
        return round(
            100
            * (
                throughput * 0.50
                + delivery * 0.30
                + waiting * 0.10
                + charging * 0.10
            ),
            1,
        )

    baseline["efficiency_score"] = efficiency_score(baseline)
    optimized["efficiency_score"] = efficiency_score(optimized)

    def improvement(metric: str, *, lower_is_better: bool = False) -> float:
        old = float(baseline[metric])
        new = float(optimized[metric])
        if old == 0:
            return 0
        change = (old - new) / old if lower_is_better else (new - old) / old
        return round(change * 100, 1)

    return {
        "scenario": "Six fixed jobs, four robots, mixed starting batteries",
        "baseline": baseline,
        "optimized": optimized,
        "improvement": {
            "throughput_percent": improvement("throughput"),
            "delivery_time_percent": improvement(
                "average_delivery_ticks", lower_is_better=True
            ),
            "waiting_percent": improvement(
                "waiting_events", lower_is_better=True
            ),
            "overall_efficiency_percent": round(
                float(optimized["efficiency_score"])
                - float(baseline["efficiency_score"]),
                1,
            ),
        },
        "efficiency_formula": {
            "throughput": 50,
            "delivery_speed": 30,
            "reduced_waiting": 10,
            "reduced_charging": 10,
        },
    }
