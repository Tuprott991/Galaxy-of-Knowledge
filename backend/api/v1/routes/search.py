"""
Search-related API routes
"""
from typing import Optional, List, Union
from fastapi import APIRouter, Depends, Query, HTTPException

from ..models.search import SearchPaper
from ..models.paper import PapersResponse, PaperVisualization
from ..models.base import ErrorResponse
from database.search import semantic_search

search_router = APIRouter(prefix="/papers", tags=["search"])


@search_router.get("/search")
async def search_papers(
    query: str = Query(..., description="Search query text"),
    search_type: str = Query("semantic", description="Type of search: semantic, title, abstract, or hybrid"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return")
):
    """
    Search papers using various search methods
    
    - **semantic**: Vector-based semantic search using embeddings
    - **title**: Text search in paper titles
    - **abstract**: Text search in paper abstracts  
    - **hybrid**: Combination of semantic and text search
    """
    try:
        from database.connect import get_db_pool
        
        if search_type == "semantic":
            # Use the semantic search function from database.search
            results = semantic_search(query, limit)
            
            # Format results for API response
            search_results = []
            for result in results:
                # Extract coordinates from nested structure if present
                plot_coords = result.get('plot_coordinates', {})
                x = plot_coords.get('x') if plot_coords else result.get('x')
                y = plot_coords.get('y') if plot_coords else result.get('y')
                z = plot_coords.get('z') if plot_coords else result.get('z')
                
                search_results.append(SearchPaper(
                    paper_id=result['paper_id'],
                    title=result['title'],
                    abstract=result.get('abstract', '')[:300] + "..." if result.get('abstract') and len(result.get('abstract', '')) > 300 else result.get('abstract'),
                    cluster=result.get('cluster'),
                    relevance_score=result['similarity_score'],
                    x=x,
                    y=y,
                    z=z
                ))
            
        elif search_type == "title":
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT paper_id, title, abstract, cluster, 
                           similarity(title, $1) as score, x, y, z
                    FROM paper 
                    WHERE title ILIKE $2
                    ORDER BY score DESC, title
                    LIMIT $3
                """, query, f"%{query}%", limit)
                
                search_results = [
                    SearchPaper(
                        paper_id=row['paper_id'],
                        title=row['title'],
                        abstract=row['abstract'][:300] + "..." if row['abstract'] and len(row['abstract']) > 300 else row['abstract'],
                        cluster=row['cluster'],
                        relevance_score=float(row['score']) if row['score'] else 0.0,
                        x=float(row['x']) if row['x'] is not None else None,
                        y=float(row['y']) if row['y'] is not None else None,
                        z=float(row['z']) if row['z'] is not None else None
                    )
                    for row in results
                ]
            
        elif search_type == "abstract":
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT paper_id, title, abstract, cluster,
                           similarity(abstract, $1) as score, x, y, z
                    FROM paper 
                    WHERE abstract ILIKE $2
                    ORDER BY score DESC, title
                    LIMIT $3
                """, query, f"%{query}%", limit)
                
                search_results = [
                    SearchPaper(
                        paper_id=row['paper_id'],
                        title=row['title'],
                        abstract=row['abstract'][:300] + "..." if row['abstract'] and len(row['abstract']) > 300 else row['abstract'],
                        cluster=row['cluster'],
                        relevance_score=float(row['score']) if row['score'] else 0.0,
                        x=float(row['x']) if row['x'] is not None else None,
                        y=float(row['y']) if row['y'] is not None else None,
                        z=float(row['z']) if row['z'] is not None else None
                    )
                    for row in results
                ]
            
        elif search_type == "hybrid":
            # Combine semantic and text search
            semantic_results = semantic_search(query, limit // 2)
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                text_results = await conn.fetch("""
                    SELECT paper_id, title, abstract, cluster,
                           GREATEST(
                               similarity(title, $1),
                               similarity(COALESCE(abstract, ''), $2)
                           ) as score, x, y, z
                    FROM paper 
                    WHERE title ILIKE $3 OR abstract ILIKE $4
                    ORDER BY score DESC, title
                    LIMIT $5
                """, query, query, f"%{query}%", f"%{query}%", limit // 2)
            
            # Combine and deduplicate results
            all_results = {}
            
            # Add semantic results
            for result in semantic_results:
                # Extract coordinates from nested structure if present
                plot_coords = result.get('plot_coordinates', {})
                x = plot_coords.get('x') if plot_coords else result.get('x')
                y = plot_coords.get('y') if plot_coords else result.get('y')
                z = plot_coords.get('z') if plot_coords else result.get('z')
                
                all_results[result['paper_id']] = SearchPaper(
                    paper_id=result['paper_id'],
                    title=result['title'],
                    abstract=result.get('abstract', '')[:300] + "..." if result.get('abstract') and len(result.get('abstract', '')) > 300 else result.get('abstract'),
                    cluster=result.get('cluster'),
                    relevance_score=result['similarity_score'],
                    x=x,
                    y=y,
                    z=z
                )
            
                # Add text results (with slightly lower weight)
                for row in text_results:
                    paper_id = row['paper_id']
                    if paper_id not in all_results:
                        all_results[paper_id] = SearchPaper(
                            paper_id=row['paper_id'],
                            title=row['title'],
                            abstract=row['abstract'][:300] + "..." if row['abstract'] and len(row['abstract']) > 300 else row['abstract'],
                            cluster=row['cluster'],
                            relevance_score=float(row['score']) * 0.8 if row['score'] else 0.0,  # Slight penalty for text search
                            x=float(row['x']) if row['x'] is not None else None,
                            y=float(row['y']) if row['y'] is not None else None,
                            z=float(row['z']) if row['z'] is not None else None
                        )
            
                # Sort by relevance score and limit
                search_results = sorted(all_results.values(), key=lambda x: x.relevance_score, reverse=True)[:limit]
            
        else:
            raise HTTPException(status_code=400, detail=f"Invalid search_type: {search_type}")
        
        return {
            "success": True,
            "data": search_results,
            "count": len(search_results),
            "search_type": search_type,
            "query": query,
            "message": f"Found {len(search_results)} papers matching '{query}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@search_router.get("/{paper_id}/similar")
async def get_similar_papers(
    paper_id: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of similar papers to return")
):
    """
    Get papers similar to the specified paper using semantic similarity
    """
    try:
        from database.connect import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # First check if the paper exists
            source_paper = await conn.fetchrow("SELECT title FROM paper WHERE paper_id = $1", paper_id)
            
            if not source_paper:
                raise HTTPException(status_code=404, detail=f"Paper with ID '{paper_id}' not found")
            
            # Use semantic search with the paper's title as query
            # This is a simplified approach - ideally we'd use the paper's embedding directly
            results = semantic_search(source_paper['title'], limit + 1)  # +1 to exclude the source paper
            
            # Filter out the source paper itself
            similar_papers = []
            for result in results:
                if result['paper_id'] != paper_id:
                    # Extract coordinates from nested structure if present
                    plot_coords = result.get('plot_coordinates', {})
                    x = plot_coords.get('x') if plot_coords else result.get('x')
                    y = plot_coords.get('y') if plot_coords else result.get('y')
                    z = plot_coords.get('z') if plot_coords else result.get('z')
                    
                    similar_papers.append(SearchPaper(
                        paper_id=result['paper_id'],
                        title=result['title'],
                        abstract=result.get('abstract', '')[:300] + "..." if result.get('abstract') and len(result.get('abstract', '')) > 300 else result.get('abstract'),
                        cluster=result.get('cluster'),
                        relevance_score=result['similarity_score'],
                        x=x,
                        y=y,
                        z=z
                    ))
            similar_papers = similar_papers[:limit]
            
            return {
                "success": True,
                "data": similar_papers,
                "count": len(similar_papers),
                "source_paper_id": paper_id,
                "source_paper_title": source_paper['title'],
                "message": f"Found {len(similar_papers)} similar papers to '{source_paper['title']}'"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find similar papers: {str(e)}")


@search_router.get("/search/batch")
async def batch_search_papers(
    queries: str = Query(..., description="Comma-separated list of search queries"),
    search_type: str = Query("semantic", description="Type of search to use for all queries"),
    limit_per_query: int = Query(5, ge=1, le=20, description="Maximum results per query")
):
    """
    Perform batch search for multiple queries
    """
    try:
        query_list = [q.strip() for q in queries.split(',') if q.strip()]
        
        if not query_list:
            raise HTTPException(status_code=400, detail="No valid queries provided")
        
        if len(query_list) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 queries allowed per batch")
        
        batch_results = {}
        
        for query in query_list:
            if search_type == "semantic":
                results = semantic_search(query, limit_per_query)
                search_results = []
                for result in results:
                    # Extract coordinates from nested structure if present
                    plot_coords = result.get('plot_coordinates', {})
                    x = plot_coords.get('x') if plot_coords else result.get('x')
                    y = plot_coords.get('y') if plot_coords else result.get('y')
                    z = plot_coords.get('z') if plot_coords else result.get('z')
                    
                    search_results.append(SearchPaper(
                        paper_id=result['paper_id'],
                        title=result['title'],
                        abstract=result.get('abstract', '')[:200] + "..." if result.get('abstract') and len(result.get('abstract', '')) > 200 else result.get('abstract'),
                        cluster=result.get('cluster'),
                        relevance_score=result['similarity_score'],
                        x=x,
                        y=y,
                        z=z
                    ))
            else:
                # For simplicity, only semantic search is implemented for batch
                # Other search types would need connection management
                raise HTTPException(status_code=400, detail="Batch search currently only supports semantic search")
            
            batch_results[query] = {
                "results": search_results,
                "count": len(search_results)
            }
        
        return {
            "success": True,
            "data": batch_results,
            "total_queries": len(query_list),
            "search_type": search_type,
            "message": f"Completed batch search for {len(query_list)} queries"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch search failed: {str(e)}")
