"""
Project Database Operations

Handles database operations for projects, analysis cache, and cost tracking.
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import json
from datetime import datetime
import os
import sys

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connect import connect, close_connection

logger = logging.getLogger(__name__)


class ProjectDatabase:
    """Class to handle database operations for the paper analysis pipeline"""
    
    def __init__(self):
        self.conn = None
    
    def get_connection(self):
        """Get database connection"""
        if not self.conn or self.conn.closed:
            self.conn = connect()
        return self.conn
    
    def close_connection(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            close_connection(self.conn)
            self.conn = None
    
    def insert_projects(self, projects: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Insert projects into the database
        
        Args:
            projects: List of project dictionaries
            
        Returns:
            Tuple of (inserted_count, updated_count)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            inserted_count = 0
            updated_count = 0
            
            for project in projects:
                try:
                    # Check if project already exists
                    cursor.execute(
                        "SELECT id FROM projects WHERE project_id = %s",
                        (project['project_id'],)
                    )
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing project
                        self._update_project(cursor, project)
                        updated_count += 1
                    else:
                        # Insert new project
                        self._insert_project(cursor, project)
                        inserted_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing project {project.get('project_id', 'unknown')}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"Successfully processed projects: {inserted_count} inserted, {updated_count} updated")
            
            return inserted_count, updated_count
            
        except Exception as e:
            logger.error(f"Error inserting projects: {e}")
            if self.conn:
                self.conn.rollback()
            return 0, 0
        finally:
            if cursor:
                cursor.close()
    
    def _insert_project(self, cursor, project: Dict[str, Any]):
        """Insert a single project"""
        insert_query = """
            INSERT INTO projects (
                project_id, title, fiscal_year, pi_institution, pi_institution_type,
                project_start_date, project_end_date, solicitation_funding_source,
                research_impact_earth_benefit, abstract, raw_text
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        cursor.execute(insert_query, (
            project['project_id'],
            project['title'],
            project['fiscal_year'],
            project['pi_institution'],
            project['pi_institution_type'],
            project['project_start_date'],
            project['project_end_date'],
            project['solicitation_funding_source'],
            project['research_impact_earth_benefit'],
            project['abstract'],
            project['raw_text']
        ))
    
    def _update_project(self, cursor, project: Dict[str, Any]):
        """Update an existing project"""
        update_query = """
            UPDATE projects SET
                title = %s,
                fiscal_year = %s,
                pi_institution = %s,
                pi_institution_type = %s,
                project_start_date = %s,
                project_end_date = %s,
                solicitation_funding_source = %s,
                research_impact_earth_benefit = %s,
                abstract = %s,
                raw_text = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE project_id = %s
        """
        
        cursor.execute(update_query, (
            project['title'],
            project['fiscal_year'],
            project['pi_institution'],
            project['pi_institution_type'],
            project['project_start_date'],
            project['project_end_date'],
            project['solicitation_funding_source'],
            project['research_impact_earth_benefit'],
            project['abstract'],
            project['raw_text'],
            project['project_id']
        ))
    
    def get_projects_without_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get projects that don't have LLM-generated summaries yet
        
        Args:
            limit: Maximum number of projects to return
            
        Returns:
            List of project dictionaries
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT project_id, title, abstract, raw_text
                FROM projects 
                WHERE summary IS NULL OR summary = '{}'::jsonb
                ORDER BY created_at
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            projects = cursor.fetchall()
            
            return [dict(project) for project in projects]
            
        except Exception as e:
            logger.error(f"Error fetching projects without summaries: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def update_project_summary(self, project_id: str, summary: Dict[str, Any]) -> bool:
        """
        Update project with LLM-generated summary
        
        Args:
            project_id: Project identifier
            summary: Structured summary dictionary
            
        Returns:
            True if successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE projects SET summary = %s WHERE project_id = %s",
                (Json(summary), project_id)
            )
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Updated summary for project {project_id}")
                return True
            else:
                logger.warning(f"No project found with ID {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating project summary: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_projects_without_embeddings(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get projects that don't have embeddings yet
        
        Args:
            limit: Maximum number of projects to return
            
        Returns:
            List of project dictionaries
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT project_id, title, abstract, summary, raw_text
                FROM projects 
                WHERE embedding IS NULL 
                AND summary IS NOT NULL 
                AND summary != '{}'::jsonb
                ORDER BY created_at
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            projects = cursor.fetchall()
            
            return [dict(project) for project in projects]
            
        except Exception as e:
            logger.error(f"Error fetching projects without embeddings: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def update_project_embedding(self, project_id: str, embedding: List[float]) -> bool:
        """
        Update project with embedding vector
        
        Args:
            project_id: Project identifier
            embedding: Vector embedding
            
        Returns:
            True if successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Convert embedding to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            cursor.execute(
                "UPDATE projects SET embedding = %s::vector WHERE project_id = %s",
                (embedding_str, project_id)
            )
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Updated embedding for project {project_id}")
                return True
            else:
                logger.warning(f"No project found with ID {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating project embedding: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def find_similar_projects(self, paper_embedding: List[float], limit: int = 4) -> List[Dict[str, Any]]:
        """
        Find projects most similar to a given paper embedding
        
        Args:
            paper_embedding: Vector embedding of the paper
            limit: Number of similar projects to return
            
        Returns:
            List of similar project dictionaries with similarity scores
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Convert embedding to PostgreSQL vector format properly
            # paper_embedding should be a list of floats
            if isinstance(paper_embedding, str):
                # If it's already a string, clean it up
                embedding_str = paper_embedding.strip('[]').replace(' ', '')
            else:
                # Convert list of floats to proper format
                embedding_str = '[' + ','.join(str(float(x)) for x in paper_embedding) + ']'
            
            logger.info(f"Using embedding format: {embedding_str[:100]}...")  # Log first 100 chars
            
            query = """
                SELECT 
                    project_id,
                    title,
                    fiscal_year,
                    pi_institution,
                    pi_institution_type,
                    project_start_date,
                    project_end_date,
                    solicitation_funding_source,
                    research_impact_earth_benefit,
                    abstract,
                    raw_text,
                    summary,
                    created_at,
                    updated_at,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM projects 
                WHERE embedding IS NOT NULL
                ORDER BY similarity_score DESC
                LIMIT %s
            """
            
            cursor.execute(query, (embedding_str, limit))
            projects = cursor.fetchall()
            
            return [dict(project) for project in projects]
            
        except Exception as e:
            logger.error(f"Error finding similar projects: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def get_cached_analysis(self, paper_text: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result for a paper
        
        Args:
            paper_text: Original paper text
            
        Returns:
            Cached analysis result or None
        """
        try:
            paper_hash = hashlib.sha256(paper_text.encode()).hexdigest()
            
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                """
                SELECT llm_output, top_projects, created_at
                FROM analysis_cache 
                WHERE paper_hash = %s
                """,
                (paper_hash,)
            )
            
            result = cursor.fetchone()
            
            if result:
                # Update cache hit count and last accessed time
                cursor.execute(
                    """
                    UPDATE analysis_cache 
                    SET cache_hit_count = cache_hit_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE paper_hash = %s
                    """,
                    (paper_hash,)
                )
                conn.commit()
                
                logger.info(f"Cache hit for paper hash {paper_hash[:8]}...")
                return dict(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached analysis: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def cache_analysis_result(
        self, 
        paper_text: str, 
        similar_projects: List[Dict[str, Any]], 
        llm_output: Dict[str, Any]
    ) -> bool:
        """
        Cache analysis result for future use
        
        Args:
            paper_text: Original paper text
            similar_projects: List of similar projects found
            llm_output: LLM analysis result
            
        Returns:
            True if successful
        """
        try:
            paper_hash = hashlib.sha256(paper_text.encode()).hexdigest()
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO analysis_cache (paper_hash, paper_summary, top_projects, llm_output)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (paper_hash) DO UPDATE SET
                    paper_summary = EXCLUDED.paper_summary,
                    top_projects = EXCLUDED.top_projects,
                    llm_output = EXCLUDED.llm_output,
                    last_accessed = CURRENT_TIMESTAMP
                """,
                (paper_hash, paper_text[:1000], Json(similar_projects), Json(llm_output))
            )
            
            conn.commit()
            logger.info(f"Cached analysis result for paper hash {paper_hash[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error caching analysis result: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        Get paper details including embedding by paper_id
        
        Args:
            paper_id: Paper ID to search for
            
        Returns:
            Paper dictionary with embedding or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # First try to find in paper table
            cursor.execute(
                """
                SELECT id, title, abstract, author_list, embeddings, summarize
                FROM paper
                WHERE paper_id = %s
                """,
                (paper_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return dict(result)
            
            # If not found, try the projects table (in case paper_id refers to a project)
            cursor.execute(
                """
                SELECT project_id as id, title, summary as abstract, 
                       '' as authors, embedding, summary as summarize
                FROM projects 
                WHERE project_id = %s
                """,
                (paper_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return dict(result)
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting paper by ID {paper_id}: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def log_cost(
        self, 
        operation_type: str, 
        tokens_input: int = 0, 
        tokens_output: int = 0, 
        cost_usd: float = 0.0,
        cache_hit: bool = False,
        top_k_used: int = 0,
        response_time_ms: int = 0,
        paper_id: str = None,
        request_id: str = None
    ) -> bool:
        """
        Log cost and usage information
        
        Args:
            operation_type: Type of operation ('embedding', 'llm_analysis', 'similarity_search')
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            cost_usd: Estimated cost in USD
            cache_hit: Whether this was a cache hit
            top_k_used: Number of similar projects used
            response_time_ms: Response time in milliseconds
            paper_id: Paper ID being analyzed
            request_id: Unique request identifier
            
        Returns:
            True if successful
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO cost_tracker (
                    request_id, paper_id, operation_type, tokens_input, tokens_output,
                    cost_usd, cache_hit, top_k_used, response_time_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request_id, paper_id, operation_type, tokens_input, tokens_output,
                    cost_usd, cache_hit, top_k_used, response_time_ms
                )
            )
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error logging cost: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_project_statistics(self) -> Dict[str, Any]:
        """Get statistics about projects in the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM project_statistics")
            stats = cursor.fetchone()
            
            return dict(stats) if stats else {}
            
        except Exception as e:
            logger.error(f"Error getting project statistics: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()
    
    def get_cost_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get cost summary for the last N days"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    operation_type,
                    SUM(total_requests) as total_requests,
                    SUM(cache_hits) as cache_hits,
                    SUM(total_tokens_input) as total_tokens_input,
                    SUM(total_tokens_output) as total_tokens_output,
                    SUM(total_cost_usd) as total_cost_usd,
                    AVG(avg_response_time_ms) as avg_response_time_ms,
                    AVG(cache_hit_rate_percent) as avg_cache_hit_rate
                FROM daily_cost_summary 
                WHERE date >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY operation_type
                ORDER BY total_cost_usd DESC
            """
            
            cursor.execute(query, (days,))
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return []
        finally:
            if cursor:
                cursor.close()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    db = ProjectDatabase()
    try:
        stats = db.get_project_statistics()
        print("📊 Project Statistics:", stats)
    finally:
        db.close_connection()
