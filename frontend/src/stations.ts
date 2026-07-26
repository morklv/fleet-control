import type { FleetState, Position } from "./types";

export type MapLocation = { label: string; position: Position };

const namedLocations: MapLocation[] = [
  { label: "Inbound A / 02.01", position: { x: 2, y: 1 } },
  { label: "Inbound B / 15.01", position: { x: 15, y: 1 } },
  { label: "Storage W / 02.06", position: { x: 2, y: 6 } },
  { label: "Storage E / 15.06", position: { x: 15, y: 6 } },
  { label: "Dispatch A / 02.10", position: { x: 2, y: 10 } },
  { label: "Dispatch B / 15.10", position: { x: 15, y: 10 } },
];

const key = ({ x, y }: Position) => `${x},${y}`;

export function mapLocations(warehouse: FleetState["warehouse"]): MapLocation[] {
  const blocked = new Set(warehouse.obstacles.map(key));
  const traversable = (position: Position) =>
    position.x >= 0 &&
    position.x < warehouse.width &&
    position.y >= 0 &&
    position.y < warehouse.height &&
    !blocked.has(key(position));

  const named = namedLocations.filter(({ position }) => traversable(position));
  const namedKeys = new Set(named.map(({ position }) => key(position)));
  const grid: MapLocation[] = [];

  for (let y = 0; y < warehouse.height; y += 1) {
    for (let x = 0; x < warehouse.width; x += 1) {
      const position = { x, y };
      if (traversable(position) && !namedKeys.has(key(position))) {
        grid.push({
          label: `Map cell / ${String(x).padStart(2, "0")}.${String(y).padStart(2, "0")}`,
          position,
        });
      }
    }
  }

  return [...named, ...grid];
}
