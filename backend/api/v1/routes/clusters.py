"""
Clusters-related API routes
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException

from ..models.paper import PapersResponse, PaperVisualization
from ..models.base import ErrorResponse
from ..models.treemap import ClusterTopic, TreemapNode, TreemapResponse
from ..dependencies.database import get_db_connection
from database.connect import close_connection
from services.topic_generator import get_topic_generator

# Setup logging
logger = logging.getLogger(__name__)

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


@clusters_router.get("/{cluster_id}/topic")
async def get_cluster_topic(
    cluster_id: str,
    conn=Depends(get_db_connection)
):
    """
    Generate and return topic for a specific cluster based on paper titles
    """
    try:
        cursor = conn.cursor()
        
        # Get paper titles for the cluster
        cursor.execute("""
            SELECT paper_id, title
            FROM paper 
            WHERE cluster = %s AND title IS NOT NULL
            ORDER BY paper_id
        """, (cluster_id,))
        
        results = cursor.fetchall()
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found or has no papers")
        
        # Extract titles
        titles = [row[1] for row in results]
        
        # Generate topic using AI
        topic_generator = get_topic_generator()
        topic_name, confidence = topic_generator.generate_topic_from_titles(titles, cluster_id)
        
        # Prepare response
        cluster_topic = ClusterTopic(
            cluster_id=cluster_id,
            topic=topic_name,
            confidence=confidence,
            paper_count=len(results),
            sample_titles=titles[:5]  # First 5 titles as samples
        )
        
        return {
            "success": True,
            "data": cluster_topic,
            "message": f"Generated topic for cluster '{cluster_id}' with {len(titles)} papers"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate cluster topic: {str(e)}")
    finally:
        close_connection(conn)


@clusters_router.get("/topics/all")
async def get_all_cluster_topics(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum number of clusters to process"),
    min_papers: int = Query(3, ge=1, description="Minimum number of papers required in cluster"),
    conn=Depends(get_db_connection)
):
    """
    Generate topics for all clusters with sufficient papers
    """
    try:
        cursor = conn.cursor()
        
        # Get all clusters with paper counts
        query = """
            SELECT 
                cluster,
                COUNT(*) as paper_count,
                array_agg(title ORDER BY paper_id) as titles
            FROM paper 
            WHERE cluster IS NOT NULL AND title IS NOT NULL
            GROUP BY cluster
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
        """
        params = [min_papers]
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            return {
                "success": True,
                "data": [],
                "message": f"No clusters found with at least {min_papers} papers"
            }
        
        # Generate topics for each cluster
        topic_generator = get_topic_generator()
        cluster_topics = []
        
        for row in results:
            cluster_id = row[0]
            paper_count = row[1]
            titles = row[2]  # PostgreSQL array
            
            try:
                # Generate topic
                topic_name, confidence = topic_generator.generate_topic_from_titles(titles, cluster_id)
                
                cluster_topic = ClusterTopic(
                    cluster_id=cluster_id,
                    topic=topic_name,
                    confidence=confidence,
                    paper_count=paper_count,
                    sample_titles=titles[:5]  # First 5 titles
                )
                cluster_topics.append(cluster_topic)
                
            except Exception as e:
                logger.error(f"Failed to generate topic for cluster {cluster_id}: {e}")
                # Add fallback topic
                cluster_topic = ClusterTopic(
                    cluster_id=cluster_id,
                    topic=f"Research Cluster {cluster_id[:8]}",
                    confidence=0.1,
                    paper_count=paper_count,
                    sample_titles=titles[:5]
                )
                cluster_topics.append(cluster_topic)
        
        return {
            "success": True,
            "data": cluster_topics,
            "total_clusters": len(cluster_topics),
            "message": f"Generated topics for {len(cluster_topics)} clusters"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate cluster topics: {str(e)}")
    finally:
        close_connection(conn)


@clusters_router.get("/treemap")
async def get_treemap_data(
    min_papers: int = Query(3, ge=1, description="Minimum papers per cluster"),
    max_clusters: int = Query(50, ge=1, le=200, description="Maximum clusters to include"),
    conn=Depends(get_db_connection)
):
    """
    Get treemap data for dashboard visualization with AI-generated topics
    """
    try:
        cursor = conn.cursor()
        
        # Get clusters with paper counts and titles
        cursor.execute("""
            SELECT 
                cluster,
                COUNT(*) as paper_count,
                array_agg(title ORDER BY paper_id) as titles
            FROM paper 
            WHERE cluster IS NOT NULL AND title IS NOT NULL
            GROUP BY cluster
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
            LIMIT %s
        """, (min_papers, max_clusters))
        
        results = cursor.fetchall()
        
        if not results:
            return TreemapResponse(
                success=True,
                data=[],
                total_clusters=0,
                total_papers=0,
                message=f"No clusters found with at least {min_papers} papers"
            )
        
        # Generate topics and create treemap nodes
        topic_generator = get_topic_generator()
        treemap_nodes = []
        total_papers = 0
        
        for row in results:
            cluster_id = row[0]
            paper_count = row[1]
            titles = row[2]
            
            try:
                # Generate topic
                topic_name, confidence = topic_generator.generate_topic_from_titles(titles, cluster_id)
                
                # Create treemap node
                node = TreemapNode(
                    name=topic_name,
                    value=paper_count,
                    cluster_id=cluster_id,
                    topic=topic_name,
                    confidence=confidence
                )
                treemap_nodes.append(node)
                total_papers += paper_count
                
            except Exception as e:
                logger.error(f"Failed to process cluster {cluster_id}: {e}")
                # Add fallback node
                fallback_topic = f"Cluster {cluster_id[:8]}"
                node = TreemapNode(
                    name=fallback_topic,
                    value=paper_count,
                    cluster_id=cluster_id,
                    topic=fallback_topic,
                    confidence=0.1
                )
                treemap_nodes.append(node)
                total_papers += paper_count
        
        # Sort by paper count (value) for better visualization
        treemap_nodes.sort(key=lambda x: x.value, reverse=True)
        
        return TreemapResponse(
            success=True,
            data=treemap_nodes,
            total_clusters=len(treemap_nodes),
            total_papers=total_papers,
            message=f"Generated treemap data for {len(treemap_nodes)} clusters with {total_papers} papers"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate treemap data: {str(e)}")
    finally:
        close_connection(conn)


@clusters_router.get("/topics/saved")
async def get_saved_cluster_topics(
    min_papers: int = Query(3, ge=1, description="Minimum papers per cluster"),
    limit: Optional[int] = Query(None, ge=1, le=200, description="Maximum clusters to return"),
    conn=Depends(get_db_connection)
):
    """
    Get pre-generated topics from database (much faster than AI generation)
    """
    try:
        cursor = conn.cursor()
        
        # Get clusters with saved topics
        query = """
            SELECT 
                cluster,
                topic,
                COUNT(*) as paper_count,
                array_agg(title ORDER BY paper_id) as sample_titles
            FROM paper 
            WHERE cluster IS NOT NULL 
              AND topic IS NOT NULL 
              AND topic != ''
              AND title IS NOT NULL
            GROUP BY cluster, topic
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
        """
        params = [min_papers]
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        if not results:
            return {
                "success": True,
                "data": [],
                "message": f"No clusters found with saved topics and at least {min_papers} papers"
            }
        
        # Format response
        cluster_topics = []
        for row in results:
            cluster_id = row[0]
            topic = row[1]
            paper_count = row[2]
            sample_titles = row[3]
            
            cluster_topic = ClusterTopic(
                cluster_id=cluster_id,
                topic=topic,
                confidence=1.0,  # Pre-saved topics have full confidence
                paper_count=paper_count,
                sample_titles=sample_titles[:5]  # First 5 titles
            )
            cluster_topics.append(cluster_topic)
        
        return {
            "success": True,
            "data": cluster_topics,
            "total_clusters": len(cluster_topics),
            "message": f"Retrieved {len(cluster_topics)} pre-saved cluster topics from database"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve saved topics: {str(e)}")
    finally:
        close_connection(conn)


@clusters_router.get("/treemap/saved")
async def get_saved_treemap_data(
    min_papers: int = Query(3, ge=1, description="Minimum papers per cluster"),
    max_clusters: int = Query(50, ge=1, le=200, description="Maximum clusters to include"),
    conn=Depends(get_db_connection)
):
    """
    Get treemap data using pre-saved topics from database (fastest option)
    """
    try:
        cursor = conn.cursor()
        
        # Get clusters with saved topics
        cursor.execute("""
            SELECT 
                cluster,
                topic,
                COUNT(*) as paper_count
            FROM paper 
            WHERE cluster IS NOT NULL 
              AND topic IS NOT NULL 
              AND topic != ''
            GROUP BY cluster, topic
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
            LIMIT %s
        """, (min_papers, max_clusters))
        
        results = cursor.fetchall()
        
        if not results:
            return TreemapResponse(
                success=True,
                data=[],
                total_clusters=0,
                total_papers=0,
                message=f"No clusters found with saved topics and at least {min_papers} papers"
            )
        
        # Create treemap nodes from saved data
        treemap_nodes = []
        total_papers = 0
        
        for row in results:
            cluster_id = row[0]
            topic = row[1]
            paper_count = row[2]
            
            # Create treemap node
            node = TreemapNode(
                name=topic,
                value=paper_count,
                cluster_id=cluster_id,
                topic=topic,
                confidence=1.0  # Pre-saved topics have full confidence
            )
            treemap_nodes.append(node)
            total_papers += paper_count
        
        return TreemapResponse(
            success=True,
            data=treemap_nodes,
            total_clusters=len(treemap_nodes),
            total_papers=total_papers,
            message=f"Retrieved treemap data for {len(treemap_nodes)} clusters with {total_papers} papers from saved topics"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate treemap from saved topics: {str(e)}")
    finally:
        close_connection(conn)
