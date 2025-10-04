"""
Statistics-related models
"""
from typing import Dict, Any
from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    """Statistics response model"""
    success: bool = Field(..., description="Request success status")
    data: Dict[str, Any] = Field(..., description="Statistics data")
    message: str = Field(..., description="Response message")
