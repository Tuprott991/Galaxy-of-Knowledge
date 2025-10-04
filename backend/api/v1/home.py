"""
Main API router that combines all route modules
"""
from fastapi import APIRouter

from .routes.papers import papers_router
from .routes.search import search_router  
from .routes.clusters import clusters_router
from .routes.stats import stats_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(papers_router)
router.include_router(search_router)
router.include_router(clusters_router)
router.include_router(stats_router)
