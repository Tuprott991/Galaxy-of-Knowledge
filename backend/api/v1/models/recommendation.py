"""
Recommendation system models
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .base import BaseResponse


class RecommendationRequest(BaseModel):
    """Request model for paper recommendations"""
    query: str = Field(..., description="Search query or research interest")
    user_id: Optional[str] = Field(None, description="User ID for personalization")
    context: str = Field("general", description="Context: general, literature_review, recent_research, methodology")
    exclude_papers: Optional[List[str]] = Field(default_factory=list, description="Paper IDs to exclude")
    preferred_clusters: Optional[List[str]] = Field(default_factory=list, description="Preferred research clusters")
    min_score: Optional[float] = Field(0.0, ge=0.0, le=100.0, description="Minimum paper score threshold")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of recommendations")


class RecommendedPaper(BaseModel):
    """Single recommended paper model"""
    paper_id: str
    title: str
    abstract: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    
    # Scoring components
    final_score: float = Field(..., description="Final recommendation score (0-100)")
    semantic_score: float = Field(..., description="Semantic similarity score")
    authority_score: float = Field(..., description="Citation authority score")
    recency_score: float = Field(..., description="Publication recency score")
    diversity_score: float = Field(..., description="Topic diversity bonus")
    
    # Paper metadata
    publication_year: Optional[int] = None
    cluster: Optional[str] = None
    topic: Optional[str] = None
    citation_count: int = 0
    reference_count: int = 0
    paper_score: float = 0.0
    
    # Explanation
    recommendation_reason: str = Field(..., description="Why this paper was recommended")


class RecommendationResponse(BaseResponse):
    """Response model for paper recommendations"""
    data: List[RecommendedPaper]
    query: str
    context: str
    total_candidates: int = Field(..., description="Total papers considered")
    personalized: bool = Field(False, description="Whether recommendations are personalized")
    
    # Scoring statistics
    score_distribution: Dict[str, float] = Field(default_factory=dict, description="Score component averages")


class RecommendationStats(BaseModel):
    """Statistics about recommendation performance"""
    query: str
    execution_time_ms: float
    semantic_candidates: int
    authority_filtered: int
    final_recommendations: int
    avg_scores: Dict[str, float]
    cluster_distribution: Dict[str, int]
