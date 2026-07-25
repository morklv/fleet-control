import type { FleetState, Position } from "./types";

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
  if (!response.ok) throw new Error("Command failed");
}

export function connectFleet(
  onState: (state: FleetState) => void,
  onConnection: (connected: boolean) => void,
): () => void {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/fleet`);
  socket.onopen = () => onConnection(true);
  socket.onclose = () => onConnection(false);
  socket.onerror = () => onConnection(false);
  socket.onmessage = (message) => {
    onState(JSON.parse(message.data) as FleetState);
  };
  return () => socket.close();
}
