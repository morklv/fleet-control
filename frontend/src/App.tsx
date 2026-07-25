import { useEffect, useState } from "react";

import { command, connectFleet } from "./api";
import { ControlPanel } from "./components/ControlPanel";
import { EventFeed } from "./components/EventFeed";
import { Telemetry } from "./components/Telemetry";
import { WarehouseView } from "./components/WarehouseView";
import type { FleetState } from "./types";

export default function App() {
  const [state, setState] = useState<FleetState | null>(null);
  const [connected, setConnected] = useState(false);
  const [selectedRobot, setSelectedRobot] = useState<string | null>("R-01");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(true);

  useEffect(() => connectFleet(setState, setConnected), []);

  async function toggle() {
    await command("/api/simulation/toggle");
    setRunning((current) => !current);
  }

  async function reset() {
    await command("/api/simulation/reset");
    setRunning(true);
  }

  if (!state) {
    return (
      <main className="loading-screen">
        <div className="scanner" />
        <span>ESTABLISHING FLEET UPLINK</span>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header>
        <div className="brand">
          <div className="brand-mark"><span /><span /><span /></div>
          <div>
            <strong>FLEET CONTROL</strong>
            <small>AUTONOMOUS FULFILLMENT SYSTEM</small>
          </div>
        </div>
        <div className="header-actions">
          <span className={`connection ${connected ? "online" : ""}`}>
            <i /> {connected ? "LIVE LINK" : "LINK LOST"}
          </span>
          <button onClick={toggle}>{running ? "PAUSE" : "RESUME"}</button>
          <button onClick={reset}>RESET</button>
        </div>
      </header>

      <Telemetry state={state} />

      <div className="workspace">
        <WarehouseView
          state={state}
          selectedRobot={selectedRobot}
          onSelectRobot={setSelectedRobot}
        />
        <ControlPanel
          state={state}
          selectedRobot={selectedRobot}
          onError={setError}
        />
      </div>

      <EventFeed events={state.events} />

      {error && (
        <button className="error-toast" onClick={() => setError("")}>
          {error} <span>×</span>
        </button>
      )}
    </main>
  );
}
