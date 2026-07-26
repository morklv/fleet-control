import type { FleetState } from "../types";

export function Telemetry({ state }: { state: FleetState }) {
  return (
    <section className="telemetry">
      <div className="metric">
        <span>ROBOTS ACTIVE</span>
        <strong>{state.metrics.active_robots.toString().padStart(2, "0")}</strong>
      </div>
      <div className="metric">
        <span>JOBS QUEUED</span>
        <strong>{state.metrics.queued_jobs.toString().padStart(2, "0")}</strong>
      </div>
      <div className="metric">
        <span>JOBS COMPLETED</span>
        <strong>{state.metrics.completed_jobs.toString().padStart(2, "0")}</strong>
      </div>
      <div className="metric">
        <span>AVG BATTERY</span>
        <strong>{state.metrics.average_battery}%</strong>
      </div>
      <div className="metric">
        <span>CHARGING</span>
        <strong>{state.metrics.robots_charging.toString().padStart(2, "0")}</strong>
      </div>
      <div className={`metric ${state.metrics.failed_robots ? "alert" : ""}`}>
        <span>ROBOT FAULTS</span>
        <strong>{state.metrics.failed_robots.toString().padStart(2, "0")}</strong>
      </div>
    </section>
  );
}
