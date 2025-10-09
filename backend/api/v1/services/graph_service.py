"""
Graph service for generating 2D network visualization data (Async)
"""

import asyncio
from typing import List, Dict, Set, Tuple, Optional, Any
import asyncpg

from ..models.graph import Node, Edge, GraphData
from database.connect import get_db_pool


class GraphService:
    """Async service for generating graph data for 2D visualization"""
    
    def __init__(self):
        pass
    
    async def get_db_connection(self) -> asyncpg.Connection:
        """Get async database connection from pool"""
        pool = await get_db_pool()
        return await pool.acquire()
    
    async def generate_graph(self, paper_id: str, mode: str, depth: int = 2, max_nodes: int = 50) -> GraphData:
        """
        Generate graph data based on mode and depth
        
        Args:
            paper_id: Center paper ID
            mode: Graph mode (author, citing, key_knowledge, similar)
            depth: Graph depth (default: 2)
            max_nodes: Maximum number of nodes
        
        Returns:
            GraphData object with nodes and edges
        """
        if mode == "author":
            return await self._generate_author_graph(paper_id, depth, max_nodes)
        elif mode == "citing":
            return await self._generate_citing_graph(paper_id, depth, max_nodes)
        elif mode == "key_knowledge":
            return await self._generate_key_knowledge_graph(paper_id, depth, max_nodes)
        elif mode == "similar":
            return await self._generate_similar_graph(paper_id, depth, max_nodes)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
    
    async def _generate_author_graph(self, paper_id: str, depth: int, max_nodes: int) -> GraphData:
        """Generate graph based on author relationships"""
        
        nodes = {}
        edges = []
        visited_papers = set()
        
        # Add center paper with enhanced metadata
        center_paper = await self._get_paper_info(paper_id)
        if not center_paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        nodes[paper_id] = Node(
            id=paper_id,
            label=center_paper['title'][:50] + "..." if len(center_paper['title']) > 50 else center_paper['title'],
            type="paper",
            level=0,
            size=20,
            color="#e74c3c",  # Red for center
            metadata={
                "paper_id": center_paper['paper_id'],
                "title": center_paper['title'],
                "abstract": center_paper['abstract'][:500] + "..." if center_paper['abstract'] and len(center_paper['abstract']) > 500 else center_paper['abstract'],
                "author_list": center_paper['author_list'],
                "cluster": center_paper['cluster'],
                "topic": center_paper['topic'],
                "score": center_paper['score'],
                "citation_count": center_paper['citation_count'],
                "author_count": center_paper['author_count'],
                "knowledge_context_count": center_paper['knowledge_context_count'],
                "coordinates": {
                    "x": center_paper['plot_visualize_x'],
                    "y": center_paper['plot_visualize_y'],
                    "z": center_paper['plot_visualize_z']
                },
                "created_at": center_paper['created_at'].isoformat() if center_paper['created_at'] else None,
                "summary": center_paper['summarize']
            }
        )
        visited_papers.add(paper_id)
        
        # Level 1: Papers by same authors
        level1_papers = await self._get_papers_by_same_authors(paper_id, max_nodes // 2)
        for paper in level1_papers:
            if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                # Add related paper node with rich metadata
                nodes[paper['paper_id']] = Node(
                    id=paper['paper_id'],
                    label=paper['title'][:40] + "..." if len(paper['title']) > 40 else paper['title'],
                    type="paper",
                    level=1,
                    size=15,
                    color="#3498db",  # Blue for level 1
                    metadata={
                        "paper_id": paper['paper_id'],
                        "title": paper['title'],
                        "abstract": paper['abstract'][:300] + "..." if paper['abstract'] and len(paper['abstract']) > 300 else paper['abstract'],
                        "cluster": paper['cluster'],
                        "topic": paper['topic'],
                        "score": paper['score'],
                        "citation_count": paper['citation_count'],
                        "author_count": paper['author_count'],
                        "shared_authors_count": paper['shared_authors_count'],
                        "shared_author_names": paper['shared_author_names'],
                        "avg_author_productivity": paper.get('avg_author_productivity'),
                        "same_cluster": paper.get('same_cluster', False),
                        "created_at": paper['created_at'].isoformat() if paper['created_at'] else None
                    }
                )
                visited_papers.add(paper['paper_id'])
                
                # Add edge with comprehensive metadata
                shared_authors_names = paper.get('shared_author_names', [])
                author_names_str = ", ".join(shared_authors_names[:3])  # Take max 3 names
                if len(shared_authors_names) > 3:
                    author_names_str += f" and {len(shared_authors_names) - 3} other authors"
                
                # Determine collaboration strength
                collaboration_strength = "strong" if paper.get('shared_authors_count', 1) >= 3 else \
                                       "medium" if paper.get('shared_authors_count', 1) == 2 else "weak"
                
                edges.append(Edge(
                    source=paper_id,
                    target=paper['paper_id'],
                    type="author",
                    label="shared authors",
                    color="#f39c12",
                    weight=min(paper.get('shared_authors_count', 1) / 5.0, 1.0),  # Normalize weight
                    relation=f"Shared authors: {author_names_str}",
                    metadata={
                        "shared_authors_count": paper.get('shared_authors_count', 1),
                        "shared_author_names": shared_authors_names,
                        "collaboration_strength": collaboration_strength,
                        "same_cluster": paper.get('same_cluster', False),
                        "author_productivity_score": paper.get('avg_author_productivity'),
                        "target_citation_count": paper['citation_count'],
                        "level": 1,
                        "relationship_type": "co_authorship"
                    }
                ))
        
        # Level 2: Papers by authors of level 1 papers
        if depth >= 2:
            for level1_paper_id in list(visited_papers - {paper_id}):
                level2_papers = await self._get_papers_by_same_authors(level1_paper_id, 5)
                for paper in level2_papers:
                    if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                        nodes[paper['paper_id']] = Node(
                            id=paper['paper_id'],
                            label=paper['title'][:30] + "..." if len(paper['title']) > 30 else paper['title'],
                            level=2,
                            size=10,
                            color="#95a5a6",  # Gray for level 2
                            metadata=paper
                        )
                        visited_papers.add(paper['paper_id'])
                        
                        # Add edge
                        shared_authors_names = paper.get('shared_author_names', [])
                        author_names_str = ", ".join(shared_authors_names[:2])  # Level 2 only take 2 names
                        if len(shared_authors_names) > 2:
                            author_names_str += f" and {len(shared_authors_names) - 2} other authors"
                        
                        edges.append(Edge(
                            source=level1_paper_id,
                            target=paper['paper_id'],
                            type="author",
                            label="same author",
                            color="#bdc3c7",
                            relation=f"{author_names_str} also authored this paper",
                            metadata={
                                "shared_authors_count": paper.get('shared_authors_count', 1),
                                "shared_author_names": shared_authors_names,
                                "level": 2,
                                "relationship_strength": "weak",
                                "connection_type": "extended_coauthorship"
                            }
                        ))
        
        return GraphData(
            nodes=list(nodes.values()),
            edges=edges,
            mode="author",
            center_paper_id=paper_id,
            total_nodes=len(nodes),
            total_edges=len(edges)
        )
    
    async def _generate_citing_graph(self, paper_id: str, depth: int, max_nodes: int) -> GraphData:
        """Generate graph based on citation relationships"""
        
        nodes = {}
        edges = []
        visited_papers = set()
        
        # Add center paper
        center_paper = await self._get_paper_info(paper_id)
        if not center_paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        nodes[paper_id] = Node(
            id=paper_id,
            label=center_paper['title'][:50] + "..." if len(center_paper['title']) > 50 else center_paper['title'],
            level=0,
            size=20,
            color="#e74c3c",
            metadata=center_paper
        )
        visited_papers.add(paper_id)
        
        # Level 1: Papers that cite this paper + papers cited by this paper
        citing_papers = await self._get_citing_papers(paper_id, max_nodes // 4)
        cited_papers = await self._get_cited_papers(paper_id, max_nodes // 4)
        
        # Add citing papers
        for paper in citing_papers:
            if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                nodes[paper['paper_id']] = Node(
                    id=paper['paper_id'],
                    label=paper['title'][:40] + "..." if len(paper['title']) > 40 else paper['title'],
                    level=1,
                    size=15,
                    color="#2ecc71",  # Green for citing
                    metadata=paper
                )
                visited_papers.add(paper['paper_id'])
                
                edges.append(Edge(
                    source=paper['paper_id'],
                    target=paper_id,
                    type="cites",
                    label="cites",
                    color="#27ae60",
                    relation=f"Paper '{paper['title'][:30]}...' cites the center paper",
                    metadata={
                        "citation_type": "incoming",
                        "level": 1,
                        "relationship_strength": "medium"
                    }
                ))
        
        # Add cited papers
        for paper in cited_papers:
            if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                nodes[paper['paper_id']] = Node(
                    id=paper['paper_id'],
                    label=paper['title'][:40] + "..." if len(paper['title']) > 40 else paper['title'],
                    level=1,
                    size=15,
                    color="#9b59b6",  # Purple for cited
                    metadata=paper
                )
                visited_papers.add(paper['paper_id'])
                
                edges.append(Edge(
                    source=paper_id,
                    target=paper['paper_id'],
                    type="cites",
                    label="cites",
                    color="#8e44ad",
                    relation=f"Center paper cites '{paper['title'][:30]}...'",
                    metadata={
                        "citation_type": "outgoing",
                        "level": 1,
                        "relationship_strength": "medium"
                    }
                ))
        
        # Level 2: Second-order citations
        if depth >= 2:
            level1_papers = list(visited_papers - {paper_id})
            for level1_paper_id in level1_papers:
                if len(nodes) >= max_nodes:
                    break
                
                # Get a few citing/cited papers for each level 1 paper
                second_citing = await self._get_citing_papers(level1_paper_id, 3)
                second_cited = await self._get_cited_papers(level1_paper_id, 3)
                
                for paper in second_citing + second_cited:
                    if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                        nodes[paper['paper_id']] = Node(
                            id=paper['paper_id'],
                            label=paper['title'][:30] + "..." if len(paper['title']) > 30 else paper['title'],
                            level=2,
                            size=10,
                            color="#95a5a6",
                            metadata=paper
                        )
                        visited_papers.add(paper['paper_id'])
                        
                        # Determine edge direction
                        if paper in second_citing:
                            edges.append(Edge(
                                source=paper['paper_id'],
                                target=level1_paper_id,
                                type="cites",
                                label="cites",
                                color="#bdc3c7",
                                relation=f"Indirect citation via '{paper['title'][:20]}...'",
                                metadata={
                                    "citation_type": "second_order_incoming",
                                    "level": 2,
                                    "relationship_strength": "weak"
                                }
                            ))
                        else:
                            edges.append(Edge(
                                source=level1_paper_id,
                                target=paper['paper_id'],
                                type="cites",
                                label="cites",
                                color="#bdc3c7",
                                relation=f"Indirect citation to '{paper['title'][:20]}...'",
                                metadata={
                                    "citation_type": "second_order_outgoing",
                                    "level": 2,
                                    "relationship_strength": "weak"
                                }
                            ))
        
        return GraphData(
            nodes=list(nodes.values()),
            edges=edges,
            mode="citing",
            center_paper_id=paper_id,
            total_nodes=len(nodes),
            total_edges=len(edges)
        )
    
    async def _generate_key_knowledge_graph(self, paper_id: str, depth: int, max_nodes: int) -> GraphData:
        """Generate graph based on key knowledge relationships"""
        
        nodes = {}
        edges = []
        visited_papers = set()
        
        # Add center paper
        center_paper = await self._get_paper_info(paper_id)
        if not center_paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        nodes[paper_id] = Node(
            id=paper_id,
            label=center_paper['title'][:50] + "..." if len(center_paper['title']) > 50 else center_paper['title'],
            level=0,
            size=20,
            color="#e74c3c",
            metadata=center_paper
        )
        visited_papers.add(paper_id)
        
        # Level 1: Papers with shared key knowledge
        related_papers = await self._get_papers_by_key_knowledge(paper_id, max_nodes // 2)
        for paper in related_papers:
            if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                nodes[paper['paper_id']] = Node(
                    id=paper['paper_id'],
                    label=paper['title'][:40] + "..." if len(paper['title']) > 40 else paper['title'],
                    level=1,
                    size=15,
                    color="#f39c12",  # Orange for key knowledge
                    metadata=paper
                )
                visited_papers.add(paper['paper_id'])
                
                edges.append(Edge(
                    source=paper_id,
                    target=paper['paper_id'],
                    type="key_knowledge",
                    label="shared knowledge",
                    color="#e67e22",
                    weight=paper.get('similarity_score', 1.0),
                    relation=f"{paper.get('similarity_score', 0.0):.1%} knowledge similarity based on embeddings",
                    metadata={
                        "knowledge_count": paper.get('knowledge_count', 1),
                        "similarity_score": paper.get('similarity_score', 0.0),
                        "level": 1,
                        "relationship_strength": "strong" if paper.get('similarity_score', 0) > 0.8 else 
                                               "medium" if paper.get('similarity_score', 0) > 0.6 else "weak",
                        "similarity_type": "embedding_based"
                    }
                ))
        
        # Level 2: Papers related to level 1 papers through key knowledge
        if depth >= 2:
            level1_papers = list(visited_papers - {paper_id})
            for level1_paper_id in level1_papers:
                if len(nodes) >= max_nodes:
                    break
                
                level2_papers = await self._get_papers_by_key_knowledge(level1_paper_id, 5)
                for paper in level2_papers:
                    if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                        nodes[paper['paper_id']] = Node(
                            id=paper['paper_id'],
                            label=paper['title'][:30] + "..." if len(paper['title']) > 30 else paper['title'],
                            level=2,
                            size=10,
                            color="#95a5a6",
                            metadata=paper
                        )
                        visited_papers.add(paper['paper_id'])
                        
                        edges.append(Edge(
                            source=level1_paper_id,
                            target=paper['paper_id'],
                            type="key_knowledge",
                            label="shared knowledge",
                            color="#bdc3c7",
                            weight=paper.get('similarity_score', 1.0),
                            relation=f"Indirect knowledge similarity {paper.get('similarity_score', 0.0):.1%}",
                            metadata={
                                "knowledge_count": paper.get('knowledge_count', 1),
                                "similarity_score": paper.get('similarity_score', 0.0),
                                "level": 2,
                                "relationship_strength": "weak",
                                "similarity_type": "indirect_embedding"
                            }
                        ))
        
        return GraphData(
            nodes=list(nodes.values()),
            edges=edges,
            mode="key_knowledge",
            center_paper_id=paper_id,
            total_nodes=len(nodes),
            total_edges=len(edges)
        )
    
    async def _generate_similar_graph(self, paper_id: str, depth: int, max_nodes: int) -> GraphData:
        """Generate graph based on similarity relationships"""
        
        nodes = {}
        edges = []
        visited_papers = set()
        
        # Add center paper
        center_paper = await self._get_paper_info(paper_id)
        if not center_paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        nodes[paper_id] = Node(
            id=paper_id,
            label=center_paper['title'][:50] + "..." if len(center_paper['title']) > 50 else center_paper['title'],
            level=0,
            size=20,
            color="#e74c3c",
            metadata=center_paper
        )
        visited_papers.add(paper_id)
        
        # Level 1: Most similar papers
        similar_papers = await self._get_similar_papers(paper_id, max_nodes // 2)
        for paper in similar_papers:
            if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                nodes[paper['paper_id']] = Node(
                    id=paper['paper_id'],
                    label=paper['title'][:40] + "..." if len(paper['title']) > 40 else paper['title'],
                    level=1,
                    size=15,
                    color="#1abc9c",  # Teal for similar
                    metadata=paper
                )
                visited_papers.add(paper['paper_id'])
                
                edges.append(Edge(
                    source=paper_id,
                    target=paper['paper_id'],
                    type="similar",
                    label=f"similarity: {paper.get('similarity_score', 0.0):.2f}",
                    color="#16a085",
                    weight=paper.get('similarity_score', 1.0),
                    relation=f"{paper.get('similarity_score', 0.0):.1%} similarity to center paper",
                    metadata={
                        "similarity_score": paper.get('similarity_score', 0.0),
                        "similarity_type": "content_based",
                        "level": 1,
                        "relationship_strength": "strong" if paper.get('similarity_score', 0) > 0.8 else 
                                               "medium" if paper.get('similarity_score', 0) > 0.5 else "weak"
                    }
                ))
        
        # Level 2: Papers similar to level 1 papers
        if depth >= 2:
            level1_papers = list(visited_papers - {paper_id})
            for level1_paper_id in level1_papers:
                if len(nodes) >= max_nodes:
                    break
                
                level2_papers = await self._get_similar_papers(level1_paper_id, 5)
                for paper in level2_papers:
                    if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                        nodes[paper['paper_id']] = Node(
                            id=paper['paper_id'],
                            label=paper['title'][:30] + "..." if len(paper['title']) > 30 else paper['title'],
                            level=2,
                            size=10,
                            color="#95a5a6",
                            metadata=paper
                        )
                        visited_papers.add(paper['paper_id'])
                        
                        edges.append(Edge(
                            source=level1_paper_id,
                            target=paper['paper_id'],
                            type="similar",
                            label=f"similarity: {paper.get('similarity_score', 0.0):.2f}",
                            color="#bdc3c7",
                            weight=paper.get('similarity_score', 1.0),
                            relation=f"Indirect similarity {paper.get('similarity_score', 0.0):.1%}",
                            metadata={
                                "similarity_score": paper.get('similarity_score', 0.0),
                                "similarity_type": "indirect",
                                "level": 2,
                                "relationship_strength": "weak"
                            }
                        ))
        
        return GraphData(
            nodes=list(nodes.values()),
            edges=edges,
            mode="similar",
            center_paper_id=paper_id,
            total_nodes=len(nodes),
            total_edges=len(edges)
        )
    
    # Database query methods
    
    async def _get_paper_info(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive paper information with rich metadata"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                query = """
                    SELECT 
                        p.paper_id, 
                        p.title, 
                        p.abstract, 
                        p.author_list,
                        p.cluster,
                        p.topic,
                        p.score,
                        p.summarize,
                        p.cited_by,
                        p.plot_visualize_x,
                        p.plot_visualize_y,
                        p.plot_visualize_z,
                        p.created_at,
                        p.updated_at,
                        -- Calculate derived metrics
                        COALESCE(array_length(p.cited_by, 1), 0) as citation_count,
                        COALESCE(array_length(p.author_list, 1), 0) as author_count,
                        -- Get key knowledge context count
                        (SELECT COUNT(*) FROM key_knowledge kk WHERE kk.paper_id = p.id) as knowledge_context_count
                    FROM paper p
                    WHERE p.paper_id = $1
                """
                
                result = await conn.fetchrow(query, paper_id)
                return dict(result) if result else None
                
        except Exception as e:
            print(f"Error getting paper info: {e}")
            return None
    
    async def _get_papers_by_same_authors(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers by same authors with comprehensive metadata"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                query = """
                WITH paper_authors AS (
                    SELECT DISTINCT author_name
                    FROM paper p, unnest(p.author_list) as author_name
                    WHERE p.paper_id = %s
                ),
                author_productivity AS (
                    SELECT 
                        author_name,
                        COUNT(DISTINCT p.paper_id) as total_papers,
                        AVG(COALESCE(array_length(p.cited_by, 1), 0)) as avg_citations
                    FROM paper p, unnest(p.author_list) as author_name
                    WHERE author_name IN (SELECT author_name FROM paper_authors)
                    GROUP BY author_name
                ),
                related_papers AS (
                    SELECT DISTINCT 
                        p.paper_id, 
                        p.title, 
                        p.abstract,
                        p.cluster,
                        p.topic,
                        p.score,
                        COALESCE(array_length(p.cited_by, 1), 0) as citation_count,
                        COALESCE(array_length(p.author_list, 1), 0) as author_count,
                        p.created_at,
                        (
                            SELECT COUNT(*)
                            FROM unnest(p.author_list) as author_name
                            WHERE author_name IN (SELECT author_name FROM paper_authors)
                        ) as shared_authors_count,
                        (
                            SELECT COALESCE(array_agg(author_name), ARRAY[]::text[])
                            FROM unnest(p.author_list) as author_name
                            WHERE author_name IN (SELECT author_name FROM paper_authors)
                        ) as shared_author_names,
                        -- Calculate collaboration strength
                        (
                            SELECT AVG(ap.total_papers)
                            FROM unnest(p.author_list) as author_name
                            JOIN author_productivity ap ON ap.author_name = author_name
                            WHERE author_name IN (SELECT author_name FROM paper_authors)
                        ) as avg_author_productivity,
                        -- Check if same cluster (topical similarity)
                        CASE 
                            WHEN p.cluster = (SELECT cluster FROM paper WHERE paper_id = %s) 
                            THEN true 
                            ELSE false 
                        END as same_cluster
                    FROM paper p
                    WHERE p.paper_id != %s
                    AND p.author_list && (SELECT array_agg(author_name) FROM paper_authors)
                )
                SELECT * FROM related_papers
                WHERE shared_authors_count > 0
                ORDER BY 
                    shared_authors_count DESC,
                    same_cluster DESC,
                    citation_count DESC,
                    avg_author_productivity DESC
                LIMIT $4
                """
                
                results = await conn.fetch(query, paper_id, paper_id, paper_id, limit)
                return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting papers by same authors: {e}")
            return []
    
    async def _get_citing_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers that cite this paper using actual citation data"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                query = """
                    SELECT 
                        p.paper_id, 
                        p.title, 
                        p.abstract, 
                        p.author_list,
                        p.cluster,
                        p.cited_by,
                        p.topic,
                        p.score,
                        COALESCE(array_length(p.cited_by, 1), 0) as citation_count,
                        COALESCE(array_length(p.author_list, 1), 0) as author_count,
                        p.created_at,
                        -- Calculate citation context (how this paper cites the center paper)
                        'incoming' as citation_type
                    FROM paper p
                    WHERE $1 = ANY(p.cited_by)
                    AND p.paper_id != $2
                    ORDER BY 
                        COALESCE(array_length(p.cited_by, 1), 0) DESC,  -- More cited papers first
                        p.created_at DESC  -- Recent papers first
                    LIMIT $3
                """
                
                results = await conn.fetch(query, paper_id, paper_id, limit)
                return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting citing papers: {e}")
            return []
    
    async def _get_cited_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers cited by this paper using actual citation data"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                query = """
                    WITH center_paper_refs AS (
                        SELECT unnest(cited_by) as ref_paper_id
                        FROM paper
                        WHERE paper_id = $1
                        AND cited_by IS NOT NULL
                    )
                    SELECT 
                        p.paper_id, 
                        p.title, 
                        p.abstract, 
                        p.author_list,
                        p.cluster,
                        p.topic,
                        p.score,
                        COALESCE(array_length(p.cited_by, 1), 0) as citation_count,
                        COALESCE(array_length(p.author_list, 1), 0) as author_count,
                        p.created_at,
                        'outgoing' as citation_type
                    FROM paper p
                    JOIN center_paper_refs cpr ON p.paper_id = cpr.ref_paper_id
                    WHERE p.paper_id != $2
                    ORDER BY 
                        COALESCE(array_length(p.cited_by, 1), 0) DESC,  -- More cited papers first
                        p.created_at DESC
                    LIMIT $3
                """
                
                results = await conn.fetch(query, paper_id, paper_id, limit)
                return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting cited papers: {e}")
            return []
    
    async def _get_papers_by_key_knowledge(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers related by key knowledge similarity using embeddings"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                query = """
                    WITH center_paper_embedding AS (
                        SELECT AVG(kk.embedding) as avg_embedding
                        FROM key_knowledge kk
                        JOIN paper p ON kk.paper_id = p.id
                        WHERE p.paper_id = $1
                        AND kk.embedding IS NOT NULL
                    ),
                    related_papers AS (
                        SELECT DISTINCT p.paper_id, p.title, p.abstract,
                               AVG(kk.embedding) as paper_avg_embedding,
                               COUNT(kk.context) as knowledge_count
                        FROM paper p
                        JOIN key_knowledge kk ON kk.paper_id = p.id
                        WHERE p.paper_id != $2
                        AND kk.embedding IS NOT NULL
                        GROUP BY p.paper_id, p.title, p.abstract
                        HAVING COUNT(kk.context) > 0
                    ),
                    similarity_papers AS (
                        SELECT rp.*,
                               1 - (rp.paper_avg_embedding <=> cpe.avg_embedding) as similarity_score
                        FROM related_papers rp
                        CROSS JOIN center_paper_embedding cpe
                        WHERE cpe.avg_embedding IS NOT NULL
                    )
                    SELECT * FROM similarity_papers
                    WHERE similarity_score > 0.3  -- Minimum similarity threshold
                    ORDER BY similarity_score DESC
                    LIMIT $3
                """
                
                results = await conn.fetch(query, paper_id, paper_id, limit)
                return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting papers by key knowledge: {e}")
            return []
    
    async def _get_similar_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get similar papers based on embeddings and cluster analysis"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                query = """
                    WITH center_paper AS (
                        SELECT embeddings, cluster, topic
                        FROM paper
                        WHERE paper_id = $1
                        AND embeddings IS NOT NULL
                    ),
                    similar_papers AS (
                        SELECT 
                            p.paper_id, 
                            p.title, 
                            p.abstract,
                            p.cluster,
                            p.topic,
                            p.score,
                            COALESCE(array_length(p.cited_by, 1), 0) as citation_count,
                            COALESCE(array_length(p.author_list, 1), 0) as author_count,
                            p.created_at,
                            -- Calculate embedding similarity if available
                            CASE 
                                WHEN p.embeddings IS NOT NULL AND cp.embeddings IS NOT NULL 
                                THEN 1 - (p.embeddings <=> cp.embeddings)
                                ELSE NULL
                            END as embedding_similarity,
                            -- Check cluster similarity
                            CASE 
                                WHEN p.cluster = cp.cluster AND p.cluster IS NOT NULL
                                THEN true 
                                ELSE false 
                            END as same_cluster,
                            -- Check topic similarity
                            CASE 
                                WHEN p.topic = cp.topic AND p.topic IS NOT NULL
                                THEN true 
                                ELSE false 
                            END as same_topic,
                            -- Calculate coordinate distance if available
                            CASE 
                                WHEN p.plot_visualize_x IS NOT NULL AND p.plot_visualize_y IS NOT NULL 
                                     AND p.plot_visualize_z IS NOT NULL
                                THEN sqrt(
                                    power(p.plot_visualize_x - COALESCE((SELECT plot_visualize_x FROM paper WHERE paper_id = $2), 0), 2) +
                                    power(p.plot_visualize_y - COALESCE((SELECT plot_visualize_y FROM paper WHERE paper_id = $3), 0), 2) +
                                    power(p.plot_visualize_z - COALESCE((SELECT plot_visualize_z FROM paper WHERE paper_id = $4), 0), 2)
                                )
                                ELSE NULL
                            END as spatial_distance
                        FROM paper p
                        CROSS JOIN center_paper cp
                        WHERE p.paper_id != $5
                        AND (
                            p.embeddings IS NOT NULL OR 
                            p.cluster = cp.cluster OR
                            p.topic = cp.topic
                        )
                    ),
                    ranked_similar AS (
                        SELECT *,
                            -- Calculate composite similarity score
                            COALESCE(embedding_similarity, 0) * 0.5 +
                            CASE WHEN same_cluster THEN 0.3 ELSE 0 END +
                            CASE WHEN same_topic THEN 0.2 ELSE 0 END +
                            CASE 
                                WHEN spatial_distance IS NOT NULL 
                                THEN GREATEST(0, (100 - spatial_distance) / 100) * 0.1
                                ELSE 0 
                            END as composite_similarity
                        FROM similar_papers
                    )
                    SELECT *,
                        composite_similarity as similarity_score
                    FROM ranked_similar
                    WHERE composite_similarity > 0.1  -- Minimum similarity threshold
                    ORDER BY 
                        composite_similarity DESC,
                        citation_count DESC,
                        created_at DESC
                    LIMIT $6
                """
                
                results = await conn.fetch(query, paper_id, paper_id, paper_id, paper_id, paper_id, limit)
                return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting similar papers: {e}")
            return []
