"""
Search-related models
"""
from typing import Optional
from pydantic import BaseModel, Field


class SearchPaper(BaseModel):
    """Search result paper model"""
    paper_id: str = Field(..., description="Paper ID")
    title: str = Field(..., description="Paper title")
    abstract: Optional[str] = Field(None, description="Paper abstract (truncated)")
    cluster: Optional[str] = Field(None, description="Cluster UUID")
    relevance_score: float = Field(..., description="Search relevance score")
    x: Optional[float] = Field(None, description="X coordinate for visualization")
    y: Optional[float] = Field(None, description="Y coordinate for visualization")
    z: Optional[float] = Field(None, description="Z coordinate for visualization")
