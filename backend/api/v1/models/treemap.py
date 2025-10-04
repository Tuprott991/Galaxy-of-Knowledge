"""
Treemap and topic analysis models
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ClusterTopic(BaseModel):
    """Topic information for a cluster"""
    cluster_id: str = Field(..., description="Cluster UUID")
    topic: str = Field(..., description="AI-generated topic name")
    confidence: float = Field(..., description="Confidence score (0-1)")
    paper_count: int = Field(..., description="Number of papers in cluster")
    sample_titles: List[str] = Field(..., description="Sample paper titles from cluster")


class TreemapNode(BaseModel):
    """Treemap node data structure"""
    name: str = Field(..., description="Topic/cluster name")
    value: int = Field(..., description="Number of papers")
    cluster_id: str = Field(..., description="Cluster UUID")
    topic: str = Field(..., description="Generated topic")
    confidence: float = Field(..., description="Topic confidence score")
    children: Optional[List[Dict[str, Any]]] = Field(None, description="Child nodes for hierarchical treemap")


class TreemapResponse(BaseModel):
    """Treemap API response model"""
    success: bool = Field(..., description="Request success status")
    data: List[TreemapNode] = Field(..., description="Treemap nodes data")
    total_clusters: int = Field(..., description="Total number of clusters")
    total_papers: int = Field(..., description="Total number of papers")
    message: str = Field(..., description="Response message")
