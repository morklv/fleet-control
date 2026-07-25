export type Position = { x: number; y: number };

export type Robot = {
  id: string;
  position: Position;
  state: string;
  current_job_id: string | null;
  path: Position[];
  wait_ticks: number;
};

export type Job = {
  id: string;
  pickup: Position;
  dropoff: Position;
  priority: number;
  state: string;
  assigned_robot_id: string | null;
};

export type FleetEvent = {
  tick: number;
  kind: string;
  message: string;
  robot_id: string | null;
  job_id: string | null;
};

export type FleetState = {
  tick: number;
  warehouse: {
    width: number;
    height: number;
    obstacles: Position[];
  };
  robots: Robot[];
  jobs: Job[];
  events: FleetEvent[];
  metrics: {
    completed_jobs: number;
    queued_jobs: number;
    active_robots: number;
    failed_robots: number;
  };
};
