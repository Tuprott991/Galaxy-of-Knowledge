"""
Clusters-related API routes
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException

from ..models.paper import PapersResponse, PaperVisualization
from ..models.base import ErrorResponse
from ..dependencies.database import get_db_connection
from database.connect import close_connection

clusters_router = APIRouter(prefix="/clusters", tags=["clusters"])


@clusters_router.get("/{cluster_id}/papers")
async def get_cluster_papers(
    cluster_id: str,
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of papers to return"),
    conn=Depends(get_db_connection)
):
    """
    Get all papers in a specific cluster
    """
    try:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                paper_id, title,
                plot_visualize_x AS x, 
                plot_visualize_y AS y, 
                plot_visualize_z AS z,
                cluster
            FROM paper 
            WHERE cluster = %s
              AND plot_visualize_x IS NOT NULL 
              AND plot_visualize_y IS NOT NULL 
              AND plot_visualize_z IS NOT NULL
              AND title IS NOT NULL
            ORDER BY paper_id
        """
        params = [cluster_id]
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cursor.execute(query, params)
        papers = cursor.fetchall()
        
        if not papers:
            # Check if cluster exists at all
            cursor.execute("SELECT COUNT(*) FROM paper WHERE cluster = %s", (cluster_id,))
            cluster_count = cursor.fetchone()[0]
            
            if cluster_count == 0:
                raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found")
            else:
                # Cluster exists but no papers have coordinates
                return PapersResponse(
                    success=True,
                    data=[],
                    count=0,
                    message=f"Cluster '{cluster_id}' exists but contains no papers with visualization coordinates"
                )
        
        paper_data = [
            PaperVisualization(
                paper_id=paper[0],
                title=paper[1],
                x=float(paper[2]),
                y=float(paper[3]),
                z=float(paper[4]),
                cluster=paper[5]
            )
            for paper in papers
        ]
        
        return PapersResponse(
            success=True,
            data=paper_data,
            count=len(paper_data),
            message=f"Retrieved {len(paper_data)} papers from cluster '{cluster_id}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cluster papers: {str(e)}")
    finally:
        close_connection(conn)


@clusters_router.get("/summary")
async def get_clusters_summary(conn=Depends(get_db_connection)):
    """
    Get summary information about all clusters
    """
    try:
        cursor = conn.cursor()
        
        # Get cluster statistics
        cursor.execute("""
            SELECT 
                cluster,
                COUNT(*) as paper_count,
                COUNT(CASE WHEN plot_visualize_x IS NOT NULL 
                           AND plot_visualize_y IS NOT NULL 
                           AND plot_visualize_z IS NOT NULL 
                      THEN 1 END) as papers_with_coords,
                AVG(plot_visualize_x) as avg_x,
                AVG(plot_visualize_y) as avg_y,
                AVG(plot_visualize_z) as avg_z
            FROM paper 
            WHERE cluster IS NOT NULL
            GROUP BY cluster
            ORDER BY paper_count DESC
        """)
        
        cluster_stats = cursor.fetchall()
        
        # Total statistics
        cursor.execute("SELECT COUNT(DISTINCT cluster) FROM paper WHERE cluster IS NOT NULL")
        total_clusters = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM paper WHERE cluster IS NOT NULL")
        total_clustered_papers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM paper")
        total_papers = cursor.fetchone()[0]
        
        clusters_data = [
            {
                "cluster_id": row[0],
                "paper_count": row[1],
                "papers_with_coordinates": row[2],
                "centroid": {
                    "x": float(row[3]) if row[3] else None,
                    "y": float(row[4]) if row[4] else None,
                    "z": float(row[5]) if row[5] else None
                }
            }
            for row in cluster_stats
        ]
        
        summary_data = {
            "total_clusters": total_clusters,
            "total_clustered_papers": total_clustered_papers,
            "total_papers": total_papers,
            "clustering_coverage": round((total_clustered_papers / total_papers) * 100, 2) if total_papers > 0 else 0,
            "clusters": clusters_data
        }
        
        return {
            "success": True,
            "data": summary_data,
            "message": f"Retrieved summary for {total_clusters} clusters covering {total_clustered_papers} papers"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve clusters summary: {str(e)}")
    finally:
        close_connection(conn)
