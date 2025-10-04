"""
Graph service for generating 2D network visualization data
"""

import asyncio
from typing import List, Dict, Set, Tuple, Optional, Any
from psycopg2.extras import RealDictCursor

from ..models.graph import Node, Edge, GraphData
from database.connect import connect


class GraphService:
    """Service for generating graph data for 2D visualization"""
    
    def __init__(self):
        pass
    
    def get_db_connection(self):
        """Create database connection"""
        return connect()
    
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
        
        # Add center paper
        center_paper = await self._get_paper_info(paper_id)
        if not center_paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        nodes[paper_id] = Node(
            id=paper_id,
            label=center_paper['title'][:50] + "..." if len(center_paper['title']) > 50 else center_paper['title'],
            level=0,
            size=20,
            color="#e74c3c",  # Red for center
            metadata=center_paper
        )
        visited_papers.add(paper_id)
        
        # Level 1: Papers by same authors
        level1_papers = await self._get_papers_by_same_authors(paper_id, max_nodes // 2)
        for paper in level1_papers:
            if paper['paper_id'] not in visited_papers and len(nodes) < max_nodes:
                nodes[paper['paper_id']] = Node(
                    id=paper['paper_id'],
                    label=paper['title'][:40] + "..." if len(paper['title']) > 40 else paper['title'],
                    level=1,
                    size=15,
                    color="#3498db",  # Blue for level 1
                    metadata=paper
                )
                visited_papers.add(paper['paper_id'])
                
                # Add edge
                shared_authors_names = paper.get('shared_author_names', [])
                author_names_str = ", ".join(shared_authors_names[:3])  # Lấy tối đa 3 tên đầu
                if len(shared_authors_names) > 3:
                    author_names_str += f" và {len(shared_authors_names) - 3} tác giả khác"
                
                edges.append(Edge(
                    source=paper_id,
                    target=paper['paper_id'],
                    type="author",
                    label="same author",
                    color="#f39c12",
                    relation=f"{author_names_str} co-authored this paper",
                    metadata={
                        "shared_authors_count": paper.get('shared_authors_count', 1),
                        "shared_author_names": shared_authors_names,
                        "level": 1,
                        "relationship_strength": "strong" if paper.get('shared_authors_count', 1) > 2 else "medium"
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
                        author_names_str = ", ".join(shared_authors_names[:2])  # Level 2 chỉ lấy 2 tên
                        if len(shared_authors_names) > 2:
                            author_names_str += f" và {len(shared_authors_names) - 2} tác giả khác"
                        
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
                        "paper_year": paper.get('published_date', '').split('-')[0] if paper.get('published_date') else None,
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
                        "paper_year": paper.get('published_date', '').split('-')[0] if paper.get('published_date') else None,
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
                        "confidence_score": paper.get('avg_confidence', 0.5),
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
                                "confidence_score": paper.get('avg_confidence', 0.3),
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
        """Get basic paper information"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT p.paper_id, p.title, p.abstract, p.published_date, p.doi,
                       array_agg(DISTINCT a.name) as authors
                FROM paper p
                LEFT JOIN authors a ON p.paper_id = a.paper_id
                WHERE p.paper_id = %s
                GROUP BY p.paper_id, p.title, p.abstract, p.published_date, p.doi
            """
            
            cursor.execute(query, (paper_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            print(f"Error getting paper info: {e}")
            return None
    
    async def _get_papers_by_same_authors(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers by same authors"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                WITH paper_authors AS (
                    SELECT DISTINCT a.name
                    FROM authors a
                    WHERE a.paper_id = %s
                ),
                related_papers AS (
                    SELECT DISTINCT p.paper_id, p.title, p.abstract, p.published_date,
                           COUNT(DISTINCT a.name) as shared_authors_count,
                           array_agg(DISTINCT a.name) as shared_author_names
                    FROM paper p
                    JOIN authors a ON p.paper_id = a.paper_id
                    JOIN paper_authors pa ON a.name = pa.name
                    WHERE p.paper_id != %s
                    GROUP BY p.paper_id, p.title, p.abstract, p.published_date
                    HAVING COUNT(DISTINCT a.name) > 0
                )
                SELECT * FROM related_papers
                ORDER BY shared_authors_count DESC
                LIMIT %s
            """
            
            cursor.execute(query, (paper_id, paper_id, limit))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting papers by same authors: {e}")
            return []
    
    async def _get_citing_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers that cite this paper"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # For now, we'll use a simple query. This can be enhanced with actual citation data
            query = """
                SELECT p.paper_id, p.title, p.abstract, p.published_date
                FROM paper p
                WHERE p.paper_id != %s
                ORDER BY RANDOM()
                LIMIT %s
            """
            
            cursor.execute(query, (paper_id, limit))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting citing papers: {e}")
            return []
    
    async def _get_cited_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers cited by this paper"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # For now, we'll use a simple query. This can be enhanced with actual citation data
            query = """
                SELECT p.paper_id, p.title, p.abstract, p.published_date
                FROM paper p
                WHERE p.paper_id != %s
                ORDER BY RANDOM()
                LIMIT %s
            """
            
            cursor.execute(query, (paper_id, limit))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting cited papers: {e}")
            return []
    
    async def _get_papers_by_key_knowledge(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get papers related by key knowledge similarity using embeddings"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                WITH center_paper_embedding AS (
                    SELECT AVG(kk.embedding) as avg_embedding
                    FROM key_knowledge kk
                    WHERE kk.paper_id = %s
                    AND kk.embedding IS NOT NULL
                ),
                related_papers AS (
                    SELECT DISTINCT p.paper_id, p.title, p.abstract, p.published_date,
                           AVG(kk.embedding) as paper_avg_embedding,
                           COUNT(kk.knowledge_text) as knowledge_count,
                           AVG(kk.confidence_score) as avg_confidence
                    FROM paper p
                    JOIN key_knowledge kk ON p.paper_id = kk.paper_id
                    WHERE p.paper_id != %s
                    AND kk.embedding IS NOT NULL
                    GROUP BY p.paper_id, p.title, p.abstract, p.published_date
                    HAVING COUNT(kk.knowledge_text) > 0
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
                LIMIT %s
            """
            
            cursor.execute(query, (paper_id, paper_id, limit))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting papers by key knowledge: {e}")
            return []
    
    async def _get_similar_papers(self, paper_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get similar papers based on embeddings or other similarity metrics"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get papers from the same cluster as a proxy for similarity
            query = """
                WITH paper_cluster AS (
                    SELECT cluster
                    FROM paper
                    WHERE paper_id = %s
                ),
                similar_papers AS (
                    SELECT p.paper_id, p.title, p.abstract, p.published_date,
                           RANDOM() as similarity_score  -- Placeholder for actual similarity calculation
                    FROM paper p
                    CROSS JOIN paper_cluster pc
                    WHERE p.cluster = pc.cluster
                    AND p.paper_id != %s
                    AND p.cluster IS NOT NULL
                )
                SELECT * FROM similar_papers
                ORDER BY similarity_score DESC
                LIMIT %s
            """
            
            cursor.execute(query, (paper_id, paper_id, limit))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Error getting similar papers: {e}")
            return []
