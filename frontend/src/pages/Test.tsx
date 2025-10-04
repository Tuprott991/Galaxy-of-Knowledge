import React, { Suspense, useState, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Stars, PointerLockControls } from "@react-three/drei";
import type { Paper } from "../types";
import { samplePapers } from "../data/sample-data";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import * as THREE from "three";
import { ShortDetail } from "@/components/mainpage/short-detail";
import { colorPalette } from "@/data/color-palette";
import { cluster } from "@/data/cluster";
import { randomClusterColor } from "@/utils/helper";

type PaperPointProps = {
  paper: Paper;
  selected?: boolean;
  onHover: (paper: Paper | null) => void;
  colorMap?: Record<string, string>;
};

const PaperPoint: React.FC<PaperPointProps> = ({ paper, onHover, colorMap }) => {
  const [hovered, setHovered] = useState(false);
  const color = colorMap?.[paper.cluster] || "gray";

  return (
    <group
      position={[paper.x, paper.y, paper.z]}
      onPointerOver={() => {
        setHovered(true);
        onHover(paper);
      }}
      onPointerOut={() => {
        setHovered(false);
        onHover(null);
      }}
    >
      <mesh>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 2.5 : 1.2}
        />
      </mesh>

      {hovered && (
        <mesh>
          <sphereGeometry args={[0.12, 32, 32]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.3}
            side={THREE.BackSide}
          />
        </mesh>
      )}
    </group>
  );
};

const MainScene: React.FC<{ isActive: boolean; onHover: (paper: Paper | null) => void }> = ({
  isActive,
  onHover,
}) => {
  const { camera } = useThree();
  const [keys, setKeys] = useState<{ [key: string]: boolean }>({});
  const colorMap = React.useMemo(() => randomClusterColor(cluster, colorPalette), []);

  useEffect(() => {
    const downHandler = (e: KeyboardEvent) =>
      setKeys((k) => ({ ...k, [e.key.toLowerCase()]: true }));
    const upHandler = (e: KeyboardEvent) =>
      setKeys((k) => ({ ...k, [e.key.toLowerCase()]: false }));

    window.addEventListener("keydown", downHandler);
    window.addEventListener("keyup", upHandler);

    return () => {
      window.removeEventListener("keydown", downHandler);
      window.removeEventListener("keyup", upHandler);
    };
  }, []);

  // Di chuyển camera
  useFrame(() => {
    if (!isActive) return;

    const speed = 0.1;
    const direction = new THREE.Vector3();

    if (keys["w"]) {
      camera.getWorldDirection(direction);
      camera.position.addScaledVector(direction, speed);
    }
    if (keys["s"]) {
      camera.getWorldDirection(direction);
      camera.position.addScaledVector(direction, -speed);
    }
    if (keys["a"]) {
      camera.getWorldDirection(direction);
      direction.cross(camera.up);
      camera.position.addScaledVector(direction, -speed);
    }
    if (keys["d"]) {
      camera.getWorldDirection(direction);
      direction.cross(camera.up);
      camera.position.addScaledVector(direction, speed);
    }
  });

  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} />

      <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade />

      <EffectComposer>
        <Bloom intensity={1} luminanceThreshold={0} luminanceSmoothing={0.9} />
      </EffectComposer>

      <Suspense fallback={<></>}>
        {samplePapers.map((paper) => (
          <PaperPoint
            key={paper.id}
            paper={paper}
            onHover={onHover}
            colorMap={colorMap}
          />
        ))}
      </Suspense>

      {isActive && <PointerLockControls />}
    </>
  );
};

const PaperScatter3D: React.FC = () => {
  const [isActive, setIsActive] = useState(false);
  const [hoveredPaper, setHoveredPaper] = useState<Paper | null>(null);

  const handleClick = () => {
    setIsActive(true);
    const canvas = document.querySelector("canvas");
    canvas?.requestPointerLock();
  };

  useEffect(() => {
    const handlePointerLockChange = () => {
      if (!document.pointerLockElement) {
        setIsActive(false);
      }
    };
    document.addEventListener("pointerlockchange", handlePointerLockChange);
    return () => {
      document.removeEventListener("pointerlockchange", handlePointerLockChange);
    };
  }, []);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        cursor: isActive ? "none" : "pointer",
      }}
      onClick={handleClick}
    >
      <Canvas style={{ background: "black" }} camera={{ position: [0, 1.6, 5], fov: 75 }}>
        <MainScene isActive={isActive} onHover={setHoveredPaper} />
      </Canvas>

      {!isActive ? (
        <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white text-[18px] bg-black/50 px-6 py-3 rounded-lg">
          Click the screen to start playing!
        </div>
      ) : (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white text-2xl font-bold pointer-events-none select-none">
          +
        </div>
      )}

      {hoveredPaper && <ShortDetail paper={hoveredPaper} />}
    </div>
  );
};

export default PaperScatter3D;
