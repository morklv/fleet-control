import type { Job } from "../types";

const stateLabels: Record<string, string> = {
  queued: "Queued",
  assigned: "Assigned",
  in_progress: "In progress",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

type Props = {
  jobs: Job[];
  pending: boolean;
  onCancel: (jobId: string) => void;
};

export function JobQueue({ jobs, pending, onCancel }: Props) {
  const ordered = [...jobs].reverse();

  return (
    <section className="data-panel job-queue">
      <div className="section-heading">
        <div>
          <span className="section-kicker">WORK ORDERS</span>
          <h2>Jobs</h2>
        </div>
        <span className="section-count">{jobs.length}</span>
      </div>

      {ordered.length ? (
        <div className="job-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Job</th>
                <th>Route</th>
                <th>Priority</th>
                <th>Robot</th>
                <th>Status</th>
                <th><span className="visually-hidden">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((job) => (
                <tr key={job.id}>
                  <td><strong>{job.id}</strong></td>
                  <td>
                    {job.pickup.x}.{job.pickup.y}
                    <span className="route-arrow">→</span>
                    {job.dropoff.x}.{job.dropoff.y}
                  </td>
                  <td>{job.priority}</td>
                  <td>{job.assigned_robot_id ?? "—"}</td>
                  <td>
                    <span className={`job-state ${job.state}`}>
                      {stateLabels[job.state] ?? job.state}
                    </span>
                  </td>
                  <td className="job-action">
                    {!["completed", "cancelled", "failed"].includes(job.state) && (
                      <button
                        disabled={pending}
                        onClick={() => onCancel(job.id)}
                        aria-label={`Cancel ${job.id}`}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-state">
          No jobs yet. Create a job from the dispatch panel to begin.
        </p>
      )}
    </section>
  );
}
