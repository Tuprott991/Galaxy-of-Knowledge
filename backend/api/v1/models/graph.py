"""
Graph models for 2D network visualization
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Node(BaseModel):
    """Graph node representing a paper"""
    id: str = Field(..., description="Paper ID")
    label: str = Field(..., description="Paper title")
    type: str = Field(default="paper", description="Node type")
    size: int = Field(default=10, description="Node size for visualization")
    color: str = Field(default="#3498db", description="Node color")
    level: int = Field(..., description="Depth level (0, 1, or 2)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional paper metadata")


class Edge(BaseModel):
    """Graph edge representing relationship between papers"""
    source: str = Field(..., description="Source paper ID")
    target: str = Field(..., description="Target paper ID")
    type: str = Field(..., description="Relationship type")
    weight: float = Field(default=1.0, description="Edge weight/strength")
    label: str = Field(default="", description="Edge label")
    color: str = Field(default="#95a5a6", description="Edge color")
    relation: str = Field(..., description="Specific relation description (e.g., author names, citation context)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional edge metadata")


class GraphData(BaseModel):
    """Complete graph data structure"""
    nodes: List[Node] = Field(..., description="List of nodes")
    edges: List[Edge] = Field(..., description="List of edges")
    mode: str = Field(..., description="Graph mode used")
    center_paper_id: str = Field(..., description="Center paper ID")
    total_nodes: int = Field(..., description="Total number of nodes")
    total_edges: int = Field(..., description="Total number of edges")


class GraphRequest(BaseModel):
    """Request model for graph generation"""
    paper_id: str = Field(..., description="Center paper ID")
    mode: str = Field(..., description="Graph mode: author, citing, key_knowledge, similar")
    depth: int = Field(default=2, description="Graph depth (default: 2)")
    max_nodes: int = Field(default=50, description="Maximum number of nodes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "paper_id": "123e4567-e89b-12d3-a456-426614174000",
                "mode": "citing",
                "depth": 2,
                "max_nodes": 50
            }
        }


class GraphResponse(BaseModel):
    """Response model for graph API"""
    success: bool = Field(..., description="Request success status")
    data: Optional[GraphData] = Field(None, description="Graph data")
    message: str = Field(default="", description="Response message")
    error: Optional[str] = Field(None, description="Error message if any")
