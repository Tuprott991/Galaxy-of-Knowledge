"""
Statistics-related models
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class YearTrend(BaseModel):
    """Year trend data model"""
    year: int = Field(..., description="Publication year")
    count: int = Field(..., description="Number of papers published in this year")


class TrendData(BaseModel):
    """Trend data model"""
    yearly_trends: List[YearTrend] = Field(..., description="Yearly publication trends")
    total_papers: int = Field(..., description="Total number of papers")
    year_range: Dict[str, int] = Field(..., description="Year range with min and max years")
    peak_year: Dict[str, Any] = Field(..., description="Year with most publications")


class StatsResponse(BaseModel):
    """Statistics response model"""
    success: bool = Field(..., description="Request success status")
    data: Dict[str, Any] = Field(..., description="Statistics data")
    message: str = Field(..., description="Response message")


class TrendResponse(BaseModel):
    """Trend response model"""
    success: bool = Field(..., description="Request success status")
    data: TrendData = Field(..., description="Trend data")
    message: str = Field(..., description="Response message")
