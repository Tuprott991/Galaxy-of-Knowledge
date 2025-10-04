"""
Papers API Router
Handles all paper-related endpoints for Galaxy of Knowledge
"""
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from database.connect import connect, close_connection
from database.search import PaperSearch

# Setup logging
logger = logging.getLogger("api.v1.papers")

# Create router
router = APIRouter()


# =========================
# ===== Response Models ===
# =========================

class PaperVisualization(BaseModel):
    """Paper visualization data model"""
    paper_id: str = Field(..., description="Paper ID (PMCID)")
    title: str = Field(..., description="Paper title")
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: float = Field(..., description="Z coordinate")
    cluster: Optional[str] = Field(None, description="Cluster UUID")


class PaperHTMLContext(BaseModel):
    """Paper HTML context data model"""
    paper_id: str = Field(..., description="Paper ID (PMCID)")
    title: Optional[str] = Field(None, description="Paper title")
    html_context: Optional[str] = Field(None, description="HTML context content")
    has_html_context: bool = Field(..., description="Whether paper has HTML context")
    html_context_length: int = Field(..., description="Length of HTML context in characters")


class HTMLContextResponse(BaseModel):
    """HTML Context API response model"""
    success: bool = Field(..., description="Request success status")
    data: PaperHTMLContext = Field(..., description="Paper HTML context data")
    message: str = Field(..., description="Response message")


class PapersResponse(BaseModel):
    """Papers API response model"""
    success: bool = Field(..., description="Request success status")
    data: List[PaperVisualization] = Field(..., description="Papers data")
    count: int = Field(..., description="Number of papers returned")
    message: str = Field(..., description="Response message")


class StatsResponse(BaseModel):
    """Statistics response model"""
    success: bool = Field(..., description="Request success status")
    data: Dict[str, Any] = Field(..., description="Statistics data")
    message: str = Field(..., description="Response message")


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(False, description="Request success status")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")


class SearchPaper(BaseModel):
    """Search result paper model"""
    paper_id: str = Field(..., description="Paper ID")
    title: str = Field(..., description="Paper title")
    abstract: Optional[str] = Field(None, description="Paper abstract (truncated)")
    cluster: Optional[str] = Field(None, description="Cluster UUID")
    relevance_score: float = Field(..., description="Search relevance score")


class PaperDetail(BaseModel):
    """Detailed paper information model"""
    paper_id: str = Field(..., description="Paper ID")
    title: str = Field(..., description="Paper title")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    authors: Optional[List[str]] = Field(None, description="Paper authors")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    coordinates: Dict[str, Optional[float]] = Field(..., description="3D coordinates")
    cluster: Optional[str] = Field(None, description="Cluster UUID")
    cited_by: Optional[List[str]] = Field(None, description="Papers that cite this paper")
    references: Optional[List[str]] = Field(None, description="Papers referenced by this paper")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


# =========================
# ===== DB Dependency =====
# =========================

def get_db_connection():
    """Get database connection"""
    try:
        conn = connect()
        if not conn:
            raise HTTPException(status_code=500, detail="Failed to connect to database")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


# =========================
# ======== ROUTES =========
# =========================

@router.get(
    "/papers/visualization",
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
                cluster
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

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        papers_data = [
            PaperVisualization(
                paper_id=row[0],
                title=row[1],
                x=float(row[2]),
                y=float(row[3]),
                z=float(row[4]),
                cluster=row[5]
            )
            for row in results
        ]

        count = len(papers_data)
        message = f"Successfully retrieved {count} papers for visualization"
        logger.info(message)

        return PapersResponse(success=True, data=papers_data, count=count, message=message)

    except Exception as e:
        logger.exception("Error getting papers visualization")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve papers visualization: {e}")
    finally:
        close_connection(conn)


@router.get(
    "/papers/stats",
    response_model=StatsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_papers_statistics(conn=Depends(get_db_connection)):
    """Get comprehensive papers statistics"""
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM paper")
        total_papers = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                COUNT(plot_visualize_x) FILTER (WHERE plot_visualize_x IS NOT NULL) AS with_coords,
                COUNT(cluster) FILTER (WHERE cluster IS NOT NULL) AS with_clusters,
                COUNT(embeddings) FILTER (WHERE embeddings IS NOT NULL) AS with_embeddings,
                COUNT(summarize) FILTER (WHERE summarize IS NOT NULL) AS with_summaries
            FROM paper
        """)
        with_coords, with_clusters, with_embeddings, with_summaries = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(DISTINCT cluster)
            FROM paper
            WHERE cluster IS NOT NULL AND cluster != '-1'
        """)
        unique_clusters = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                CASE WHEN cluster = '-1' THEN 'Noise Points'
                     ELSE CONCAT('Cluster ', LEFT(cluster, 8), '...')
                END AS cluster_name,
                cluster,
                COUNT(*) AS count 
            FROM paper 
            WHERE cluster IS NOT NULL 
            GROUP BY cluster 
            ORDER BY count DESC 
            LIMIT 10
        """)
        cluster_distribution = [
            {"cluster_name": n, "cluster_id": c, "count": ct}
            for n, c, ct in cursor.fetchall()
        ]

        def ratio(a): return round((a / total_papers * 100) if total_papers else 0, 2)

        stats_data = {
            "totals": {
                "total_papers": total_papers,
                "papers_with_coordinates": with_coords,
                "papers_with_clusters": with_clusters,
                "papers_with_embeddings": with_embeddings,
                "papers_with_summaries": with_summaries,
                "unique_clusters": unique_clusters
            },
            "ratios": {
                "coordinate_ratio": ratio(with_coords),
                "cluster_ratio": ratio(with_clusters),
                "embedding_ratio": ratio(with_embeddings),
                "summary_ratio": ratio(with_summaries)
            },
            "cluster_distribution": cluster_distribution,
            "pipeline_status": {
                "data_ingestion": total_papers > 0,
                "embedding_generation": with_embeddings > 0,
                "coordinate_generation": with_coords > 0,
                "clustering": with_clusters > 0,
                "summarization": with_summaries > 0
            }
        }

        logger.info(f"Generated statistics for {total_papers} papers")
        return StatsResponse(success=True, data=stats_data, message="Successfully retrieved papers statistics")

    except Exception as e:
        logger.exception("Error getting papers statistics")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve papers statistics: {e}")
    finally:
        close_connection(conn)


@router.get(
    "/papers/{paper_id}/html-context",
    response_model=HTMLContextResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_paper_html_context(
    paper_id: str,
    conn=Depends(get_db_connection)
):
    """
    Get HTML context for a specific paper
    
    Returns the full HTML context content for a paper, if available.
    This endpoint is separate from the main paper detail endpoint to optimize
    performance when only HTML context is needed.
    """
    try:
        cursor = conn.cursor()
        
        # Get paper's HTML context and basic info
        cursor.execute("""
            SELECT paper_id, title, html_context
            FROM paper 
            WHERE paper_id = %s
        """, (paper_id,))
        
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"Paper {paper_id} not found"
            )
        
        paper_id_db, title, html_context = result
        
        # Process HTML context
        has_html_context = bool(html_context and html_context.strip())
        html_context_length = len(html_context) if html_context else 0
        
        paper_html_data = PaperHTMLContext(
            paper_id=paper_id_db,
            title=title,
            html_context=html_context,
            has_html_context=has_html_context,
            html_context_length=html_context_length
        )
        
        message = f"Successfully retrieved HTML context for paper {paper_id}"
        if not has_html_context:
            message += " (no HTML context available)"
        
        logger.info(f"Retrieved HTML context for paper {paper_id} (length: {html_context_length})")
        
        return HTMLContextResponse(
            success=True,
            data=paper_html_data,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting paper HTML context")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve HTML context: {str(e)}"
        )
    finally:
        close_connection(conn)


@router.get("/papers/search")
async def search_papers(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: Optional[int] = Query(50, ge=1, le=1000, description="Maximum results"),
    search_type: str = Query("semantic", regex="^(semantic|text)$", description="Search type: semantic or text"),
    distance_threshold: Optional[float] = Query(None, ge=0.0, le=2.0, description="Maximum distance threshold for semantic search"),
    cluster: Optional[str] = Query(None, description="Filter by specific cluster"),
    conn=Depends(get_db_connection)
):
    """
    Search papers by query using semantic or text search
    
    - **semantic**: Uses embedding vectors for semantic similarity
    - **text**: Traditional text matching on title, abstract, authors
    """
    try:
        if search_type == "semantic":
            # Use semantic search
            search_service = PaperSearch()
            search_service.conn = conn  # Reuse existing connection
            search_service.initialize()
            
            results = search_service.search(
                query=q, 
                top_k=limit,
                distance_threshold=distance_threshold,
                cluster=cluster
            )
            
            # Transform results to match API format
            papers_data = []
            for paper in results:
                papers_data.append({
                    "paper_id": paper["paper_id"],
                    "title": paper["title"],
                    "abstract": paper["abstract"][:300] + "..." if paper["abstract"] and len(paper["abstract"]) > 300 else paper["abstract"],
                    "cluster": paper["cluster"],
                    "authors": paper["authors"] or [],
                    "relevance_score": paper["similarity_score"],
                    "distance": paper["distance"],
                    "coordinates": paper["plot_coordinates"]
                })
                
        else:
            # Use traditional text search
            cursor = conn.cursor()
            search_query = f"%{q.lower()}%"
            
            # Build query with optional cluster filter
            base_query = """
                SELECT 
                    paper_id, title, abstract, cluster, author_list,
                    CASE 
                        WHEN LOWER(title) LIKE %s THEN 3
                        WHEN LOWER(abstract) LIKE %s THEN 2
                        WHEN LOWER(array_to_string(author_list, ' ')) LIKE %s THEN 1
                        ELSE 0 END AS relevance_score
                FROM paper 
                WHERE LOWER(title) LIKE %s 
                   OR LOWER(abstract) LIKE %s
                   OR LOWER(array_to_string(author_list, ' ')) LIKE %s
            """
            
            params = [search_query, search_query, search_query, search_query, search_query, search_query]
            
            if cluster:
                base_query += " AND cluster = %s"
                params.append(cluster)
                
            base_query += " ORDER BY relevance_score DESC, title LIMIT %s"
            params.append(limit)
            
            cursor.execute(base_query, tuple(params))
            results = cursor.fetchall()
            
            papers_data = []
            for pid, title, abstract, cluster_id, authors, score in results:
                if isinstance(authors, str):
                    try:
                        authors = json.loads(authors)
                    except Exception:
                        authors = [authors]
                        
                truncated = abstract[:300] + "..." if abstract and len(abstract) > 300 else abstract
                papers_data.append({
                    "paper_id": pid, 
                    "title": title, 
                    "abstract": truncated,
                    "cluster": cluster_id, 
                    "authors": authors or [], 
                    "relevance_score": float(score),
                    "distance": None,  # Not applicable for text search
                    "coordinates": None  # Not included in text search for performance
                })

        return {
            "success": True,
            "data": papers_data,
            "count": len(papers_data),
            "query": q,
            "search_type": search_type,
            "cluster_filter": cluster,
            "distance_threshold": distance_threshold,
            "message": f"Found {len(papers_data)} papers matching '{q}' using {search_type} search"
        }

    except Exception as e:
        logger.exception("Error searching papers")
        raise HTTPException(status_code=500, detail=f"Failed to search papers: {e}")
    finally:
        close_connection(conn)


@router.get("/papers/{paper_id}/similar")
async def get_similar_papers(
    paper_id: str,
    limit: Optional[int] = Query(10, ge=1, le=100, description="Maximum number of similar papers"),
    exclude_self: bool = Query(True, description="Exclude the reference paper from results"),
    conn=Depends(get_db_connection)
):
    """
    Find papers similar to a given paper using semantic embeddings
    """
    try:
        search_service = PaperSearch()
        search_service.conn = conn  # Reuse existing connection
        search_service.initialize()
        
        results = search_service.search_similar_papers(
            paper_id=paper_id,
            top_k=limit,
            exclude_self=exclude_self
        )
        
        # Transform results
        papers_data = []
        for paper in results:
            papers_data.append({
                "paper_id": paper["paper_id"],
                "title": paper["title"],
                "abstract": paper["abstract"][:200] + "..." if paper["abstract"] and len(paper["abstract"]) > 200 else paper["abstract"],
                "cluster": paper["cluster"],
                "authors": paper["authors"] or [],
                "similarity_score": paper["similarity_score"],
                "distance": paper["distance"],
                "coordinates": paper["plot_coordinates"]
            })
        
        return {
            "success": True,
            "data": papers_data,
            "count": len(papers_data),
            "reference_paper_id": paper_id,
            "exclude_self": exclude_self,
            "message": f"Found {len(papers_data)} papers similar to {paper_id}"
        }
        
    except Exception as e:
        logger.exception("Error finding similar papers")
        raise HTTPException(status_code=500, detail=f"Failed to find similar papers: {e}")
    finally:
        close_connection(conn)


@router.get("/papers/search/batch")
async def batch_search_papers(
    queries: List[str] = Query(..., description="List of search queries"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results per query"),
    conn=Depends(get_db_connection)
):
    """
    Perform batch semantic search for multiple queries
    """
    try:
        search_service = PaperSearch()
        search_service.conn = conn  # Reuse existing connection
        search_service.initialize()
        
        batch_results = search_service.batch_search(queries=queries, top_k=top_k)
        
        # Transform results
        formatted_results = {}
        for query, papers in batch_results.items():
            formatted_results[query] = [
                {
                    "paper_id": paper["paper_id"],
                    "title": paper["title"],
                    "abstract": paper["abstract"][:200] + "..." if paper["abstract"] and len(paper["abstract"]) > 200 else paper["abstract"],
                    "cluster": paper["cluster"],
                    "similarity_score": paper["similarity_score"],
                    "distance": paper["distance"]
                }
                for paper in papers
            ]
        
        total_results = sum(len(papers) for papers in formatted_results.values())
        
        return {
            "success": True,
            "data": formatted_results,
            "queries": queries,
            "total_queries": len(queries),
            "total_results": total_results,
            "results_per_query": top_k,
            "message": f"Completed batch search for {len(queries)} queries with {total_results} total results"
        }
        
    except Exception as e:
        logger.exception("Error in batch search")
        raise HTTPException(status_code=500, detail=f"Failed to perform batch search: {e}")
    finally:
        close_connection(conn)
async def get_paper_detail(paper_id: str, conn=Depends(get_db_connection)):
    """Get detailed information for a specific paper"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT paper_id, title, abstract, author_list, summarize,
                   plot_visualize_x, plot_visualize_y, plot_visualize_z,
                   cluster, cited_by, _references, created_at, updated_at, full_text
            FROM paper WHERE paper_id = %s
        """, (paper_id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")

        (pid, title, abstract, authors, summary, x, y, z, cluster,
         cited_by, references, created_at, updated_at, full_text) = result

        # Normalize authors
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors]

        # Get key knowledge (JOIN fix)
        cursor.execute("""
            SELECT context
            FROM key_knowledge kk
            JOIN paper p ON kk.paper_id = p.id
            WHERE p.paper_id = %s
            LIMIT 10
        """, (paper_id,))
        key_knowledge = []
        for (context,) in cursor.fetchall():
            if context:
                key_knowledge.extend(context)

        paper_data = {
            "paper_id": pid,
            "title": title,
            "abstract": abstract,
            "authors": authors or [],
            "summary": summary,
            "coordinates": {"x": float(x) if x else None, "y": float(y) if y else None, "z": float(z) if z else None},
            "cluster": cluster,
            "cited_by": cited_by or [],
            "references": references or [],
            "key_knowledge": key_knowledge[:10],
            "full_text_preview": (full_text[:500] + "...") if full_text and len(full_text) > 500 else full_text,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "processing_status": {
                "has_coordinates": all([x, y, z]),
                "has_cluster": cluster is not None,
                "has_summary": summary is not None,
                "has_key_knowledge": len(key_knowledge) > 0
            }
        }

        return {"success": True, "data": paper_data, "message": f"Successfully retrieved paper {paper_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting paper detail")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve paper detail: {e}")
    finally:
        close_connection(conn)


@router.get("/clusters/{cluster_id}/papers")
async def get_papers_by_cluster(
    cluster_id: str,
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum results"),
    conn=Depends(get_db_connection)
):
    """Get all papers in a specific cluster"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT paper_id, title, abstract, author_list,
                   plot_visualize_x, plot_visualize_y, plot_visualize_z
            FROM paper 
            WHERE cluster = %s
            ORDER BY title
            LIMIT %s
        """, (cluster_id, limit))
        results = cursor.fetchall()
        papers = []
        for pid, title, abstract, authors, x, y, z in results:
            if isinstance(authors, str):
                try:
                    authors = json.loads(authors)
                except Exception:
                    authors = [authors]
            papers.append({
                "paper_id": pid,
                "title": title,
                "abstract": abstract[:200] + "..." if abstract and len(abstract) > 200 else abstract,
                "authors": authors or [],
                "coordinates": {"x": float(x) if x else None, "y": float(y) if y else None, "z": float(z) if z else None}
            })

        return {
            "success": True,
            "data": papers,
            "count": len(papers),
            "cluster_id": cluster_id,
            "message": f"Found {len(papers)} papers in cluster {cluster_id}"
        }

    except Exception as e:
        logger.exception("Error getting papers by cluster")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve papers by cluster: {e}")
    finally:
        close_connection(conn)


@router.get("/clusters/summary")
async def get_clusters_summary(conn=Depends(get_db_connection)):
    """Get summary of all clusters"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            WITH cluster_stats AS (
                SELECT cluster,
                       COUNT(*) AS paper_count,
                       array_agg(title ORDER BY title)[1:3] AS sample_titles
                FROM paper
                WHERE cluster IS NOT NULL
                GROUP BY cluster
            )
            SELECT cluster, paper_count, sample_titles,
                   CASE WHEN cluster = '-1' THEN 'Noise Points'
                        ELSE CONCAT('Cluster ', LEFT(cluster, 8), '...') END AS cluster_name
            FROM cluster_stats
            ORDER BY CASE WHEN cluster = '-1' THEN 1 ELSE 0 END, paper_count DESC
        """)
        results = cursor.fetchall()

        clusters_data, total_clustered, noise_count = [], 0, 0
        for cid, count, samples, name in results:
            if cid == '-1':
                noise_count = count
            else:
                total_clustered += count
            clusters_data.append({
                "cluster_id": cid,
                "cluster_name": name,
                "paper_count": count,
                "sample_titles": samples or [],
                "is_noise": cid == '-1'
            })

        cursor.execute("SELECT COUNT(*) FROM paper WHERE cluster IS NOT NULL")
        total_with_clusters = cursor.fetchone()[0]
        clustering_ratio = round((total_clustered / total_with_clusters * 100) if total_with_clusters > 0 else 0, 2)

        summary = {
            "total_clusters": len([c for c in clusters_data if not c["is_noise"]]),
            "total_clustered_papers": total_clustered,
            "noise_points": noise_count,
            "clustering_ratio": clustering_ratio,
            "clusters": clusters_data
        }

        return {"success": True, "data": summary,
                "message": f"Successfully retrieved summary of {len(clusters_data)} clusters"}

    except Exception as e:
        logger.exception("Error getting clusters summary")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve clusters summary: {e}")
    finally:
        close_connection(conn)
