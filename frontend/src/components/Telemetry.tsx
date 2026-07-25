import type { FleetState } from "../types";

export function Telemetry({ state }: { state: FleetState }) {
  return (
    <section className="telemetry">
      <div className="metric">
        <span>ACTIVE UNITS</span>
        <strong>{state.metrics.active_robots.toString().padStart(2, "0")}</strong>
      </div>
      <div className="metric">
        <span>QUEUED JOBS</span>
        <strong>{state.metrics.queued_jobs.toString().padStart(2, "0")}</strong>
      </div>
      <div className="metric">
        <span>COMPLETED</span>
        <strong>{state.metrics.completed_jobs.toString().padStart(2, "0")}</strong>
      </div>
      <div className={`metric ${state.metrics.failed_robots ? "alert" : ""}`}>
        <span>DEGRADED</span>
        <strong>{state.metrics.failed_robots.toString().padStart(2, "0")}</strong>
      </div>
    </section>
  );
}
