"""
Project Database Operations (Async)

Handles async database operations for projects, analysis cache, and cost tracking.
"""

import asyncpg
import logging
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import json
from datetime import datetime
import os
import sys

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connect import get_db_pool

logger = logging.getLogger(__name__)


class ProjectDatabase:
    """Async class to handle database operations for the paper analysis pipeline"""
    
    def __init__(self):
        """Initialize ProjectDatabase - pool should be initialized separately"""
        pass
    
    async def get_connection(self):
        """Get database connection from pool"""
        pool = await get_db_pool()
        return await pool.acquire()
    
    async def close_connection(self):
        """Close database connection - now handled by pool"""
        pass
    
    async def insert_projects(self, projects: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Insert projects into the database
        
        Args:
            projects: List of project dictionaries
            
        Returns:
            Tuple of (inserted_count, updated_count)
        """
        pool = await get_db_pool()
        
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    inserted_count = 0
                    updated_count = 0
                    
                    for project in projects:
                        try:
                            # Check if project already exists
                            existing = await conn.fetchval(
                                "SELECT id FROM projects WHERE project_id = $1",
                                project['project_id']
                            )
                            
                            if existing:
                                # Update existing project
                                await self._update_project(conn, project)
                                updated_count += 1
                            else:
                                # Insert new project
                                await self._insert_project(conn, project)
                                inserted_count += 1
                                
                        except Exception as e:
                            logger.error(f"Error processing project {project.get('project_id', 'unknown')}: {e}")
                            continue
                    
                    logger.info(f"Successfully processed projects: {inserted_count} inserted, {updated_count} updated")
                    return inserted_count, updated_count
            
        except Exception as e:
            logger.error(f"Error inserting projects: {e}")
            return 0, 0
    
    async def _insert_project(self, conn, project: Dict[str, Any]):
        """Insert a single project"""
        insert_query = """
            INSERT INTO projects (
                project_id, title, fiscal_year, pi_institution, pi_institution_type,
                project_start_date, project_end_date, solicitation_funding_source,
                research_impact_earth_benefit, abstract, raw_text
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
        """
        
        await conn.execute(insert_query,
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
        )
    
    async def _update_project(self, conn, project: Dict[str, Any]):
        """Update an existing project"""
        update_query = """
            UPDATE projects SET
                title = $1,
                fiscal_year = $2,
                pi_institution = $3,
                pi_institution_type = $4,
                project_start_date = $5,
                project_end_date = $6,
                solicitation_funding_source = $7,
                research_impact_earth_benefit = $8,
                abstract = $9,
                raw_text = $10,
                updated_at = CURRENT_TIMESTAMP
            WHERE project_id = $11
        """
        
        await conn.execute(update_query,
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
        )
    
    async def get_projects_without_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get projects that don't have LLM-generated summaries yet
        
        Args:
            limit: Maximum number of projects to return
            
        Returns:
            List of project dictionaries
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                query = """
                    SELECT project_id, title, abstract, raw_text
                    FROM projects 
                    WHERE summary IS NULL OR summary = '{}'::jsonb
                    ORDER BY created_at
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                projects = await conn.fetch(query)
                return [dict(project) for project in projects]
                
        except Exception as e:
            logger.error(f"Error fetching projects without summaries: {e}")
            return []
    
    async def update_project_summary(self, project_id: str, summary: Dict[str, Any]) -> bool:
        """
        Update project with LLM-generated summary
        
        Args:
            project_id: Project identifier
            summary: Structured summary dictionary
            
        Returns:
            True if successful
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE projects SET summary = $1::jsonb WHERE project_id = $2",
                    json.dumps(summary), project_id
                )
                
                # Check if any rows were updated
                rows_updated = int(result.split()[-1]) if result else 0
                
                if rows_updated > 0:
                    logger.info(f"Updated summary for project {project_id}")
                    return True
                else:
                    logger.warning(f"No project found with ID {project_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating project summary: {e}")
            return False
    
    async def get_projects_without_embeddings(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get projects that don't have embeddings yet
        
        Args:
            limit: Maximum number of projects to return
            
        Returns:
            List of project dictionaries
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
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
                
                projects = await conn.fetch(query)
                return [dict(project) for project in projects]
                
        except Exception as e:
            logger.error(f"Error fetching projects without embeddings: {e}")
            return []
    
    async def update_project_embedding(self, project_id: str, embedding: List[float]) -> bool:
        """
        Update project with embedding vector
        
        Args:
            project_id: Project identifier
            embedding: Vector embedding
            
        Returns:
            True if successful
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Convert embedding to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                result = await conn.execute(
                    "UPDATE projects SET embedding = $1::vector WHERE project_id = $2",
                    embedding_str, project_id
                )
                
                rows_updated = int(result.split()[-1]) if result else 0
                
                if rows_updated > 0:
                    logger.info(f"Updated embedding for project {project_id}")
                    return True
                else:
                    logger.warning(f"No project found with ID {project_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating project embedding: {e}")
            return False
    
    async def find_similar_projects(self, paper_embedding: List[float], limit: int = 4) -> List[Dict[str, Any]]:
        """
        Find projects most similar to a given paper embedding
        
        Args:
            paper_embedding: Vector embedding of the paper
            limit: Number of similar projects to return
            
        Returns:
            List of similar project dictionaries with similarity scores
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
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
                        1 - (embedding <=> $1::vector) AS similarity_score
                    FROM projects 
                    WHERE embedding IS NOT NULL
                    ORDER BY similarity_score DESC
                    LIMIT $2
                """
                
                projects = await conn.fetch(query, embedding_str, limit)
                return [dict(project) for project in projects]
                
        except Exception as e:
            logger.error(f"Error finding similar projects: {e}")
            return []
    
    async def get_cached_analysis(self, paper_text: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result for a paper
        
        Args:
            paper_text: Original paper text
            
        Returns:
            Cached analysis result or None
        """
        try:
            paper_hash = hashlib.sha256(paper_text.encode()).hexdigest()
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT llm_output, top_projects, created_at
                    FROM analysis_cache 
                    WHERE paper_hash = $1
                    """,
                    paper_hash
                )
                
                if result:
                    # Update cache hit count and last accessed time
                    await conn.execute(
                        """
                        UPDATE analysis_cache 
                        SET cache_hit_count = cache_hit_count + 1,
                            last_accessed = CURRENT_TIMESTAMP
                        WHERE paper_hash = $1
                        """,
                        paper_hash
                    )
                    
                    logger.info(f"Cache hit for paper hash {paper_hash[:8]}...")
                    return dict(result)
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached analysis: {e}")
            return None
    
    async def cache_analysis_result(
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
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analysis_cache (paper_hash, paper_summary, top_projects, llm_output)
                    VALUES ($1, $2, $3::jsonb, $4::jsonb)
                    ON CONFLICT (paper_hash) DO UPDATE SET
                        paper_summary = EXCLUDED.paper_summary,
                        top_projects = EXCLUDED.top_projects,
                        llm_output = EXCLUDED.llm_output,
                        last_accessed = CURRENT_TIMESTAMP
                    """,
                    paper_hash, paper_text[:1000], 
                    json.dumps(similar_projects), json.dumps(llm_output)
                )
                
                logger.info(f"Cached analysis result for paper hash {paper_hash[:8]}...")
                return True
                
        except Exception as e:
            logger.error(f"Error caching analysis result: {e}")
            return False
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        Get paper details including embedding by paper_id
        
        Args:
            paper_id: Paper ID to search for
            
        Returns:
            Paper dictionary with embedding or None if not found
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # First try to find in paper table
                result = await conn.fetchrow(
                    """
                    SELECT id, title, abstract, author_list, embeddings, summarize
                    FROM paper
                    WHERE paper_id = $1
                    """,
                    paper_id
                )
                
                if result:
                    return dict(result)
                
                # If not found, try the projects table (in case paper_id refers to a project)
                result = await conn.fetchrow(
                    """
                    SELECT project_id as id, title, summary as abstract, 
                           '' as authors, embedding, summary as summarize
                    FROM projects 
                    WHERE project_id = $1
                    """,
                    paper_id
                )
                
                if result:
                    return dict(result)
                    
                return None
                
        except Exception as e:
            logger.error(f"Error getting paper by ID {paper_id}: {e}")
            return None
    
    async def log_cost(
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
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO cost_tracker (
                        request_id, paper_id, operation_type, tokens_input, tokens_output,
                        cost_usd, cache_hit, top_k_used, response_time_ms
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    request_id, paper_id, operation_type, tokens_input, tokens_output,
                    cost_usd, cache_hit, top_k_used, response_time_ms
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error logging cost: {e}")
            return False
    
    async def get_project_statistics(self) -> Dict[str, Any]:
        """Get statistics about projects in the database"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                stats = await conn.fetchrow("SELECT * FROM project_statistics")
                return dict(stats) if stats else {}
                
        except Exception as e:
            logger.error(f"Error getting project statistics: {e}")
            return {}
    
    async def get_cost_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get cost summary for the last N days"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
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
                    WHERE date >= CURRENT_DATE - INTERVAL '$1 days'
                    GROUP BY operation_type
                    ORDER BY total_cost_usd DESC
                """
                
                results = await conn.fetch(query, days)
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return []


if __name__ == "__main__":
    import asyncio
    from database.connect import init_db_pool, close_db_pool
    
    async def main():
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize database pool
        await init_db_pool()
        
        try:
            # Example usage
            db = ProjectDatabase()
            stats = await db.get_project_statistics()
            print("📊 Project Statistics:", stats)
        finally:
            await close_db_pool()
    
    asyncio.run(main())
