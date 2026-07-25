from fastapi.testclient import TestClient

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
