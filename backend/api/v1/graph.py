"""
Graph API endpoints for 2D network visualization
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from .models.graph import GraphRequest, GraphResponse, GraphData
from .services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])

# Create a singleton instance of GraphService
graph_service = GraphService()


@router.post("/generate", response_model=GraphResponse)
async def generate_graph(request: GraphRequest) -> GraphResponse:
    """
    Generate graph data for 2D visualization
    
    Args:
        request: Graph generation request with paper_id, mode, depth, max_nodes
        
    Returns:
        Graph data with nodes and edges for visualization
    """
    try:
        # Validate mode
        valid_modes = ["author", "citing", "key_knowledge", "similar"]
        if request.mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode '{request.mode}'. Must be one of: {', '.join(valid_modes)}"
            )
        
        # Validate depth
        if request.depth < 1 or request.depth > 3:
            raise HTTPException(
                status_code=400,
                detail="Depth must be between 1 and 3"
            )
        
        # Validate max_nodes
        if request.max_nodes < 1 or request.max_nodes > 100:
            raise HTTPException(
                status_code=400,
                detail="max_nodes must be between 1 and 100"
            )
        
        # Generate graph data
        graph_data = await graph_service.generate_graph(
            paper_id=request.paper_id,
            mode=request.mode,
            depth=request.depth,
            max_nodes=request.max_nodes
        )
        
        return GraphResponse(
            success=True,
            data=graph_data,
            message=f"Graph generated successfully with {graph_data.total_nodes} nodes and {graph_data.total_edges} edges"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/modes")
async def get_available_modes() -> Dict[str, Any]:
    """
    Get available graph modes with descriptions
    
    Returns:
        Dictionary of available modes and their descriptions
    """
    modes = {
        "author": {
            "description": "Papers connected by shared authors",
            "color_scheme": "Blue-based",
            "typical_use": "Find papers by the same research group or collaborators"
        },
        "citing": {
            "description": "Papers connected by citation relationships",
            "color_scheme": "Green/Purple-based",
            "typical_use": "Explore citation networks and paper influence"
        },
        "key_knowledge": {
            "description": "Papers connected by shared key knowledge concepts",
            "color_scheme": "Orange-based",
            "typical_use": "Find papers with similar research concepts or methodologies"
        },
        "similar": {
            "description": "Papers connected by content similarity (embeddings/clustering)",
            "color_scheme": "Teal-based",
            "typical_use": "Discover papers with similar content or topics"
        }
    }
    
    return {
        "success": True,
        "modes": modes,
        "total_modes": len(modes)
    }


@router.get("/paper/{paper_id}/summary")
async def get_paper_graph_summary(paper_id: str) -> Dict[str, Any]:
    """
    Get a summary of graph possibilities for a specific paper
    
    Args:
        paper_id: Paper ID to analyze
        
    Returns:
        Summary of available graph connections for the paper
    """
    try:
        # Get basic paper info
        paper_info = await graph_service._get_paper_info(paper_id)
        if not paper_info:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        
        # Get connection counts for each mode
        author_connections = await graph_service._get_papers_by_same_authors(paper_id, 100)
        citing_connections = await graph_service._get_citing_papers(paper_id, 100)
        cited_connections = await graph_service._get_cited_papers(paper_id, 100)
        knowledge_connections = await graph_service._get_papers_by_key_knowledge(paper_id, 100)
        similar_connections = await graph_service._get_similar_papers(paper_id, 100)
        
        summary = {
            "paper_id": paper_id,
            "title": paper_info.get("title", ""),
            "year": paper_info.get("year"),
            "authors": paper_info.get("authors", []),
            "connection_counts": {
                "author": len(author_connections),
                "citing": len(citing_connections),
                "cited": len(cited_connections),
                "key_knowledge": len(knowledge_connections),
                "similar": len(similar_connections)
            },
            "recommendations": []
        }
        
        # Add recommendations based on connection counts
        if len(author_connections) > 0:
            summary["recommendations"].append({
                "mode": "author",
                "reason": f"Found {len(author_connections)} papers by shared authors"
            })
        
        if len(citing_connections) + len(cited_connections) > 0:
            summary["recommendations"].append({
                "mode": "citing",
                "reason": f"Found {len(citing_connections + cited_connections)} citation relationships"
            })
        
        if len(knowledge_connections) > 0:
            summary["recommendations"].append({
                "mode": "key_knowledge",
                "reason": f"Found {len(knowledge_connections)} papers with shared knowledge"
            })
        
        if len(similar_connections) > 0:
            summary["recommendations"].append({
                "mode": "similar",
                "reason": f"Found {len(similar_connections)} similar papers"
            })
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting paper summary: {str(e)}")
