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

Every tick serializes the authoritative state to WebSocket clients.
```

## Responsibilities

- `domain`: immutable positions and validated robot/job state.
- `planning`: reusable A* graph search.
- `application`: policies for assignment, ticks, reservations, and recovery.
- `api`: input validation, HTTP commands, and WebSocket broadcasting.
- `frontend`: visualization and operator commands; it owns no fleet truth.

## Domain invariants

1. A robot occupies exactly one traversable cell.
2. Two robots never occupy the same cell at the end of a tick.
3. A job belongs to at most one robot.
4. Failed robots hold no route or active job.
5. A completed job has reached its drop-off cell.
6. Robot state changes follow an explicit transition table.

## Failure semantics

Failure is handled centrally by the coordinator. The active robot clears its
path, relinquishes the job, and enters `failed`. The job becomes `queued`, so the
normal scheduler—not a special recovery shortcut—assigns it to another robot.
That reuse keeps failure handling consistent with ordinary scheduling.
