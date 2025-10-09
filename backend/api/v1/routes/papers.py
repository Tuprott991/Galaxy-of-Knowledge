"""
Papers-related API routes (Async)
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
import asyncpg

from ..models.paper import PapersResponse, HTMLContextResponse, PaperHTMLContext
from ..models.base import ErrorResponse
from ..models.stats import StatsResponse
from ..dependencies.database import get_db
from services.recommendation_engine import get_recommendation_engine
from services.score_calculator import get_score_calculator

papers_router = APIRouter(prefix="/papers", tags=["papers"])


@papers_router.get(
    "/visualization",
    response_model=PapersResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_papers_visualization(
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of papers to return")
):
    """
    Get papers data for 3D visualization
    """
    try:
        from database.connect import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    paper_id, title,
                    plot_visualize_x AS x, 
                    plot_visualize_y AS y, 
                    plot_visualize_z AS z,
                    cluster,
                    topic,
                    score
                FROM paper 
                WHERE plot_visualize_x IS NOT NULL 
                  AND plot_visualize_y IS NOT NULL 
                  AND plot_visualize_z IS NOT NULL
                  AND title IS NOT NULL
                ORDER BY paper_id
            """
            
            if limit:
                query += " LIMIT $1"
                papers = await conn.fetch(query, limit)
            else:
                papers = await conn.fetch(query)
            
            paper_data = [
                {
                    "paper_id": paper['paper_id'],
                    "title": paper['title'],
                    "x": float(paper['x']),
                    "y": float(paper['y']),
                    "z": float(paper['z']),
                    "cluster": paper['cluster'],
                    "topic": paper['topic'],
                    "score": paper['score'] if paper['score'] is not None else 0
                }
                for paper in papers
            ]
            
            return PapersResponse(
                success=True,
                data=paper_data,
                count=len(paper_data),
                message=f"Retrieved {len(paper_data)} papers successfully"
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve papers: {str(e)}")


@papers_router.get(
    "/stats",
    response_model=StatsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_papers_statistics():
    """Get comprehensive papers statistics"""
    try:
        from database.connect import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Total papers count
            total_papers = await conn.fetchval("SELECT COUNT(*) FROM paper")
            
            # Papers with coordinates
            papers_with_coords = await conn.fetchval("""
                SELECT COUNT(*) FROM paper 
                WHERE plot_visualize_x IS NOT NULL 
                  AND plot_visualize_y IS NOT NULL 
                  AND plot_visualize_z IS NOT NULL
            """)
            
            # Papers with clusters
            papers_with_clusters = await conn.fetchval(
                "SELECT COUNT(*) FROM paper WHERE cluster IS NOT NULL"
            )
            
            # Cluster distribution
            cluster_dist = await conn.fetch("""
                SELECT cluster, COUNT(*) as count 
                FROM paper 
                WHERE cluster IS NOT NULL 
                GROUP BY cluster 
                ORDER BY count DESC
            """)
            
            # Papers with HTML context
            papers_with_html = await conn.fetchval(
                "SELECT COUNT(*) FROM paper WHERE html_context IS NOT NULL"
            )
            
            stats_data = {
                "total_papers": total_papers,
                "papers_with_coordinates": papers_with_coords,
                "papers_with_clusters": papers_with_clusters,
                "papers_with_html_context": papers_with_html,
                "cluster_distribution": [
                    {"cluster": row['cluster'], "count": row['count']} for row in cluster_dist
                ],
                "coverage": {
                    "coordinates": round((papers_with_coords / total_papers) * 100, 2) if total_papers > 0 else 0,
                    "clusters": round((papers_with_clusters / total_papers) * 100, 2) if total_papers > 0 else 0,
                    "html_context": round((papers_with_html / total_papers) * 100, 2) if total_papers > 0 else 0
                }
            }
            
            return StatsResponse(
                success=True,
                data=stats_data,
                message="Statistics retrieved successfully"
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


@papers_router.get(
    "/{paper_id}/html-context",
    response_model=HTMLContextResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_paper_html_context(paper_id: str):
    """
    Get HTML context for a specific paper by paper_id
    """
    try:
        from database.connect import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Query to get paper HTML context - fixed to use author_list instead of authors
            query = """
                SELECT 
                    paper_id,
                    title,
                    html_context,
                    author_list
                FROM paper 
                WHERE paper_id = $1
            """
            
            result = await conn.fetchrow(query, paper_id)
            
            if not result:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Paper with ID '{paper_id}' not found"
                )
            
            # author_list is already an array in PostgreSQL
            authors_list = result['author_list'] if result['author_list'] else []
            
            paper_data = PaperHTMLContext(
                paper_id=result['paper_id'],
                title=result['title'],
                html_context=result['html_context'],
                authors=authors_list,
                has_html_context=result['html_context'] is not None,
                html_context_length=len(result['html_context']) if result['html_context'] else 0
            )
            
            return HTMLContextResponse(
                success=True,
                data=paper_data,
                message=f"HTML context for paper '{paper_id}' retrieved successfully"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve HTML context: {str(e)}"
        )


@papers_router.get("/recommendations")
async def get_paper_recommendations(
    query: str = Query(..., description="Search query or research interest"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    context: str = Query("general", description="Context: general, literature_review, recent_research, methodology"),
    user_id: Optional[str] = Query(None, description="User ID for personalization"),
    exclude_papers: Optional[str] = Query(None, description="Comma-separated paper IDs to exclude"),
    preferred_clusters: Optional[str] = Query(None, description="Comma-separated preferred clusters"),
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum recommendation score")
):
    """
    Get personalized paper recommendations using hybrid multi-signal approach
    
    Combines:
    - Semantic similarity (40%) - Content relevance via embeddings
    - Citation authority (30%) - Impact and quality metrics  
    - Publication recency (20%) - Temporal relevance
    - Topic diversity (10%) - Exploration bonus
    
    Context modes:
    - general: Balanced recommendations
    - literature_review: Emphasizes high-impact papers
    - recent_research: Prioritizes recent publications
    - methodology: Focuses on methodological relevance
    """
    try:
        # Parse optional parameters
        exclude_list = exclude_papers.split(',') if exclude_papers else []
        cluster_list = preferred_clusters.split(',') if preferred_clusters else []
        
        # Initialize recommendation engine
        rec_engine = get_recommendation_engine()
        rec_engine.initialize()
        
        try:
            # Get user's preferred clusters if user_id provided
            user_clusters = []
            if user_id:
                user_clusters = rec_engine.get_user_preference_clusters(user_id)
                # Merge with explicitly provided clusters
                user_clusters.extend(cluster_list)
                user_clusters = list(set(user_clusters))  # Remove duplicates
            else:
                user_clusters = cluster_list
            
            # Generate recommendations
            recommendations, stats = rec_engine.recommend_papers(
                query=query,
                limit=limit,
                context=context,
                user_clusters=user_clusters,
                exclude_papers=exclude_list,
                min_score=min_score
            )
            
            # Format response - simple data return for frontend
            return {
                "success": True,
                "data": recommendations,
                "query": query,
                "context": context,
                "total_candidates": stats.get('semantic_candidates', 0),
                "personalized": bool(user_id),
                "score_distribution": stats.get('avg_scores', {}),
                "statistics": {
                    "execution_time_ms": stats.get('execution_time_ms', 0),
                    "candidates_evaluated": stats.get('total_scored', 0),
                    "final_count": len(recommendations),
                    "cluster_distribution": stats.get('cluster_distribution', {}),
                    "context_weights": stats.get('context_weights', {})
                },
                "message": f"Generated {len(recommendations)} recommendations for '{query}' in {context} context"
            }
            
        finally:
            rec_engine.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@papers_router.get("/recommendations/similar/{paper_id}")
async def get_similar_paper_recommendations(
    paper_id: str,
    limit: int = Query(10, ge=1, le=30, description="Number of similar papers"),
    exclude_self: bool = Query(True, description="Exclude the source paper from results"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")
):
    """
    Get papers similar to a specific paper using embeddings and metadata
    
    Uses the same hybrid scoring but anchored to a specific paper instead of query
    """
    try:
        rec_engine = get_recommendation_engine()
        rec_engine.initialize()
        
        try:
            # Use the search engine's similar papers function
            similar_papers = rec_engine.search_engine.search_similar_papers(
                paper_id=paper_id,
                top_k=limit,
                exclude_self=exclude_self
            )
            
            # Filter by similarity threshold
            filtered_papers = [
                paper for paper in similar_papers 
                if paper.get('similarity_score', 0) >= min_similarity
            ]
            
            # Enhance with recommendation reasons
            for paper in filtered_papers:
                similarity = paper.get('similarity_score', 0)
                if similarity > 0.8:
                    paper['recommendation_reason'] = "Very high content similarity"
                elif similarity > 0.6:
                    paper['recommendation_reason'] = "Strong content similarity"
                else:
                    paper['recommendation_reason'] = "Moderate content similarity"
            
            return {
                "success": True,
                "data": filtered_papers,
                "source_paper_id": paper_id,
                "total_found": len(similar_papers),
                "filtered_count": len(filtered_papers),
                "min_similarity_threshold": min_similarity,
                "message": f"Found {len(filtered_papers)} papers similar to {paper_id}"
            }
            
        finally:
            rec_engine.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find similar papers: {str(e)}"
        )


@papers_router.post("/calculate-score/{paper_id}")
async def calculate_paper_score(paper_id: str):
    """
    Calculate and update score for a specific paper
    
    Score components:
    - Citation count (40%) - Impact through citations
    - Reference quality (25%) - Research thoroughness  
    - Recency (20%) - Publication freshness
    - Cluster popularity (15%) - Topic relevance
    """
    try:
        calculator = get_score_calculator()
        result = calculator.calculate_and_update_single_paper(paper_id)
        
        if result["success"]:
            return {
                "success": True,
                "paper_id": paper_id,
                "score": result["score"],
                "score_breakdown": result["components"],
                "metadata": result["metadata"],
                "message": f"Score calculated and updated for paper {paper_id}"
            }
        else:
            raise HTTPException(
                status_code=404 if "not found" in result["error"].lower() else 500,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate score: {str(e)}"
        )


@papers_router.post("/calculate-scores/batch")
async def batch_calculate_scores(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of papers to process")
):
    """
    Calculate and update scores for multiple papers in batch
    
    Useful for bulk score updates or initial score calculation
    """
    try:
        calculator = get_score_calculator()
        result = calculator.batch_calculate_scores(limit=limit)
        
        return {
            "success": result["success"],
            "statistics": {
                "total_processed": result.get("total_processed", 0),
                "successful_updates": result.get("successful", 0),
                "failed_updates": result.get("failed", 0),
                "success_rate": f"{(result.get('successful', 0) / max(result.get('total_processed', 1), 1) * 100):.1f}%"
            },
            "sample_results": result.get("results", []),
            "message": f"Processed {result.get('total_processed', 0)} papers, {result.get('successful', 0)} successful updates"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch calculate scores: {str(e)}"
        )


@papers_router.get("/{paper_id}/score")
async def get_paper_score(paper_id: str):
    """
    Get current score and scoring details for a specific paper
    """
    try:
        from database.connect import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT 
                    paper_id,
                    title,
                    COALESCE(score, 0) as score,
                    COALESCE(array_length(cited_by, 1), 0) as citation_count,
                    COALESCE(array_length(_references, 1), 0) as reference_count,
                    cluster,
                    COALESCE(
                        CASE 
                            WHEN json_data->>'published_date' ~ '^[0-9]{4}' 
                            THEN substring(json_data->>'published_date' from '^([0-9]{4})')::int
                        END,
                        CASE 
                            WHEN json_data->>'year' ~ '^[0-9]{4}$' 
                            THEN (json_data->>'year')::int
                        END,
                        LEAST(EXTRACT(YEAR FROM created_at)::int, 2025)
                    ) as publication_year,
                    updated_at
                FROM paper 
                WHERE paper_id = $1
            """, paper_id)
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Paper with ID '{paper_id}' not found"
                )
            
            # Calculate component scores for breakdown
            calculator = get_score_calculator()
            
            paper_data = {
                'citation_count': result['citation_count'],
                'reference_count': result['reference_count'],
                'cluster': result['cluster'],
                'publication_year': result['publication_year']
            }
            
            # Get component scores
            citation_score = calculator.calculate_citation_score(paper_data['citation_count'])
            reference_score = calculator.calculate_reference_score(paper_data['reference_count'])
            recency_score = calculator.calculate_recency_score(paper_data['publication_year'])
            
            return {
                "success": True,
                "paper_id": result['paper_id'],
                "title": result['title'],
                "current_score": result['score'],
                "score_breakdown": {
                    "citation_score": round(citation_score, 2),
                    "reference_score": round(reference_score, 2),
                    "recency_score": round(recency_score, 2),
                    "components_weighted": {
                        "citations": round(citation_score * 0.40, 2),
                        "references": round(reference_score * 0.25, 2),
                        "recency": round(recency_score * 0.20, 2),
                        "cluster": round(result['score'] - (citation_score * 0.40 + reference_score * 0.25 + recency_score * 0.20), 2)
                    }
                },
                "metadata": {
                    "citation_count": result['citation_count'],
                    "reference_count": result['reference_count'],
                    "cluster": result['cluster'],
                    "publication_year": result['publication_year'],
                    "last_updated": result['updated_at'].isoformat() if result['updated_at'] else None
                },
                "message": f"Score details for paper {paper_id}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve paper score: {str(e)}"
        )
