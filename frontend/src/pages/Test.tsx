import React, { Suspense, useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { Stars } from "@react-three/drei";
import type { Paper } from "../types";
import { samplePapers } from "../data/sampleData";
import {Bloom, EffectComposer} from "@react-three/postprocessing";
import * as THREE from "three";
import { PointerLockControls } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";



type PaperPointProps = { paper: Paper; selected?: boolean };

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
        <group
            position={[paper.x, paper.y, paper.z]}
            onPointerOver={() => setHovered(true)}
            onPointerOut={() => setHovered(false)}
        >
            {/* Quả cầu chính */}
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
                        transparent={true}
                        opacity={0.3}
                        side={THREE.BackSide}
                    />
                </mesh>
            )}
        </group>
    );
};

const MainScene: React.FC<{ isActive: boolean }> = ({ isActive }) => {
    const { camera } = useThree();
    const [keys, setKeys] = useState<{ [key: string]: boolean }>({});

    // lắng nghe phím bấm
    useEffect(() => {
        const downHandler = (e: KeyboardEvent) => setKeys((k) => ({ ...k, [e.key.toLowerCase()]: true }));
        const upHandler = (e: KeyboardEvent) => setKeys((k) => ({ ...k, [e.key.toLowerCase()]: false }));

        window.addEventListener("keydown", downHandler);
        window.addEventListener("keyup", upHandler);

        return () => {
            window.removeEventListener("keydown", downHandler);
            window.removeEventListener("keyup", upHandler);
        };
    }, []);

    // mỗi frame cập nhật vị trí camera
    useFrame(() => {
        const speed = 0.1; // tốc độ di chuyển
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
            direction.cross(camera.up); // sang trái
            camera.position.addScaledVector(direction, -speed);
        }
        if (keys["d"]) {
            camera.getWorldDirection(direction);
            direction.cross(camera.up); // sang phải
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

            <Suspense fallback={null}>
                {samplePapers.map((paper) => (
                    <PaperPoint key={paper.id} paper={paper} />
                ))}
            </Suspense>

            {isActive && <PointerLockControls />}
        </>
    );
};

const PaperScatter3D: React.FC = () => {
  const [isActive, setIsActive] = useState(false);

  // Khi click vào màn hình -> kích hoạt chế độ điều khiển
    const handleClick = () => {
        setIsActive(true);
        const canvas = document.querySelector("canvas");
        canvas?.requestPointerLock();
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

        <div
            style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                color: "white",
                fontSize: "24px",
                fontWeight: "bold",
                pointerEvents: "none", // không chặn click
                userSelect: "none",    // không cho bôi chọn
            }}
        >
            +
        </div>

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
