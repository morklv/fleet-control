from fleet_control.application import compare_schedulers


def test_scheduler_benchmark_is_reproducible_and_compares_same_workload() -> None:
    first = compare_schedulers()
    second = compare_schedulers()

    assert first == second
    assert first["baseline"]["completed_jobs"] == 6
    assert first["optimized"]["completed_jobs"] == 6
    assert first["optimized"]["throughput"] > first["baseline"]["throughput"]
    assert first["baseline"]["efficiency_score"] == 100
    assert first["optimized"]["efficiency_score"] > 100
