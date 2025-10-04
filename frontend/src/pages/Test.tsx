import React, { Suspense, useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { FirstPersonControls, Stars } from "@react-three/drei";
import type { Paper } from "../types";
import { samplePapers } from "../data/sampleData";

type PaperPointProps = { paper: Paper };

const PaperPoint: React.FC<PaperPointProps> = ({ paper }) => {
  const [hovered, setHovered] = React.useState(false);

  const colorMap: Record<string, string> = {
    AI: "#ff9f1c",
    Physics: "#d65db1",
    Biology: "#39ff14",
    Energy: "#08f7fe",
    CS: "#ff073a",
    Environment: "#00ffbf",
  };

  const color = colorMap[paper.cluster] || "gray";

  return (
    <mesh
      position={[paper.x, paper.y, paper.z]}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <sphereGeometry args={[0.08, 16, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={hovered ? 2.5 : 1.2}
      />
    </mesh>
  );
};

const MainScene: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <>
    <ambientLight intensity={0.6} />
    <pointLight position={[10, 10, 10]} />
    <Stars radius={100} depth={50} count={3000} fade />

    <Suspense fallback={null}>
      {samplePapers.map((paper) => (
        <PaperPoint key={paper.id} paper={paper} />
      ))}
    </Suspense>

    {isActive && (
      <FirstPersonControls
        lookSpeed={0.1}
        movementSpeed={3}
        activeLook={true}
        lookVertical={true}
      />
    )}
  </>
);

const PaperScatter3D: React.FC = () => {
  const [isActive, setIsActive] = useState(false);

  // Khi click vào màn hình -> kích hoạt chế độ điều khiển
  const handleClick = () => {
    setIsActive(true);
  };

  // Khi nhấn ESC -> thoát chế độ điều khiển
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsActive(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
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
      <Canvas
        style={{ background: "black" }}
        camera={{ position: [0, 1.6, 5], fov: 75 }}
      >
        <MainScene isActive={isActive} />
      </Canvas>

      {!isActive && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            color: "white",
            fontSize: "18px",
            background: "rgba(0,0,0,0.5)",
            padding: "12px 24px",
            borderRadius: "12px",
          }}
        >
          Click the screen to start playing!
        </div>
      )}
    </div>
  );
};

export default PaperScatter3D;
