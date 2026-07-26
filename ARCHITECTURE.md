# Architecture

## Runtime flow

```text
POST /api/jobs
      │
      ▼
FleetCoordinator.submit_job
      │
      ▼
priority queue ──► nearest available robot
      │
      ▼
A*(warehouse, robot.position, pickup)
      │
      ▼
tick loop ──► reservation check ──► one-cell movement
      │
      ├── pickup reached ──► loading ──► plan drop-off
      ├── drop-off reached ──► unloading ──► completed
      └── failure ──► clear path ──► requeue job

Every tick serializes the authoritative state to WebSocket clients and
checkpoints it to SQLite, so jobs, events, robot positions, and simulation
status survive backend restarts.

Recurring missions generate a new robot-pinned job after every completed cycle.
Mission robots are reserved from general scheduling. When routes conflict,
effective job priority determines right-of-way, waiting time prevents
starvation, and repeatedly blocked robots attempt a dynamic A* replan around
current traffic.

Before each pickup or delivery leg, energy management calculates:

`required energy = remaining leg + destination-to-charger route + safety reserve`

If the battery cannot safely cover that budget, the robot stores its work phase,
routes to the nearest reachable charger, charges to full capacity, and rebuilds
the interrupted route. Battery state and charging progress are included in
SQLite snapshots and WebSocket telemetry.
```

## Responsibilities

- `domain`: immutable positions and validated robot/job state.
- `planning`: reusable A* graph search.
- `application`: policies for assignment, ticks, reservations, and recovery.
- `api`: input validation, HTTP commands, and WebSocket broadcasting.
- `frontend`: visualization and operator commands; it owns no fleet truth.
- `persistence`: SQLite snapshots of the authoritative coordinator state.

## Domain invariants

1. A robot occupies exactly one traversable cell.
2. Two robots never occupy the same cell at the end of a tick.
3. A job belongs to at most one robot.
4. Failed robots hold no route or active job.
5. A completed job has reached its drop-off cell.
6. Robot state changes follow an explicit transition table.
7. A working robot preserves sufficient energy to reach a charger.

## Failure semantics

Failure is handled centrally by the coordinator. The active robot clears its
path, relinquishes the job, and enters `failed`. The job becomes `queued`, so the
normal scheduler—not a special recovery shortcut—assigns it to another robot.
That reuse keeps failure handling consistent with ordinary scheduling.
