# Fleet Control

[Live demo](http://52.25.23.81:8080) · [Architecture notes](ARCHITECTURE.md)

## Demo video

[▶ Watch the Fleet Control demo](docs/fleet-control-demo.mov)

[![Watch the Fleet Control demo](docs/fleet-control-dashboard.png)](docs/fleet-control-demo.mov)

*The image also opens the main demo.*

Fleet Control is a small multi-robot warehouse simulation built to explore fleet
scheduling, path planning, traffic coordination, and battery management. It is
an educational simulator, not a production robot controller or ROS system.

## What it demonstrates

- A* path planning around warehouse obstacles
- Automatic and robot-specific recurring job assignment
- Collision avoidance with cell/edge reservations, priority, and yielding
- Battery-aware routing to charging stations, followed by job resumption
- Robot failure, job requeue, and recovery
- A reproducible comparison of nearest-robot and traffic-and-energy-aware scheduling
- Live REST/WebSocket state updates with 2D and 3D visualization
- SQLite persistence, automated tests, Docker, GitHub Actions, and AWS EC2 deployment

## Results and observability

| Scheduler comparison | Traffic decisions |
|---|---|
| ![Scheduler benchmark](docs/scheduler-benchmark.png) | ![Traffic event log](docs/traffic-event-log.png) |

## Architecture

```text
React + TypeScript
        │ REST / WebSocket
        ▼
Python + FastAPI
        │
FleetCoordinator
  ├── scheduling
  ├── A* routing
  ├── traffic safety
  └── energy management
        │
      SQLite
```

The coordinator owns the simulation state. The frontend visualizes that state
and sends operator commands; it does not control robot behavior directly.

## Run locally

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
python -m uvicorn fleet_control.api.app:app --app-dir backend --reload --port 8100
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`, or run the containerized version with:

```bash
docker compose up --build
```

## Verification

```bash
python -m pytest backend/tests -q
cd frontend && npm test && npm run build
```

## Interview discussion

The main design choices I would discuss are why A* is appropriate for the grid,
how the robot state machine prevents invalid transitions, how reservation-based
traffic handling avoids collisions, how charging decisions preserve an energy
reserve, and how the deterministic benchmark compares schedulers fairly.
