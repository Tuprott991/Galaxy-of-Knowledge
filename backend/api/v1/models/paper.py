"""
Paper-related models
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PaperVisualization(BaseModel):
    """Paper visualization data model"""
    paper_id: str = Field(..., description="Paper ID (PMCID)")
    title: str = Field(..., description="Paper title")
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: float = Field(..., description="Z coordinate")
    cluster: Optional[str] = Field(None, description="Cluster UUID")
    topic: str = Field(..., description="Paper topic/category")
    score: Optional[float] = Field(None, description="Relevance score")


class PaperHTMLContext(BaseModel):
    """Paper HTML context data model"""
    paper_id: str = Field(..., description="Paper ID (PMCID)")
    title: Optional[str] = Field(None, description="Paper title")
    html_context: Optional[str] = Field(None, description="HTML context content")
    authors: Optional[List[str]] = Field(None, description="Paper authors")
    has_html_context: bool = Field(..., description="Whether paper has HTML context")
    html_context_length: int = Field(..., description="Length of HTML context in characters")


class HTMLContextResponse(BaseModel):
    """HTML Context API response model"""
    success: bool = Field(..., description="Request success status")
    data: PaperHTMLContext = Field(..., description="Paper HTML context data")
    message: str = Field(..., description="Response message")


class PapersResponse(BaseModel):
    """Papers API response model"""
    success: bool = Field(..., description="Request success status")
    data: List[PaperVisualization] = Field(..., description="Papers data")
    count: int = Field(..., description="Number of papers returned")
    message: str = Field(..., description="Response message")


class PaperDetail(BaseModel):
    """Detailed paper information model"""
    paper_id: str = Field(..., description="Paper ID")
    title: str = Field(..., description="Paper title")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    authors: Optional[List[str]] = Field(None, description="Paper authors")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    coordinates: Dict[str, Optional[float]] = Field(..., description="3D coordinates")
    cluster: Optional[str] = Field(None, description="Cluster UUID")
    cited_by: Optional[List[str]] = Field(None, description="Papers that cite this paper")
    references: Optional[List[str]] = Field(None, description="Papers referenced by this paper")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
