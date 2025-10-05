import React, { Suspense, useState, useEffect, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Stars, PointerLockControls } from "@react-three/drei";
import type { Paper } from "../types";
import { ShortDetail } from "@/components/mainpage/short-detail";
import { colorPalette } from "@/data/color-palette";
import { randomClusterColor } from "@/utils/helper";
import { axiosClient } from "@/api/axiosClient";
import * as THREE from "three";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { useGlobal } from "@/context/GlobalContext";

type PaperPointProps = {
  paper: Paper;
  onHover: (paper: Paper | null) => void;
  colorMap?: Record<string, string>;
  selected?: boolean;
};

const PaperPoint: React.FC<PaperPointProps> = ({ paper, onHover, colorMap, selected }) => {
  const [hovered, setHovered] = useState(false);
  const [progress, setProgress] = useState(0);
  const [paused, setPaused] = useState(false);
  const [networkPositions, setNetworkPositions] = useState<THREE.Vector3[]>([]);
  const orbitRef = useRef<THREE.Group>(null);
  const linesRef = useRef<(THREE.Line | null)[]>([]);
  const color = colorMap?.[paper.cluster] || "gray";

  const solarSystemPlanets = [
    { name: "Mercury", color: "#8C7853", size: 0.015, distance: 0.25, emissive: "#8C7853", emissiveIntensity: 0.3 },
    { name: "Venus", color: "#FFC649", size: 0.02, distance: 0.35, emissive: "#FFC649", emissiveIntensity: 0.5 },
    { name: "Mars", color: "#CD5C5C", size: 0.018, distance: 0.45, emissive: "#CD5C5C", emissiveIntensity: 0.4 },
    { name: "Jupiter", color: "#D8CA9D", size: 0.04, distance: 0.55, emissive: "#D8CA9D", emissiveIntensity: 0.3 },
    { name: "Saturn", color: "#FAD5A5", size: 0.035, distance: 0.65, emissive: "#FAD5A5", emissiveIntensity: 0.3 },
    { name: "Uranus", color: "#4FD0E7", size: 0.025, distance: 0.75, emissive: "#4FD0E7", emissiveIntensity: 0.4 },
    { name: "Neptune", color: "#4B70DD", size: 0.025, distance: 0.85, emissive: "#4B70DD", emissiveIntensity: 0.4 }
  ];

  useEffect(() => {
    const handleSpace = (e: KeyboardEvent) => {
      if (e.key === "q" || e.key === "Q") {
        e.preventDefault();
        e.stopPropagation();
        setPaused((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleSpace);
    return () => window.removeEventListener("keydown", handleSpace);
  }, []);

  // 🔹 Khi pause, sắp xếp lại vị trí hành tinh thành network
  useEffect(() => {
    if (paused) {
      const positions: THREE.Vector3[] = [];
      const radius = 0.8; // bán kính network
      solarSystemPlanets.forEach((_, i) => {
        const theta = (i / solarSystemPlanets.length) * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const x = radius * Math.sin(phi) * Math.cos(theta);
        const y = radius * Math.sin(phi) * Math.sin(theta);
        const z = radius * Math.cos(phi);
        positions.push(new THREE.Vector3(x, y, z));
      });
      setNetworkPositions(positions);
    } else {
      setNetworkPositions([]);
    }
  }, [paused]);

  // 🔹 Animation + quay hoặc sắp xếp network
  useFrame((_, delta) => {
    if (selected || hovered) {
      setProgress((p) => Math.min(1, p + delta * 2));

      if (orbitRef.current) {
        if (!paused) {
          orbitRef.current.rotation.y += delta * 0.2;
          orbitRef.current.rotation.x += delta * 0.05;
        } else {
          orbitRef.current.children.forEach((child, i) => {
            const target = networkPositions[i];
            if (!target) return;
            child.position.lerp(target, delta * 1.5);
          });
        }
      }

      // Cập nhật vị trí đường nối
      if (paused && orbitRef.current) {
        linesRef.current.forEach((line, i) => {
          if (orbitRef.current?.children[i]) {
            const planetPos = orbitRef.current.children[i].position.clone();
            const points = [new THREE.Vector3(0, 0, 0), planetPos];
            if (line) {
              (line.geometry as THREE.BufferGeometry).setFromPoints(points);
            }
          }
        });
      }
    } else {
      setProgress((p) => Math.max(0, p - delta * 2));
    }
  });

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
          emissiveIntensity={hovered || selected ? 3 : 1.2}
        />
      </mesh>

      {/* Hiệu ứng vòng sáng */}
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

      {/* 🪐 Solar System Planets */}
      {progress > 0 && (
        <group ref={orbitRef}>
          {solarSystemPlanets.map((planet, i) => {
            const angle = (i / solarSystemPlanets.length) * Math.PI * 2;
            const baseX = Math.cos(angle) * planet.distance * progress;
            const baseY = Math.sin(angle) * planet.distance * progress * 0.3;
            const baseZ = Math.sin(angle) * planet.distance * progress;

            return (
              <mesh
                key={planet.name}
                position={[baseX, baseY, baseZ]}
                scale={[progress, progress, progress]}
              >
                <sphereGeometry args={[planet.size, 16, 16]} />
                <meshStandardMaterial
                  color={planet.color}
                  emissive={planet.emissive}
                  emissiveIntensity={planet.emissiveIntensity * progress}
                  metalness={planet.name === "Saturn" || planet.name === "Jupiter" ? 0.3 : 0.1}
                  roughness={planet.name === "Venus" ? 0.1 : 0.4}
                />

                {/* Saturn Rings */}
                {planet.name === "Saturn" && (
                  <mesh rotation={[Math.PI / 2, 0, 0]}>
                    <ringGeometry args={[planet.size * 1.5, planet.size * 2.2, 32]} />
                    <meshBasicMaterial
                      color="#C4A484"
                      transparent
                      opacity={0.6 * progress}
                      side={THREE.DoubleSide}
                    />
                  </mesh>
                )}

                <pointLight intensity={0.2 * progress} distance={1} color={planet.color} />
              </mesh>
            );
          })}
          {/* 🔹 Các đường nối network */}
          {paused &&
            solarSystemPlanets.map((_, i) => (
              <line
                key={`line-${i}`}
                ref={(ref) => {
                  linesRef.current[i] = ref as unknown as THREE.Line | null;
                }}
              >
                <bufferGeometry />
                <lineBasicMaterial color={color} transparent opacity={0.5} />
              </line>
            ))}
        </group>
      )}
    </group>
  );
};

// ========================== //
//         MainScene          //
// ========================== //

const MainScene: React.FC<{ isActive: boolean; onHover: (paper: Paper | null) => void }> = ({
  isActive,
  onHover,
}) => {
  const { camera, scene } = useThree();

  useEffect(() => {
    camera.position.set(75.366, 16.746, -33.750);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  const [keys, setKeys] = useState<{ [key: string]: boolean }>({});
  const [mouseButtons, setMouseButtons] = useState<{ left: boolean; right: boolean }>({
    left: false,
    right: false,
  });
  const [papers, setPapers] = useState<Paper[]>([]);
  const [colorMap, setColorMap] = useState<Record<string, string>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const direction = new THREE.Vector3();

  const { query } = useGlobal();

  useEffect(() => {
    const fetchData = async () => {
      try {
        let res = null;
        if (query) {
          res = await axiosClient.get("/v1/papers/search", {
            params: { query, search_type: 'semantic', limit: 100 },
          });
        } else {
          res = await axiosClient.get("/v1/papers/visualization");
        }
        console.log(res.data)
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
        console.error("Failed to fetch papers:", error);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (!query) return;

    // Tọa độ gốc của ngôi sao
    const target = new THREE.Vector3(64.70495128631592, 8.552704453468323, -32.50426769256592);

    // Khoảng cách camera lùi ra
    const distance = 3.5;

    // Hướng nhìn từ ngôi sao về phía camera hiện tại
    const direction = new THREE.Vector3().subVectors(camera.position, target).normalize();

    // Nếu camera đang ở quá xa hoặc bị lệch hướng, chuẩn hóa hướng
    if (direction.length() === 0) direction.set(0, 0, 1); // tránh NaN nếu camera == target

    // Vị trí đích cách ngôi sao một đoạn về phía sau
    const finalPos = target.clone().addScaledVector(direction, distance);

    const duration = 0.5; // giây - FASTER: reduced from 1.2 to 0.5
    const start = camera.position.clone();
    const startTime = performance.now();

    const animate = (time: number) => {
      const elapsed = (time - startTime) / (duration * 1000);
      // Use easeInOutQuad for smoother, faster animation
      const t = Math.min(elapsed < 0.5 ? 2 * elapsed * elapsed : 1 - Math.pow(-2 * elapsed + 2, 2) / 2, 1);
      camera.position.lerpVectors(start, finalPos, t);
      camera.lookAt(target);
      if (elapsed < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [query, camera]);

  const { setHtmlContent, setSelectedPaperId, setChatView, setTopic } = useGlobal();

  useEffect(() => {
    const handleSpace = async (e: KeyboardEvent) => {
      if ((e.key === "q" || e.key === "Q") && selectedId !== null) {
        e.preventDefault();
        e.stopPropagation();
        const paper = papers.find((p) => p.paper_id === selectedId);
        if (!paper) return;

        // Open chatView immediately for faster response
        setChatView?.(true);
        setSelectedPaperId?.(selectedId);

        try {
          const res = await axiosClient.get(`/v1/papers/${selectedId}/html-context`);
          console.log("Fetched HTML content:", res.data);
          setHtmlContent?.(res.data.html_context);
          setTopic?.(res.data.title);
        } catch (err) {
          console.error("Failed to fetch paper info:", err);
          // Optionally close chatView if there's an error
          setChatView?.(false);
        }
      }
    };
    window.addEventListener("keydown", handleSpace);
    return () => window.removeEventListener("keydown", handleSpace);
  }, [selectedId, papers, setHtmlContent, setSelectedPaperId, setTopic, setChatView]);

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

  function findPaperId(obj: THREE.Object3D): string | null {
    let current: THREE.Object3D | null = obj;
    while (current) {
      if (current.userData.paper_id) return current.userData.paper_id as string;
      current = current.parent;
    }
    return null;
  }

  useFrame(() => {
    if (!isActive) return;

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

    const speed = keys["shift"] ? 0.3 : 0.1;
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

  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} />
      <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade />

      <Suspense fallback={null}>
        {papers.map((paper) => (
          <group key={paper.paper_id} userData={{ paper_id: paper.paper_id }}>
            <PaperPoint
              paper={paper}
              onHover={onHover}
              colorMap={colorMap}
              selected={selectedId === paper.paper_id}
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

// ========================== //
//       PaperScatter3D       //
// ========================== //

const PaperScatter3D: React.FC = () => {
  const [isActive, setIsActive] = useState(false);
  const [hoveredPaper, setHoveredPaper] = useState<Paper | null>(null);
  const { chatView } = useGlobal();

  const enablePointerLock = () => {
    const canvas = document.querySelector("canvas");
    canvas?.requestPointerLock();
  };

  const disablePointerLock = () => {
    if (document.pointerLockElement) {
      document.exitPointerLock();
    }
  };

  useEffect(() => {
    if (chatView) {
      disablePointerLock();
      setIsActive(false);
    } else {
      enablePointerLock();
      setIsActive(true);
    }
  }, [chatView]);

  useEffect(() => {
    const handlePointerLockChange = () => {
      setIsActive(!!document.pointerLockElement);
    };
    document.addEventListener("pointerlockchange", handlePointerLockChange);
    return () => document.removeEventListener("pointerlockchange", handlePointerLockChange);
  }, []);

  return (
    <div
      style={{ width: "100vw", height: "100vh", cursor: isActive ? "none" : "pointer" }}
      onClick={() => !chatView && enablePointerLock()}
    >
      <Canvas style={{ background: "black" }} camera={{ position: [0, 1.6, 5], fov: 75 }}>
        <MainScene isActive={isActive} onHover={setHoveredPaper} />
      </Canvas>

      {!chatView && !isActive && (
        <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white text-[18px] bg-black/50 px-6 py-3 rounded-lg">
          Click the screen to start!
        </div>
      )}

      {!chatView && isActive && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white text-2xl font-bold pointer-events-none select-none">
          +
        </div>
      )}

      {hoveredPaper && !chatView && <ShortDetail paper={hoveredPaper} />}
    </div>
  );
};

export default PaperScatter3D;
