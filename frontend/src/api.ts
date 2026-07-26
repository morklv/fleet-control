import type { BenchmarkComparison, FleetState, Position } from "./types";

export async function createJob(
  pickup: Position,
  dropoff: Position,
  priority: number,
): Promise<void> {
  const response = await fetch("/api/jobs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ pickup, dropoff, priority }),
  });
  if (!response.ok) {
    const payload = (await response.json()) as { detail?: string };
    throw new Error(payload.detail ?? "Unable to create job");
  }
}

export async function command(path: string): Promise<void> {
  const response = await fetch(path, { method: "POST" });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(payload.detail ?? "Command failed");
  }
}

export async function cancelJob(jobId: string): Promise<void> {
  await command(`/api/jobs/${jobId}/cancel`);
}

export async function createMission(
  robotId: string,
  pickup: Position,
  dropoff: Position,
  priority: number,
): Promise<void> {
  const response = await fetch("/api/missions", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ robot_id: robotId, pickup, dropoff, priority }),
  });
  if (!response.ok) {
    const payload = (await response.json()) as { detail?: string };
    throw new Error(payload.detail ?? "Unable to start mission");
  }
}

export async function stopMission(missionId: string): Promise<void> {
  await command(`/api/missions/${missionId}/stop`);
}

export async function runBenchmark(): Promise<BenchmarkComparison> {
  const response = await fetch("/api/benchmarks/schedulers");
  if (!response.ok) throw new Error("Unable to run scheduler benchmark");
  return response.json() as Promise<BenchmarkComparison>;
}

export function connectFleet(
  onState: (state: FleetState) => void,
  onConnection: (connected: boolean) => void,
): () => void {
  let socket: WebSocket | null = null;
  let reconnectTimer: number | undefined;
  let retry = 0;
  let disposed = false;

  async function loadSnapshot() {
    try {
      const response = await fetch("/api/state");
      if (response.ok) onState((await response.json()) as FleetState);
    } catch {
      // The WebSocket retry loop remains the source of connection status.
    }
  }

  function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/ws/fleet`);
    socket.onopen = () => {
      retry = 0;
      onConnection(true);
    };
    socket.onclose = () => {
      onConnection(false);
      if (!disposed) {
        const delay = Math.min(1000 * 2 ** retry++, 8000);
        reconnectTimer = window.setTimeout(connect, delay);
      }
    };
    socket.onerror = () => onConnection(false);
    socket.onmessage = (message) => {
      onState(JSON.parse(message.data) as FleetState);
    };
  }

  void loadSnapshot();
  connect();

  return () => {
    disposed = true;
    window.clearTimeout(reconnectTimer);
    socket?.close();
  };
}
