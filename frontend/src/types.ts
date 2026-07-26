export type Position = { x: number; y: number };

export type Robot = {
  id: string;
  position: Position;
  state: string;
  current_job_id: string | null;
  path: Position[];
  wait_ticks: number;
  battery_level: number;
  battery_capacity: number;
  battery_percent: number;
  moves_to_charger: number | null;
  charging_station: Position | null;
};

export type Job = {
  id: string;
  pickup: Position;
  dropoff: Position;
  priority: number;
  state: string;
  assigned_robot_id: string | null;
  created_tick: number;
  assigned_tick: number | null;
  started_tick: number | null;
  completed_tick: number | null;
  cancelled_tick: number | null;
  elapsed_ticks: number;
};

export type FleetEvent = {
  tick: number;
  kind: string;
  message: string;
  robot_id: string | null;
  job_id: string | null;
};

export type RecurringMission = {
  id: string;
  robot_id: string;
  pickup: Position;
  dropoff: Position;
  priority: number;
  active: boolean;
  cycles_completed: number;
  current_job_id: string | null;
};

export type FleetState = {
  tick: number;
  running: boolean;
  warehouse: {
    width: number;
    height: number;
    obstacles: Position[];
    charging_stations: Position[];
  };
  robots: Robot[];
  jobs: Job[];
  missions: RecurringMission[];
  events: FleetEvent[];
  metrics: {
    completed_jobs: number;
    queued_jobs: number;
    active_robots: number;
    failed_robots: number;
    active_missions: number;
    robots_charging: number;
    average_battery: number;
    average_delivery_ticks: number;
  };
};

export type StrategyResult = {
  strategy: string;
  completed_jobs: number;
  total_ticks: number;
  average_delivery_ticks: number;
  waiting_events: number;
  charging_stops: number;
  throughput: number;
  efficiency_score: number;
};

export type BenchmarkComparison = {
  scenario: string;
  baseline: StrategyResult;
  optimized: StrategyResult;
  improvement: {
    throughput_percent: number;
    delivery_time_percent: number;
    waiting_percent: number;
    overall_efficiency_percent: number;
  };
  efficiency_formula: {
    throughput: number;
    delivery_speed: number;
    reduced_waiting: number;
    reduced_charging: number;
  };
};
