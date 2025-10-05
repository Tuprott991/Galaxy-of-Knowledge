import React, { useEffect, useState, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { ForceGraphMethods } from "react-force-graph-2d";

interface NodeType {
    id: string;
    label: string;
    color: string;
    size: number;
}

interface LinkType {
    source: string;
    target: string;
    color: string;
    label: string;
}

const PaperGraph: React.FC = () => {
    const [graphData, setGraphData] = useState<{ nodes: NodeType[]; links: LinkType[] }>({
        nodes: [],
        links: [],
    });
    const fgRef = useRef<ForceGraphMethods<NodeType, LinkType> | undefined>(undefined);
    const [hoverNode, setHoverNode] = useState<NodeType | null>(null);
    const [hoverLink, setHoverLink] = useState<LinkType | null>(null);

    useEffect(() => {
        const fetchGraph = async () => {
            try {
                const res = await fetch(
                    "http://localhost:8000/api/v1/graph/2d?paper_id=PMC2910419&mode=key_knowledge"
                );
                const data = await res.json();

                const nodes: NodeType[] = (data.data.nodes || []).map((n: any) => ({
                    id: n.id || Math.random().toString(),
                    label: n.label || "",
                    color: n.color || "#3498db",
                    size: (n.size || 12) * 0.5,
                }));

                const links: LinkType[] = (data.data.edges || []).map((e: any) => ({
                    source: e.source,
                    target: e.target,
                    color: e.color || "#888",
                    label: e.label || "",
                }));

                setGraphData({ nodes, links });
            } catch (err) {
                console.error("Failed to fetch graph data:", err);
            }
        };

        fetchGraph();
    }, []);

    // ✅ Cấu hình lực sau khi graph data được load
    useEffect(() => {
        if (fgRef.current) {
            fgRef.current.d3Force("link")?.distance(200); // tăng khoảng cách giữa các node
            fgRef.current.d3ReheatSimulation(); // chạy lại mô phỏng
        }
    }, [graphData]);

    return (
        <div
            style={{
                width: "100%",
                height: "700px",
                borderRadius: "12px",
                overflow: "hidden",
                boxShadow: "0 4px 20px rgba(0,0,0,0.2)",
                backgroundColor: "#1e1e1e",
            }}
        >
            <ForceGraph2D
                ref={fgRef}
                graphData={graphData}
                nodeAutoColorBy="color"
                nodeLabel={(node: any) => `${node.label}`}
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                    const fontSize = 12 / globalScale;
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, node.size, 0, 2 * Math.PI, false);
                    ctx.fillStyle = node === hoverNode ? "#ff7f50" : node.color;
                    ctx.shadowColor = "rgba(0,0,0,0.5)";
                    ctx.shadowBlur = 6;
                    ctx.fill();
                    ctx.font = `${fontSize}px Sans-Serif`;
                    ctx.textAlign = "center";
                    ctx.fillStyle = "#ffffff";
                    ctx.fillText(node.label, node.x, node.y - node.size - 4);
                }}
                onNodeHover={(node) => setHoverNode(node as NodeType | null)}
                linkColor={(link: any) => (link === hoverLink ? "#ff4500" : link.color)}
                linkWidth={(link: any) => (link === hoverLink ? 2.5 : 1)}
                linkLabel={(link: any) => link.label}
                onLinkHover={(link) => setHoverLink(link as LinkType | null)}
                enableNodeDrag={true}
                cooldownTicks={200}
                backgroundColor="#1e1e1e"
                linkDirectionalParticles={2}
                linkDirectionalParticleWidth={(link: any) => (link === hoverLink ? 3 : 0)}
                linkDirectionalParticleSpeed={0.005}
            />
        </div>
    );
};

export default PaperGraph;
