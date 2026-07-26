import { useMemo, useState } from "react";

import { createMission, stopMission } from "../api";
import { mapLocations } from "../stations";
import type { FleetState } from "../types";

type Props = {
  state: FleetState;
  onError: (message: string) => void;
};

export function MissionPanel({ state, onError }: Props) {
  const [robotId, setRobotId] = useState("R-01");
  const [pickup, setPickup] = useState(0);
  const [dropoff, setDropoff] = useState(5);
  const [priority, setPriority] = useState(5);
  const [pending, setPending] = useState(false);
  const locations = useMemo(() => mapLocations(state.warehouse), [state.warehouse]);

  async function start() {
    if (pickup === dropoff) {
      onError("Mission pickup and drop-off must be different.");
      return;
    }
    setPending(true);
    try {
      await createMission(
        robotId,
        locations[pickup].position,
        locations[dropoff].position,
        priority,
      );
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to start mission");
    } finally {
      setPending(false);
    }
  }

  async function stop(missionId: string) {
    setPending(true);
    try {
      await stopMission(missionId);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to stop mission");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="data-panel mission-panel">
      <div className="section-heading">
        <div>
          <span className="section-kicker">AUTOMATED ROUTES</span>
          <h2>Recurring missions</h2>
        </div>
        <span className="section-count">{state.metrics.active_missions}</span>
      </div>

      <div className="mission-form">
        <label>
          Robot
          <select value={robotId} onChange={(event) => setRobotId(event.target.value)}>
            {state.robots.map((robot) => (
              <option key={robot.id} value={robot.id}>{robot.id}</option>
            ))}
          </select>
        </label>
        <label>
          Pickup
          <select value={pickup} onChange={(event) => setPickup(+event.target.value)}>
            {locations.map((location, index) => (
              <option key={location.label} value={index}>{location.label}</option>
            ))}
          </select>
        </label>
        <label>
          Drop-off
          <select value={dropoff} onChange={(event) => setDropoff(+event.target.value)}>
            {locations.map((location, index) => (
              <option key={location.label} value={index}>{location.label}</option>
            ))}
          </select>
        </label>
        <label>
          Traffic priority <output>{priority}</output>
          <input
            type="range"
            min="0"
            max="10"
            value={priority}
            onChange={(event) => setPriority(+event.target.value)}
          />
        </label>
        <button className="primary-action" disabled={pending} onClick={start}>
          Start recurring mission <span>↻</span>
        </button>
      </div>

      <div className="mission-list">
        {state.missions.map((mission) => (
          <div className="mission-row" key={mission.id}>
            <strong>{mission.robot_id}</strong>
            <span>
              {mission.pickup.x}.{mission.pickup.y} → {mission.dropoff.x}.{mission.dropoff.y}
            </span>
            <span>{mission.cycles_completed} cycles</span>
            <span className={mission.active ? "mission-active" : ""}>
              {mission.active ? "Active" : "Stopped"}
            </span>
            {mission.active && (
              <button disabled={pending} onClick={() => stop(mission.id)}>
                Stop
              </button>
            )}
          </div>
        ))}
        {!state.missions.length && (
          <p className="empty-state">Assign a robot to repeat a route continuously.</p>
        )}
      </div>
    </section>
  );
}
