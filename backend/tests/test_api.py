from fastapi.testclient import TestClient
from pathlib import Path

from fleet_control.api.app import create_app


def test_state_and_job_creation_api() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        initial = client.get("/api/state")
        assert initial.status_code == 200
        assert len(initial.json()["robots"]) == 4

        response = client.post(
            "/api/jobs",
            json={
                "pickup": {"x": 2, "y": 1},
                "dropoff": {"x": 15, "y": 10},
                "priority": 7,
            },
        )

        assert response.status_code == 201
        assert response.json()["state"] == "queued"
        assert len(client.get("/api/state").json()["jobs"]) == 1


def test_invalid_job_cell_is_rejected() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        response = client.post(
            "/api/jobs",
            json={
                "pickup": {"x": 4, "y": 2},
                "dropoff": {"x": 2, "y": 2},
            },
        )

        assert response.status_code == 422


def test_fail_and_recover_robot_api() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        assert client.post("/api/robots/R-01/fail").status_code == 200
        assert client.post("/api/robots/R-01/recover").status_code == 200


def test_simulation_controls_report_authoritative_state() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        assert client.get("/api/state").json()["running"] is True

        paused = client.post("/api/simulation/toggle")
        assert paused.status_code == 200
        assert paused.json() == {"running": False}
        assert client.get("/api/state").json()["running"] is False

        stepped = client.post("/api/simulation/step")
        assert stepped.status_code == 200
        assert stepped.json() == {"tick": 1}
        assert client.get("/api/state").json()["tick"] == 1

        client.post("/api/simulation/toggle")
        rejected = client.post("/api/simulation/step")
        assert rejected.status_code == 409


def test_job_cancellation_api() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        created = client.post(
            "/api/jobs",
            json={
                "pickup": {"x": 2, "y": 1},
                "dropoff": {"x": 15, "y": 10},
                "priority": 7,
            },
        ).json()
        cancelled = client.post(f"/api/jobs/{created['id']}/cancel")

        assert cancelled.status_code == 200
        assert cancelled.json()["state"] == "cancelled"


def test_demo_api_starts_three_jobs() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        response = client.post("/api/simulation/demo")
        state = client.get("/api/state").json()

        assert response.status_code == 200
        assert [job["id"] for job in state["jobs"]] == [
            "DEMO-01",
            "DEMO-02",
            "DEMO-03",
        ]
        assert state["running"] is True


def test_demo_automatically_fails_and_recovers_robot() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        client.post("/api/simulation/demo")
        client.post("/api/simulation/toggle")
        for _ in range(20):
            client.post("/api/simulation/step")
        events = client.get("/api/state").json()["events"]

        assert any(event["kind"] == "job_requeued" for event in events)
        assert any(event["kind"] == "robot_recovered" for event in events)


def test_sqlite_state_survives_application_restart(tmp_path: Path) -> None:
    database = tmp_path / "fleet-control.db"
    with TestClient(
        create_app(start_simulation=False, database_path=str(database))
    ) as client:
        created = client.post(
            "/api/jobs",
            json={
                "pickup": {"x": 2, "y": 1},
                "dropoff": {"x": 15, "y": 10},
                "priority": 8,
            },
        ).json()
        mission = client.post(
            "/api/missions",
            json={
                "robot_id": "R-03",
                "pickup": {"x": 2, "y": 10},
                "dropoff": {"x": 15, "y": 1},
                "priority": 4,
            },
        )
        assert mission.status_code == 201

    with TestClient(
        create_app(start_simulation=False, database_path=str(database))
    ) as client:
        state = client.get("/api/state").json()

    assert [job["id"] for job in state["jobs"]] == [created["id"]]
    assert state["jobs"][0]["priority"] == 8
    assert state["missions"][0]["robot_id"] == "R-03"


def test_recurring_mission_api_can_start_and_stop() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        created = client.post(
            "/api/missions",
            json={
                "robot_id": "R-02",
                "pickup": {"x": 15, "y": 1},
                "dropoff": {"x": 2, "y": 10},
                "priority": 6,
            },
        )
        mission_id = created.json()["id"]

        assert created.status_code == 201
        assert client.get("/api/state").json()["missions"][0]["robot_id"] == "R-02"
        stopped = client.post(f"/api/missions/{mission_id}/stop")
        assert stopped.status_code == 200
        assert stopped.json()["state"] == "stopped"


def test_scheduler_benchmark_api() -> None:
    with TestClient(create_app(start_simulation=False)) as client:
        response = client.get("/api/benchmarks/schedulers")

    assert response.status_code == 200
    assert response.json()["optimized"]["completed_jobs"] == 6
