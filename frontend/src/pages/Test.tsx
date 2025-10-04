import React, { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import { samplePapers } from "../data/sampleData";
import type { Paper } from "../types";

type PaperPointProps = {
  paper: Paper;
};

const PaperPoint: React.FC<PaperPointProps> = ({ paper }) => {
  const colorMap: Record<string, string> = {
    AI: "orange",
    Physics: "purple",
    Biology: "green",
    Energy: "blue",
    CS: "red",
    Environment: "teal",
  };

  return (
    <mesh position={[paper.x, paper.y, paper.z]}>
      {/* Icosahedron thay cho sphere */}
      <icosahedronGeometry args={[0.08, 0]} />
      <meshStandardMaterial
        color={colorMap[paper.cluster] || "gray"}
        flatShading
      />
      <Html distanceFactor={10}>
        <div
          style={{
            background: "rgba(0,0,0,0.6)",
            color: "white",
            padding: "2px 5px",
            borderRadius: "4px",
            fontSize: "8px",
            whiteSpace: "nowrap",
          }}
        >
          {paper.title}
        </div>
      </Html>
    </mesh>
  );
};

const Paper3DScene: React.FC = () => {
  return (
    <Canvas style={{ width: "100vw", height: "100vh" }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />
      <Suspense fallback={null}>
        {samplePapers.map((paper) => (
          <PaperPoint key={paper.id} paper={paper} />
        ))}
      </Suspense>
      <OrbitControls />
    </Canvas>
  );
};

export default Paper3DScene;
