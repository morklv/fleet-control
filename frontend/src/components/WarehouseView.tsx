import { lazy, Suspense, useState } from "react";

import type { FleetState } from "../types";

const Warehouse3D = lazy(() =>
  import("./Warehouse3D").then((module) => ({ default: module.Warehouse3D })),
);

type Props = {
  state: FleetState;
  selectedRobot: string | null;
  onSelectRobot: (id: string) => void;
};

function key(x: number, y: number): string {
  return `${x}:${y}`;
}

export function WarehouseView({
  state,
  selectedRobot,
  onSelectRobot,
}: Props) {
  const [view, setView] = useState<"2d" | "3d">("2d");
  const obstacles = new Set(
    state.warehouse.obstacles.map(({ x, y }) => key(x, y)),
  );
  const path = new Set(
    state.robots
      .find((robot) => robot.id === selectedRobot)
      ?.path.map(({ x, y }) => key(x, y)) ?? [],
  );

  return (
    <section className="warehouse-panel">
      <div className="panel-heading">
        <div>
          <span className="section-kicker">LIVE POSITION DATA</span>
          <h2>Warehouse map</h2>
        </div>
        <div className="map-actions">
          <div className="view-toggle" aria-label="Warehouse view">
            <button
              className={view === "2d" ? "active" : ""}
              aria-pressed={view === "2d"}
              onClick={() => setView("2d")}
            >
              2D
            </button>
            <button
              className={view === "3d" ? "active" : ""}
              aria-pressed={view === "3d"}
              onClick={() => setView("3d")}
            >
              3D
            </button>
          </div>
          <span className="coordinates">
            Tick {state.tick.toString().padStart(5, "0")}
          </span>
        </div>
      </div>

      {view === "3d" ? (
        <Suspense fallback={<div className="warehouse-3d-loading">Loading 3D view…</div>}>
          <Warehouse3D
            state={state}
            selectedRobot={selectedRobot}
            onSelectRobot={onSelectRobot}
          />
        </Suspense>
      ) : <div
        className="warehouse"
        style={{
          "--columns": state.warehouse.width,
          "--rows": state.warehouse.height,
        } as React.CSSProperties}
      >
        {Array.from({
          length: state.warehouse.width * state.warehouse.height,
        }).map((_, index) => {
          const x = index % state.warehouse.width;
          const y = Math.floor(index / state.warehouse.width);
          const cellKey = key(x, y);
          return (
            <div
              className={[
                "cell",
                obstacles.has(cellKey) ? "shelf" : "",
                path.has(cellKey) ? "route" : "",
              ].join(" ")}
              key={cellKey}
            />
          );
        })}

        {state.jobs
          .filter((job) => job.state !== "completed")
          .flatMap((job) => [
            <div
              className="job-marker pickup"
              key={`${job.id}-pickup`}
              title={`${job.id} pickup`}
              style={{
                "--x": job.pickup.x,
                "--y": job.pickup.y,
              } as React.CSSProperties}
            />,
            <div
              className="job-marker dropoff"
              key={`${job.id}-dropoff`}
              title={`${job.id} dropoff`}
              style={{
                "--x": job.dropoff.x,
                "--y": job.dropoff.y,
              } as React.CSSProperties}
            />,
          ])}

        {state.warehouse.charging_stations.map((station) => (
          <div
            className="charging-station"
            key={`charger-${station.x}-${station.y}`}
            title={`Charging station ${station.x}.${station.y}`}
            style={{
              "--x": station.x,
              "--y": station.y,
            } as React.CSSProperties}
          >
            ⚡
          </div>
        ))}

        {state.robots.map((robot) => (
          <button
            className={[
              "robot",
              robot.state === "failed" ? "failed" : "",
              (robot.state === "moving_to_charger" ||
                (robot.moves_to_charger !== null &&
                  robot.battery_level <= robot.moves_to_charger + 2))
                ? "critical-battery"
                : "",
              selectedRobot === robot.id ? "selected" : "",
            ].join(" ")}
            key={robot.id}
            onClick={() => onSelectRobot(robot.id)}
            style={{
              "--x": robot.position.x,
              "--y": robot.position.y,
            } as React.CSSProperties}
            title={`${robot.id}: ${robot.state}`}
          >
            <span className="robot-top" />
            <span className="robot-id">{robot.id.replace("R-", "")}</span>
          </button>
        ))}
      </div>}

      <div className="map-legend">
        <span><i className="legend-dot robot-dot" /> Robot</span>
        <span><i className="legend-dot pickup-dot" /> Pickup</span>
        <span><i className="legend-dot dropoff-dot" /> Drop-off</span>
        <span><i className="legend-dot charger-dot" /> Charger</span>
        <span><i className="legend-line" /> Selected route</span>
      </div>
    </section>
  );
}
