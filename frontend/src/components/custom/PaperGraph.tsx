import React, { useEffect, useState } from "react";

// Kiểu dữ liệu graph
type Node = {
    id: string;
    label: string;
    type?: string;
    color?: string;
};

type Edge = {
    from: string;
    to: string;
};

type GraphData = {
    nodes: Node[];
    edges: Edge[];
};

export default function GraphPage() {
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchGraph = async () => {
            try {
                setLoading(true);
                const res = await fetch(
                    "http://localhost:8000/api/v1/graph/2d?paper_id=PMC2910419&mode=key_knowledge&max_nodes=10&depth=2"
                );

                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

                const data = await res.json();
                console.log("Fetched graph:", data);

                // Nếu backend trả về { success: true, data: { nodes, edges } }
                if (data.success && data.data) {
                    setGraphData({
                        nodes: data.data.nodes || [],
                        edges: data.data.edges || [],
                    });
                } else {
                    setGraphData({ nodes: [], edges: [] });
                }
            } catch (err: any) {
                console.error(err);
                setError(err.message || "Unknown error");
            } finally {
                setLoading(false);
            }
        };

        fetchGraph();
    }, []);

    return (
        <div style={{ padding: 20, fontFamily: "Arial" }}>
            <h2>Graph Visualization</h2>
            {loading && <p>Loading graph...</p>}
            {error && <p style={{ color: "red" }}>Error: {error}</p>}

            {!loading && !error && (
                <>
                    <h3>Nodes</h3>
                    {graphData.nodes.length === 0 ? (
                        <p>No nodes found</p>
                    ) : (
                        <ul>
                            {graphData.nodes.map((node) => (
                                <li key={node.id} style={{ color: node.color || "#000" }}>
                                    {node.label} ({node.id})
                                </li>
                            ))}
                        </ul>
                    )}

                    <h3>Edges</h3>
                    {graphData.edges.length === 0 ? (
                        <p>No edges found</p>
                    ) : (
                        <ul>
                            {graphData.edges.map((edge, index) => (
                                <li key={index}>
                                    {edge.from} → {edge.to}
                                </li>
                            ))}
                        </ul>
                    )}
                </>
            )}
        </div>
    );
}
