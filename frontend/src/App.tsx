import { useEffect, useState } from "react";

import { cancelJob, command, connectFleet } from "./api";
import { ControlPanel } from "./components/ControlPanel";
import { BenchmarkPanel } from "./components/BenchmarkPanel";
import { EventFeed } from "./components/EventFeed";
import { JobQueue } from "./components/JobQueue";
import { MissionPanel } from "./components/MissionPanel";
import { Telemetry } from "./components/Telemetry";
import { WarehouseView } from "./components/WarehouseView";
import type { FleetState } from "./types";

export default function App() {
  const [state, setState] = useState<FleetState | null>(null);
  const [connected, setConnected] = useState(false);
  const [selectedRobot, setSelectedRobot] = useState<string | null>("R-01");
  const [error, setError] = useState("");
  const [commandPending, setCommandPending] = useState(false);

  useEffect(() => connectFleet(setState, setConnected), []);

  async function toggle() {
    await runCommand("/api/simulation/toggle");
  }

  async function reset() {
    await runCommand("/api/simulation/reset");
  }

  async function step() {
    await runCommand("/api/simulation/step");
  }

  async function demo() {
    await runCommand("/api/simulation/demo");
  }

  async function cancel(jobId: string) {
    setCommandPending(true);
    try {
      await cancelJob(jobId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to cancel job");
    } finally {
      setCommandPending(false);
    }
  }

  async function runCommand(path: string) {
    setCommandPending(true);
    try {
      await command(path);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Command failed");
    } finally {
      setCommandPending(false);
    }
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
          <div className="brand-mark" aria-hidden="true">FC</div>
          <div>
            <strong>FLEET CONTROL</strong>
            <small>WAREHOUSE AUTONOMY</small>
          </div>
        </div>
        <div className="header-actions">
          <span className={`connection ${connected ? "online" : ""}`}>
            <i /> {connected ? "Connected" : "Reconnecting"}
          </span>
          <button disabled={commandPending} onClick={demo}>Run demo</button>
          <button disabled={commandPending} onClick={toggle}>
            {state.running ? "Pause simulation" : "Resume simulation"}
          </button>
          {!state.running && (
            <button disabled={commandPending} onClick={step}>Advance one tick</button>
          )}
          <button disabled={commandPending} onClick={reset}>Reset</button>
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

      <MissionPanel state={state} onError={setError} />
      <BenchmarkPanel onError={setError} />

      <div className="data-grid">
        <JobQueue
          jobs={state.jobs}
          pending={commandPending}
          onCancel={cancel}
        />
        <EventFeed events={state.events} />
      </div>

      {error && (
        <button className="error-toast" onClick={() => setError("")}>
          {error} <span>×</span>
        </button>
      )}
    </main>
  );
}
