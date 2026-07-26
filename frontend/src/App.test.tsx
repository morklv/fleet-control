import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FleetState } from "./types";

const api = vi.hoisted(() => ({
  cancelJob: vi.fn(),
  command: vi.fn(),
  connectFleet: vi.fn(),
  createJob: vi.fn(),
  createMission: vi.fn(),
  runBenchmark: vi.fn(),
  stopMission: vi.fn(),
}));

vi.mock("./api", () => api);

import App from "./App";

const state: FleetState = {
  tick: 12,
  running: true,
  warehouse: {
    width: 4,
    height: 3,
    obstacles: [],
    charging_stations: [{ x: 0, y: 2 }],
  },
  robots: [
    {
      id: "R-01",
      position: { x: 0, y: 0 },
      state: "idle",
      current_job_id: null,
      path: [],
      wait_ticks: 0,
      battery_level: 82,
      battery_capacity: 100,
      battery_percent: 82,
      moves_to_charger: 2,
      charging_station: null,
    },
  ],
  jobs: [
    {
      id: "J-01",
      pickup: { x: 1, y: 0 },
      dropoff: { x: 3, y: 2 },
      priority: 5,
      state: "queued",
      assigned_robot_id: null,
      created_tick: 10,
      assigned_tick: null,
      started_tick: null,
      completed_tick: null,
      cancelled_tick: null,
      elapsed_ticks: 2,
    },
  ],
  missions: [],
  events: [],
  metrics: {
    completed_jobs: 0,
    queued_jobs: 1,
    active_robots: 0,
    failed_robots: 0,
    active_missions: 0,
    robots_charging: 0,
    average_battery: 82,
    average_delivery_ticks: 0,
  },
};

describe("Fleet Control dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.connectFleet.mockImplementation((onState, onConnection) => {
      onState(state);
      onConnection(true);
      return () => undefined;
    });
    api.command.mockResolvedValue(undefined);
    api.createJob.mockResolvedValue(undefined);
    api.cancelJob.mockResolvedValue(undefined);
    api.createMission.mockResolvedValue(undefined);
    api.runBenchmark.mockResolvedValue(undefined);
    api.stopMission.mockResolvedValue(undefined);
  });

  it("renders authoritative fleet state and job history", () => {
    render(<App />);

    expect(screen.getByText("Warehouse map")).toBeInTheDocument();
    expect(screen.getByText("J-01")).toBeInTheDocument();
    expect(screen.getByText("Queued")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("starts the automated demo", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Run demo" }));

    expect(api.command).toHaveBeenCalledWith("/api/simulation/demo");
  });

  it("dispatches and cancels jobs through the API", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Dispatch job →" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel J-01" }));

    expect(api.createJob).toHaveBeenCalledWith(
      { x: 2, y: 1 },
      { x: 0, y: 1 },
      5,
    );
    expect(api.cancelJob).toHaveBeenCalledWith("J-01");
  });

  it("starts a robot-specific recurring mission", () => {
    render(<App />);

    fireEvent.click(
      screen.getByRole("button", { name: "Start recurring mission ↻" }),
    );

    expect(api.createMission).toHaveBeenCalledWith(
      "R-01",
      { x: 2, y: 1 },
      { x: 0, y: 1 },
      5,
    );
  });
});
