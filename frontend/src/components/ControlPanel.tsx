import { useMemo, useState } from "react";

import { command, createJob } from "../api";
import { mapLocations } from "../stations";
import type { FleetState } from "../types";

type Props = {
  state: FleetState;
  selectedRobot: string | null;
  onError: (message: string) => void;
};

export function ControlPanel({ state, selectedRobot, onError }: Props) {
  const [pickup, setPickup] = useState(0);
  const [dropoff, setDropoff] = useState(5);
  const [priority, setPriority] = useState(5);
  const [pending, setPending] = useState(false);
  const locations = useMemo(() => mapLocations(state.warehouse), [state.warehouse]);
  const robot = state.robots.find((item) => item.id === selectedRobot);
  const job = state.jobs.find((item) => item.id === robot?.current_job_id);
  const destination = !job
    ? "None"
    : robot?.state === "moving_to_pickup"
      ? `${job.pickup.x}.${job.pickup.y} pickup`
      : `${job.dropoff.x}.${job.dropoff.y} drop-off`;

  async function dispatch() {
    if (pickup === dropoff) {
      onError("Pickup and drop-off must be different.");
      return;
    }
    setPending(true);
    try {
      await createJob(
        locations[pickup].position,
        locations[dropoff].position,
        priority,
      );
    } catch (error) {
      onError(error instanceof Error ? error.message : "Dispatch failed");
    } finally {
      setPending(false);
    }
  }

  async function robotCommand(action: "fail" | "recover") {
    if (!robot) return;
    setPending(true);
    try {
      await command(`/api/robots/${robot.id}/${action}`);
    } catch (error) {
      onError(error instanceof Error ? error.message : `Unable to ${action} ${robot.id}`);
    } finally {
      setPending(false);
    }
  }

  return (
    <aside className="control-panel">
      <div className="panel-heading compact">
        <div>
          <span className="section-kicker">MISSION PLANNING</span>
          <h2>New job</h2>
        </div>
      </div>

      <div className="control-block">
        <p className="panel-copy">
          Choose where the closest available robot should collect and deliver a load.
        </p>
        <label>
          Pickup location
          <select value={pickup} onChange={(event) => setPickup(+event.target.value)}>
            {locations.map((location, index) => (
              <option value={index} key={location.label}>{location.label}</option>
            ))}
          </select>
        </label>
        <label>
          Drop-off location
          <select value={dropoff} onChange={(event) => setDropoff(+event.target.value)}>
            {locations.map((location, index) => (
              <option value={index} key={location.label}>{location.label}</option>
            ))}
          </select>
        </label>
        <label>
          Priority <output>{priority}</output>
          <input
            type="range"
            min="0"
            max="10"
            value={priority}
            onChange={(event) => setPriority(+event.target.value)}
          />
        </label>
        <button className="primary-action" disabled={pending} onClick={dispatch}>
          {pending ? "Sending…" : "Dispatch job"} <span>→</span>
        </button>
      </div>

      <div className="selected-unit">
        <div className="section-label">ROBOT DETAILS</div>
        {robot ? (
          <>
            <div className="unit-heading">
              <strong>{robot.id}</strong>
              <span className={`unit-state ${robot.state}`}>{robot.state.replaceAll("_", " ")}</span>
            </div>
            <dl>
              <div><dt>Grid position</dt><dd>{robot.position.x}.{robot.position.y}</dd></div>
              <div><dt>Current job</dt><dd>{robot.current_job_id ?? "None"}</dd></div>
              <div><dt>Destination</dt><dd>{destination}</dd></div>
              <div><dt>Steps remaining</dt><dd>{robot.path.length}</dd></div>
              <div><dt>Job elapsed</dt><dd>{job ? `${job.elapsed_ticks} ticks` : "—"}</dd></div>
              <div><dt>Ticks waiting</dt><dd>{robot.wait_ticks}</dd></div>
              <div>
                <dt>Battery</dt>
                <dd className={robot.battery_percent <= 25 ? "battery-low" : ""}>
                  {robot.battery_percent}% · {robot.battery_level} moves
                </dd>
              </div>
              <div>
                <dt>Nearest charger</dt>
                <dd>{robot.moves_to_charger ?? "—"} moves</dd>
              </div>
            </dl>
            {robot.state === "failed" ? (
              <button disabled={pending} className="secondary-action" onClick={() => robotCommand("recover")}>
                Return robot to service
              </button>
            ) : (
              <button disabled={pending} className="danger-action" onClick={() => robotCommand("fail")}>
                Simulate robot fault
              </button>
            )}
          </>
        ) : (
          <p className="empty-state">Select a robot on the map to inspect it.</p>
        )}
      </div>
    </aside>
  );
}
