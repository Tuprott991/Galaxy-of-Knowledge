"""
API Routes Package
"""
from .papers import papers_router
from .search import search_router
from .clusters import clusters_router
from .stats import stats_router

__all__ = ["papers_router", "search_router", "clusters_router", "stats_router"]
