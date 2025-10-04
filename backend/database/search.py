"""
Semantic Search Module
This module provides functionality to search papers using vector embeddings
and return the most relevant papers based on cosine similarity.
"""

import sys
import os
import logging
from typing import List, Dict, Any, Optional, Tuple

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connect import connect
from utils.embedding_provider import get_embedding_model

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaperSearch:
    """
    Class to handle semantic search over papers using embeddings
    """
    
    def __init__(self):
        """Initialize the paper search service"""
        self.conn = None
        self.embedding_model = None
    
    def initialize(self):
        """Initialize database connection and embedding model"""
        try:
            # Connect to database
            self.conn = connect()
            logger.info("Database connection established")
            
            # Initialize embedding model
            self.embedding_model = get_embedding_model()
            logger.info("Embedding model initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for search query
        
        Args:
            query: Search query string
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            embeddings = self.embedding_model.get_embeddings([query])
            embedding_vector = embeddings[0].values
            return embedding_vector
            
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise
    
    def search_papers_by_embedding(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        distance_threshold: Optional[float] = None,
        cluster: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search papers by embedding vector using cosine similarity
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            distance_threshold: Optional maximum distance threshold (papers further than this won't be returned)
            cluster: Optional cluster filter to search within specific cluster
            
        Returns:
            List of paper dictionaries with relevance scores
        """
        try:
            cursor = self.conn.cursor()
            
            # Convert embedding to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Build query with optional filters
            query = """
                SELECT 
                    id,
                    paper_id,
                    title,
                    abstract,
                    author_list,
                    cluster,
                    json_data,
                    plot_visualize_x,
                    plot_visualize_y,
                    plot_visualize_z,
                    embeddings <=> %s::vector AS distance,
                    1 - (embeddings <=> %s::vector) AS similarity_score
                FROM paper
                WHERE embeddings IS NOT NULL
            """
            
            params = [embedding_str, embedding_str]
            
            # Add cluster filter if specified
            if cluster:
                query += " AND cluster = %s"
                params.append(cluster)
            
            # Add distance threshold if specified
            if distance_threshold is not None:
                query += " AND (embeddings <=> %s::vector) <= %s"
                params.extend([embedding_str, distance_threshold])
            
            query += """
                ORDER BY distance ASC
                LIMIT %s
            """
            params.append(top_k)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            papers = []
            for row in results:
                paper = {
                    'id': row[0],
                    'paper_id': row[1],
                    'title': row[2],
                    'abstract': row[3],
                    'authors': row[4],
                    'cluster': row[5],
                    'metadata': row[6],
                    'plot_coordinates': {
                        'x': row[7],
                        'y': row[8],
                        'z': row[9]
                    } if row[7] is not None else None,
                    'distance': float(row[10]),
                    'similarity_score': float(row[11])
                }
                papers.append(paper)
            
            cursor.close()
            logger.info(f"Found {len(papers)} papers matching the query")
            return papers
            
        except Exception as e:
            logger.error(f"Error searching papers: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        top_k: int = 10,
        distance_threshold: Optional[float] = None,
        cluster: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        High-level search function that takes a text query and returns relevant papers
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            distance_threshold: Optional maximum distance threshold
            cluster: Optional cluster filter
            
        Returns:
            List of paper dictionaries with relevance scores
        """
        logger.info(f"Searching for: '{query}' (top_k={top_k})")
        
        # Generate embedding for query
        query_embedding = self.generate_query_embedding(query)
        
        # Search papers
        results = self.search_papers_by_embedding(
            query_embedding, 
            top_k=top_k,
            distance_threshold=distance_threshold,
            cluster=cluster
        )
        
        return results
    
    def search_similar_papers(
        self, 
        paper_id: str, 
        top_k: int = 10,
        exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find papers similar to a given paper
        
        Args:
            paper_id: ID of the reference paper
            top_k: Number of similar papers to return
            exclude_self: Whether to exclude the reference paper from results
            
        Returns:
            List of similar paper dictionaries
        """
        try:
            cursor = self.conn.cursor()
            
            # Get embedding of the reference paper
            cursor.execute(
                "SELECT embeddings FROM paper WHERE paper_id = %s AND embeddings IS NOT NULL",
                (paper_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                logger.warning(f"Paper {paper_id} not found or has no embedding")
                return []
            
            # Extract embedding
            reference_embedding = result[0]
            
            # Build query
            query = """
                SELECT 
                    id,
                    paper_id,
                    title,
                    abstract,
                    author_list,
                    cluster,
                    json_data,
                    plot_visualize_x,
                    plot_visualize_y,
                    plot_visualize_z,
                    embeddings <=> %s AS distance,
                    1 - (embeddings <=> %s) AS similarity_score
                FROM paper
                WHERE embeddings IS NOT NULL
            """
            
            params = [reference_embedding, reference_embedding]
            
            # Exclude the reference paper itself
            if exclude_self:
                query += " AND paper_id != %s"
                params.append(paper_id)
            
            query += """
                ORDER BY distance ASC
                LIMIT %s
            """
            params.append(top_k)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            papers = []
            for row in results:
                paper = {
                    'id': row[0],
                    'paper_id': row[1],
                    'title': row[2],
                    'abstract': row[3],
                    'authors': row[4],
                    'cluster': row[5],
                    'metadata': row[6],
                    'plot_coordinates': {
                        'x': row[7],
                        'y': row[8],
                        'z': row[9]
                    } if row[7] is not None else None,
                    'distance': float(row[10]),
                    'similarity_score': float(row[11])
                }
                papers.append(paper)
            
            cursor.close()
            logger.info(f"Found {len(papers)} papers similar to {paper_id}")
            return papers
            
        except Exception as e:
            logger.error(f"Error finding similar papers: {e}")
            raise
    
    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform batch search for multiple queries
        
        Args:
            queries: List of search query strings
            top_k: Number of results per query
            
        Returns:
            Dictionary mapping queries to their results
        """
        results = {}
        
        for query in queries:
            try:
                results[query] = self.search(query, top_k=top_k)
            except Exception as e:
                logger.error(f"Error searching for '{query}': {e}")
                results[query] = []
        
        return results
    
    def get_papers_by_cluster(self, cluster: str) -> List[Dict[str, Any]]:
        """
        Get all papers in a specific cluster
        
        Args:
            cluster: Cluster identifier
            
        Returns:
            List of papers in the cluster
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
                SELECT 
                    id,
                    paper_id,
                    title,
                    abstract,
                    author_list,
                    cluster,
                    plot_visualize_x,
                    plot_visualize_y,
                    plot_visualize_z
                FROM paper
                WHERE cluster = %s
                ORDER BY id
            """
            
            cursor.execute(query, (cluster,))
            results = cursor.fetchall()
            
            papers = []
            for row in results:
                paper = {
                    'id': row[0],
                    'paper_id': row[1],
                    'title': row[2],
                    'abstract': row[3],
                    'authors': row[4],
                    'cluster': row[5],
                    'plot_coordinates': {
                        'x': row[6],
                        'y': row[7],
                        'z': row[8]
                    } if row[6] is not None else None
                }
                papers.append(paper)
            
            cursor.close()
            logger.info(f"Found {len(papers)} papers in cluster {cluster}")
            return papers
            
        except Exception as e:
            logger.error(f"Error getting papers by cluster: {e}")
            raise
