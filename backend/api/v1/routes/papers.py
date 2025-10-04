"""
Papers-related API routes
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException

from ..models.paper import PapersResponse, HTMLContextResponse, PaperHTMLContext
from ..models.base import ErrorResponse
from ..models.stats import StatsResponse
from ..dependencies.database import get_db_connection
from database.connect import close_connection

papers_router = APIRouter(prefix="/papers", tags=["papers"])


@papers_router.get(
    "/visualization",
    response_model=PapersResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_papers_visualization(
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of papers to return"),
    conn=Depends(get_db_connection)
):
    """
    Get papers data for 3D visualization
    """
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                paper_id, title,
                plot_visualize_x AS x, 
                plot_visualize_y AS y, 
                plot_visualize_z AS z,
                cluster,
                topic
            FROM paper 
            WHERE plot_visualize_x IS NOT NULL 
              AND plot_visualize_y IS NOT NULL 
              AND plot_visualize_z IS NOT NULL
              AND title IS NOT NULL
            ORDER BY paper_id
        """
        params = []
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cursor.execute(query, params)
        papers = cursor.fetchall()
        
        paper_data = [
            {
                "paper_id": paper[0],
                "title": paper[1],
                "x": float(paper[2]),
                "y": float(paper[3]),
                "z": float(paper[4]),
                "cluster": paper[5],
                "topic": paper[6]
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
    finally:
        close_connection(conn)


@papers_router.get(
    "/stats",
    response_model=StatsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_papers_statistics(conn=Depends(get_db_connection)):
    """Get comprehensive papers statistics"""
    try:
        cursor = conn.cursor()
        
        # Total papers count
        cursor.execute("SELECT COUNT(*) FROM paper")
        total_papers = cursor.fetchone()[0]
        
        # Papers with coordinates
        cursor.execute("""
            SELECT COUNT(*) FROM paper 
            WHERE plot_visualize_x IS NOT NULL 
              AND plot_visualize_y IS NOT NULL 
              AND plot_visualize_z IS NOT NULL
        """)
        papers_with_coords = cursor.fetchone()[0]
        
        # Papers with clusters
        cursor.execute("SELECT COUNT(*) FROM paper WHERE cluster IS NOT NULL")
        papers_with_clusters = cursor.fetchone()[0]
        
        # Cluster distribution
        cursor.execute("""
            SELECT cluster, COUNT(*) as count 
            FROM paper 
            WHERE cluster IS NOT NULL 
            GROUP BY cluster 
            ORDER BY count DESC
        """)
        cluster_dist = cursor.fetchall()
        
        # Papers with HTML context
        cursor.execute("SELECT COUNT(*) FROM paper WHERE html_context IS NOT NULL")
        papers_with_html = cursor.fetchone()[0]
        
        stats_data = {
            "total_papers": total_papers,
            "papers_with_coordinates": papers_with_coords,
            "papers_with_clusters": papers_with_clusters,
            "papers_with_html_context": papers_with_html,
            "cluster_distribution": [
                {"cluster": row[0], "count": row[1]} for row in cluster_dist
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
    finally:
        close_connection(conn)


@papers_router.get(
    "/{paper_id}/html-context",
    response_model=HTMLContextResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_paper_html_context(
    paper_id: str,
    conn=Depends(get_db_connection)
):
    """
    Get HTML context for a specific paper by paper_id
    """
    try:
        cursor = conn.cursor()
        
        # Query to get paper HTML context
        query = """
            SELECT 
                paper_id,
                title,
                html_context,
                authors
            FROM paper 
            WHERE paper_id = %s
        """
        
        cursor.execute(query, (paper_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"Paper with ID '{paper_id}' not found"
            )
        
        paper_data = PaperHTMLContext(
            paper_id=result[0],
            title=result[1],
            html_context=result[2],
            authors=result[3].split(", ") if result[3] else [],
            has_html_context=result[2] is not None,
            html_context_length=len(result[2]) if result[2] else 0
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
    finally:
        close_connection(conn)
