import { OrbitControls } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group, MeshStandardMaterial } from "three";

import type { FleetState, Robot } from "../types";

type Props = {
  state: FleetState;
  selectedRobot: string | null;
  onSelectRobot: (id: string) => void;
};

function RobotMesh({
  robot,
  selected,
  width,
  height,
  onSelect,
}: {
  robot: Robot;
  selected: boolean;
  width: number;
  height: number;
  onSelect: () => void;
}) {
  const group = useRef<Group>(null);
  const warningMaterial = useRef<MeshStandardMaterial>(null);
  const targetX = robot.position.x - width / 2 + 0.5;
  const targetZ = robot.position.y - height / 2 + 0.5;
  const initialPosition = useRef<[number, number, number]>([
    targetX,
    0.32,
    targetZ,
  ]);

  useFrame((frame, delta) => {
    if (!group.current) return;
    const interpolation = 1 - Math.exp(-delta * 7);
    group.current.position.x +=
      (targetX - group.current.position.x) * interpolation;
    group.current.position.z +=
      (targetZ - group.current.position.z) * interpolation;
    if (warningMaterial.current) {
      const pulse = (Math.sin(frame.clock.elapsedTime * 5) + 1) / 2;
      warningMaterial.current.opacity = 0.25 + pulse * 0.5;
      warningMaterial.current.emissiveIntensity = 1.2 + pulse * 3;
    }
  });

  const criticalBattery =
    robot.state === "moving_to_charger" ||
    (robot.moves_to_charger !== null &&
      robot.battery_level <= robot.moves_to_charger + 2);
  const color =
    robot.state === "failed"
      ? "#b8524b"
      : selected
        ? "#d2b46f"
        : "#9aa29d";
  const statusColor =
    robot.state === "failed" || criticalBattery ? "#ef6a61" : "#a9d19f";
  const chassisColor = "#59605c";
  const trimColor = "#d2d6d1";
  const bumperColor = "#aeb5b0";
  const wheelPositions = [
    [-0.38, -0.08, -0.23],
    [0.38, -0.08, -0.23],
    [-0.38, -0.08, 0.23],
    [0.38, -0.08, 0.23],
  ] as const;

  return (
    <group
      ref={group}
      position={initialPosition.current}
      onClick={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      <mesh position={[0, -0.02, 0]}>
        <boxGeometry args={[0.7, 0.2, 0.76]} />
        <meshStandardMaterial color={chassisColor} roughness={0.78} />
      </mesh>

      {wheelPositions.map(([x, y, z]) => (
        <mesh key={`${x}:${z}`} position={[x, y, z]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.14, 0.14, 0.12, 16]} />
          <meshStandardMaterial color="#252927" roughness={0.92} />
        </mesh>
      ))}

      <mesh position={[0, 0.15, 0.03]}>
        <boxGeometry args={[0.56, 0.3, 0.54]} />
        <meshStandardMaterial color={color} roughness={0.62} />
      </mesh>

      {criticalBattery && (
        <mesh position={[0, 0.15, 0.03]}>
          <boxGeometry args={[0.59, 0.33, 0.57]} />
          <meshStandardMaterial
            ref={warningMaterial}
            color="#8f2925"
            emissive="#6f1512"
            transparent
            opacity={0.4}
            depthWrite={false}
          />
        </mesh>
      )}

      <mesh position={[0, 0.36, 0.04]}>
        <boxGeometry args={[0.27, 0.045, 0.22]} />
        <meshStandardMaterial color={trimColor} roughness={0.46} />
      </mesh>

      <mesh position={[0, 0.17, -0.255]}>
        <boxGeometry args={[0.36, 0.08, 0.035]} />
        <meshStandardMaterial color="#3e4541" roughness={0.54} />
      </mesh>

      <mesh position={[0.18, 0.32, 0.08]}>
        <boxGeometry args={[0.055, 0.055, 0.055]} />
        <meshBasicMaterial color={statusColor} />
      </mesh>

      <mesh position={[0, 0.41, 0.1]}>
        <boxGeometry args={[0.16, 0.06, 0.12]} />
        <meshStandardMaterial color="#7f8782" roughness={0.58} />
      </mesh>

      <mesh position={[0, 0.03, 0.41]}>
        <boxGeometry args={[0.46, 0.08, 0.04]} />
        <meshStandardMaterial
          color={robot.state === "failed" ? "#b8524b" : bumperColor}
        />
      </mesh>
      {selected && (
        <mesh position={[0, -0.29, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.46, 0.52, 32]} />
          <meshBasicMaterial color="#c7a35a" />
        </mesh>
      )}
    </group>
  );
}

export function Warehouse3D({ state, selectedRobot, onSelectRobot }: Props) {
  const { width, height, obstacles } = state.warehouse;
  const selected = state.robots.find((robot) => robot.id === selectedRobot);

  const worldPosition = (x: number, y: number, elevation = 0) =>
    [x - width / 2 + 0.5, elevation, y - height / 2 + 0.5] as const;

  return (
    <div className="warehouse-3d" aria-label="Interactive 3D warehouse view">
      <Canvas camera={{ position: [12, 14, 16], fov: 36 }}>
        <color attach="background" args={["#0c0e0d"]} />
        <ambientLight intensity={1.1} />
        <directionalLight
          intensity={2.2}
          position={[8, 14, 7]}
        />

        <mesh position={[0, -0.08, 0]}>
          <boxGeometry args={[width, 0.14, height]} />
          <meshStandardMaterial color="#151817" roughness={0.9} />
        </mesh>

        <gridHelper
          args={[Math.max(width, height), Math.max(width, height), "#333734", "#252825"]}
          position={[0, 0.005, 0]}
        />

        {obstacles.map((position) => (
          <mesh
            key={`${position.x}:${position.y}`}
            position={worldPosition(position.x, position.y, 0.42)}
          >
            <boxGeometry args={[0.82, 0.84, 0.82]} />
            <meshStandardMaterial color="#303431" roughness={0.78} />
          </mesh>
        ))}

        {state.jobs
          .filter((job) => !["completed", "cancelled"].includes(job.state))
          .flatMap((job) => [
            <mesh
              key={`${job.id}-pickup`}
              position={worldPosition(job.pickup.x, job.pickup.y, 0.05)}
              rotation={[-Math.PI / 2, 0, 0]}
            >
              <ringGeometry args={[0.24, 0.32, 28]} />
              <meshBasicMaterial color="#c7a35a" />
            </mesh>,
            <mesh
              key={`${job.id}-dropoff`}
              position={worldPosition(job.dropoff.x, job.dropoff.y, 0.08)}
            >
              <cylinderGeometry args={[0.2, 0.2, 0.12, 4]} />
              <meshStandardMaterial color="#c7a35a" />
            </mesh>,
          ])}

        {state.warehouse.charging_stations.map((station) => (
          <group
            key={`charger-${station.x}:${station.y}`}
            position={worldPosition(station.x, station.y, 0.035)}
          >
            <mesh>
              <cylinderGeometry args={[0.38, 0.38, 0.07, 20]} />
              <meshStandardMaterial color="#8a7443" emissive="#59491f" />
            </mesh>
            <mesh position={[0, 0.07, 0]}>
              <boxGeometry args={[0.16, 0.04, 0.28]} />
              <meshBasicMaterial color="#f0cc72" />
            </mesh>
          </group>
        ))}

        {selected?.path.map((position, index) => (
          <mesh
            key={`${position.x}:${position.y}:${index}`}
            position={worldPosition(position.x, position.y, 0.06)}
          >
            <sphereGeometry args={[0.07, 10, 10]} />
            <meshBasicMaterial color="#c7a35a" />
          </mesh>
        ))}

        {state.robots.map((robot) => (
          <RobotMesh
            key={robot.id}
            robot={robot}
            selected={robot.id === selectedRobot}
            width={width}
            height={height}
            onSelect={() => onSelectRobot(robot.id)}
          />
        ))}

        <OrbitControls
          makeDefault
          enableDamping
          minDistance={9}
          maxDistance={34}
          maxPolarAngle={Math.PI / 2.08}
          target={[0, 0, 0]}
        />
      </Canvas>
    </div>
  );
}
