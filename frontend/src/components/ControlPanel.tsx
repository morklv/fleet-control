import { useState } from "react";

import { command, createJob } from "../api";
import type { FleetState, Position } from "../types";

const stations: Array<{ label: string; position: Position }> = [
  { label: "Inbound A / 02.01", position: { x: 2, y: 1 } },
  { label: "Inbound B / 15.01", position: { x: 15, y: 1 } },
  { label: "Storage W / 02.06", position: { x: 2, y: 6 } },
  { label: "Storage E / 15.06", position: { x: 15, y: 6 } },
  { label: "Dispatch A / 02.10", position: { x: 2, y: 10 } },
  { label: "Dispatch B / 15.10", position: { x: 15, y: 10 } },
];

type Props = {
  state: FleetState;
  selectedRobot: string | null;
  onError: (message: string) => void;
};

export function ControlPanel({ state, selectedRobot, onError }: Props) {
  const [pickup, setPickup] = useState(0);
  const [dropoff, setDropoff] = useState(5);
  const [priority, setPriority] = useState(5);
  const robot = state.robots.find((item) => item.id === selectedRobot);

  async function dispatch() {
    try {
      await createJob(
        stations[pickup].position,
        stations[dropoff].position,
        priority,
      );
    } catch (error) {
      onError(error instanceof Error ? error.message : "Dispatch failed");
    }
  }

  async function robotCommand(action: "fail" | "recover") {
    if (!robot) return;
    try {
      await command(`/api/robots/${robot.id}/${action}`);
    } catch {
      onError(`Unable to ${action} ${robot.id}`);
    }
  }

  return (
    <aside className="control-panel">
      <div className="panel-heading compact">
        <div>
          <span className="eyebrow">MISSION CONTROL</span>
          <h2>Dispatch</h2>
        </div>
        <span className="status-chip">AUTO</span>
      </div>

      <div className="control-block">
        <label>
          Pickup node
          <select value={pickup} onChange={(event) => setPickup(+event.target.value)}>
            {stations.map((station, index) => (
              <option value={index} key={station.label}>{station.label}</option>
            ))}
          </select>
        </label>
        <label>
          Delivery node
          <select value={dropoff} onChange={(event) => setDropoff(+event.target.value)}>
            {stations.map((station, index) => (
              <option value={index} key={station.label}>{station.label}</option>
            ))}
          </select>
        </label>
        <label>
          Priority / {priority.toString().padStart(2, "0")}
          <input
            type="range"
            min="0"
            max="10"
            value={priority}
            onChange={(event) => setPriority(+event.target.value)}
          />
        </label>
        <button className="primary-action" onClick={dispatch}>
          CREATE FULFILLMENT JOB <span>↗</span>
        </button>
      </div>

      <div className="selected-unit">
        <div className="section-label">SELECTED UNIT</div>
        {robot ? (
          <>
            <div className="unit-heading">
              <strong>{robot.id}</strong>
              <span className={`unit-state ${robot.state}`}>{robot.state.replaceAll("_", " ")}</span>
            </div>
            <dl>
              <div><dt>Position</dt><dd>{robot.position.x}.{robot.position.y}</dd></div>
              <div><dt>Active job</dt><dd>{robot.current_job_id ?? "—"}</dd></div>
              <div><dt>Route nodes</dt><dd>{robot.path.length}</dd></div>
              <div><dt>Wait ticks</dt><dd>{robot.wait_ticks}</dd></div>
            </dl>
            {robot.state === "failed" ? (
              <button className="secondary-action" onClick={() => robotCommand("recover")}>
                RECOVER UNIT
              </button>
            ) : (
              <button className="danger-action" onClick={() => robotCommand("fail")}>
                SIMULATE FAILURE
              </button>
            )}
          </>
        ) : (
          <p className="empty-copy">Select a robot on the floor to inspect or disrupt it.</p>
        )}
      </div>
    </aside>
  );
}
