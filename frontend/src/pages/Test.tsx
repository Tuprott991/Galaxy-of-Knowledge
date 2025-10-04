import React, { Suspense, useState, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Stars, PointerLockControls } from "@react-three/drei";
import type { Paper } from "../types";
import { ShortDetail } from "@/components/mainpage/short-detail";
import { colorPalette } from "@/data/color-palette";
import { randomClusterColor } from "@/utils/helper";
import { axiosClient } from "@/api/axiosClient";
import * as THREE from "three";
import {Bloom, EffectComposer} from "@react-three/postprocessing";
import { useRef } from "react";


type PaperPointProps = {
  paper: Paper;
  onHover: (paper: Paper | null) => void;
  colorMap?: Record<string, string>;
  selected?: boolean;
};

const PaperPoint: React.FC<PaperPointProps> = ({ paper, onHover, colorMap, selected }) => {
  const [hovered, setHovered] = useState(false);
  const [progress, setProgress] = useState(0); // 0 → 1 bung ra
  const orbitRef = useRef<THREE.Group>(null);

  const color = colorMap?.[paper.cluster] || "gray";

  // Animation bung ra + quay quanh
  useFrame((_, delta) => {
    if (selected) {
      setProgress((p) => Math.min(1, p + delta)); // bung dần ra
      if (orbitRef.current) {
        orbitRef.current.rotation.y += delta * 0.8;
        orbitRef.current.rotation.x += delta * 0.3;
      }
    } else {
      setProgress((p) => Math.max(0, p - delta)); // thu lại
    }
  });

  // Vị trí của hành tinh
  const planetPositions = [
    [0.8, 0, 0],
    [-0.8, 0, 0],
    [0, 0.8, 0],
    [0, -0.8, 0],
    [0, 0, 0.8],
    [0, 0, -0.8],
    [0.8, 0.8, 0.8],
  ];

  return (
      <group
          position={[paper.x, paper.y, paper.z]}
          onPointerOver={(e) => {
            e.stopPropagation();
            setHovered(true);
            onHover(paper);
          }}
          onPointerOut={(e) => {
            e.stopPropagation();
            setHovered(false);
            onHover(null);
          }}
      >
        {/* 🌟 Ngôi sao chính */}
        <mesh>
          <sphereGeometry args={[0.08, 16, 16]} />
          <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={hovered || selected ? 3 : 1.2} // phát sáng mạnh khi chọn
          />
        </mesh>

        {/* Vòng sáng khi hover */}
        {(hovered || selected) && (
            <mesh>
              <sphereGeometry args={[0.15 + progress * 0.1, 32, 32]} />
              <meshBasicMaterial
                  color={color}
                  transparent
                  opacity={0.3 + 0.2 * progress}
                  side={THREE.BackSide}
              />
            </mesh>
        )}

        {/* 🪐 Hành tinh bay quanh */}
        {progress > 0 && (
            <group ref={orbitRef}>
              {planetPositions.map((pos, i) => {
                const [tx, ty, tz] = pos;
                return (
                    <mesh
                        key={i}
                        position={[tx * progress, ty * progress, tz * progress]} // bung ra dần
                        scale={[progress, progress, progress]} // scale từ 0 -> 1
                    >
                      <sphereGeometry args={[0.05, 16, 16]} /> {/* hành tinh tròn */}
                      <meshStandardMaterial
                          color="white"
                          emissive="cyan"
                          emissiveIntensity={2}
                          metalness={0.5}
                          roughness={0.3}
                      />
                      {/* Thêm ánh sáng cho từng hành tinh */}
                      <pointLight intensity={0.6} distance={2} color="cyan" />
                    </mesh>
                );
              })}
            </group>
        )}
      </group>
  );
};


const MainScene: React.FC<{ isActive: boolean; onHover: (paper: Paper | null) => void }> = ({
                                                                                              isActive,
                                                                                              onHover,
                                                                                            }) => {
  const { camera, scene } = useThree();
  const [keys, setKeys] = useState<{ [key: string]: boolean }>({});
  const [mouseButtons, setMouseButtons] = useState<{ left: boolean; right: boolean }>({
    left: false,
    right: false,
  });
  const [papers, setPapers] = useState<Paper[]>([]);
  const [colorMap, setColorMap] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const direction = new THREE.Vector3();

  // fetch dữ liệu paper
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axiosClient.get("/v1/papers/visualization");
        if (!res.data || res.data.length === 0) return;

        const scaled = res.data.map((p: Paper) => ({
          ...p,
          x: p.x * 10,
          y: p.y * 10,
          z: p.z * 10,
        }));

        setPapers(scaled);

        const clusters: string[] = Array.from(new Set(scaled.map((p: Paper) => p.cluster)));
        const map: Record<string, string> = randomClusterColor(clusters, colorPalette);
        setColorMap(map);
      } catch (error) {
        console.error("Failed to fetch papers/colors:", error);
      }
    };
    fetchData();
  }, []);

  // bắt phím WASD + Shift
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

  // bắt chuột trái/phải
  useEffect(() => {
    const downHandler = (e: MouseEvent) => {
      if (e.button === 0) setMouseButtons((m) => ({ ...m, left: true }));
      if (e.button === 2) setMouseButtons((m) => ({ ...m, right: true }));
    };
    const upHandler = (e: MouseEvent) => {
      if (e.button === 0) setMouseButtons((m) => ({ ...m, left: false }));
      if (e.button === 2) setMouseButtons((m) => ({ ...m, right: false }));
    };

    window.addEventListener("mousedown", downHandler);
    window.addEventListener("mouseup", upHandler);
    window.addEventListener("contextmenu", (e) => e.preventDefault());

    return () => {
      window.removeEventListener("mousedown", downHandler);
      window.removeEventListener("mouseup", upHandler);
    };
  }, []);

  function findPaperId(obj: THREE.Object3D): number | null {
    let current: THREE.Object3D | null = obj;
    while (current) {
      if (current.userData.paperId) return current.userData.paperId as number;
      current = current.parent;
    }
    return null;
  }

  // di chuyển + raycaster chọn object
  useFrame(() => {
    if (!isActive) return;

    // Raycaster từ crosshair
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
    const intersects = raycaster.intersectObjects(scene.children, true);

    const hit = intersects.find(
        (i) => i.object instanceof THREE.Mesh && i.object.geometry.type === "SphereGeometry"
    );

    if (hit) {
      const id = findPaperId(hit.object);
      setSelectedId(id);
    } else {
      setSelectedId(null);
    }

    // Movement
    let speed = keys["shift"] ? 0.3 : 0.1;

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

    if (mouseButtons.left) {
      camera.getWorldDirection(direction);
      camera.position.addScaledVector(direction, speed);
    }
    if (mouseButtons.right) {
      camera.getWorldDirection(direction);
      camera.position.addScaledVector(direction, -speed);
    }
  });

  // ✅ chỉ return 1 lần
  return (
      <>
        <ambientLight intensity={0.6} />
        <pointLight position={[10, 10, 10]} />
        <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade />

        <Suspense fallback={null}>
          {papers.map((paper) => (
              <group key={paper.id} userData={{ paperId: paper.id }}>
                <PaperPoint
                    paper={paper}
                    onHover={onHover}
                    colorMap={colorMap}
                    selected={selectedId === paper.id}
                />
              </group>
          ))}
        </Suspense>

        {isActive && <PointerLockControls />}
        <EffectComposer>
          <Bloom intensity={1.5} luminanceThreshold={0} luminanceSmoothing={0.9} />
        </EffectComposer>
      </>
  );
};




const PaperScatter3D: React.FC = () => {
  const [isActive, setIsActive] = useState(false);
  const [hoveredPaper, setHoveredPaper] = useState<Paper | null>(null);

  const handleClick = () => {
    if (!isActive) {
      setIsActive(true);
      document.querySelector("canvas")?.requestPointerLock();
    }
  };

  useEffect(() => {
    const handlePointerLockChange = () => setIsActive(!!document.pointerLockElement);
    document.addEventListener("pointerlockchange", handlePointerLockChange);
    return () => document.removeEventListener("pointerlockchange", handlePointerLockChange);
  }, []);

  return (
    <div
      style={{ width: "100vw", height: "100vh", cursor: isActive ? "none" : "pointer" }}
      onClick={handleClick}
    >
      <Canvas style={{ background: "black" }} camera={{ position: [0, 1.6, 5], fov: 75 }}>
        <MainScene isActive={isActive} onHover={setHoveredPaper} />
      </Canvas>

      {!isActive ? (
        <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white text-[18px] bg-black/50 px-6 py-3 rounded-lg">
          Click the screen to start!
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
