import type { FleetState } from "../types";

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
          <span className="eyebrow">LIVE SPATIAL MODEL</span>
          <h2>Fulfillment floor</h2>
        </div>
        <span className="coordinates">ZONE 04 / {state.tick.toString().padStart(5, "0")}</span>
      </div>

      <div
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

        {state.robots.map((robot) => (
          <button
            className={[
              "robot",
              robot.state === "failed" ? "failed" : "",
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
      </div>

      <div className="map-legend">
        <span><i className="legend-dot robot-dot" /> autonomous unit</span>
        <span><i className="legend-dot pickup-dot" /> pickup</span>
        <span><i className="legend-dot dropoff-dot" /> dropoff</span>
        <span><i className="legend-line" /> selected route</span>
      </div>
    </section>
  );
}
