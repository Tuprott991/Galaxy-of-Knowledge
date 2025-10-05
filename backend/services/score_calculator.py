"""
Paper Score Calculation and Update Service
"""
import logging
import math
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.connect import connect, close_connection

logger = logging.getLogger(__name__)


class PaperScoreCalculator:
    """
    Calculate and update paper scores based on multiple factors:
    - Citation count (40%) - Impact through citations
    - Reference quality (25%) - Research thoroughness  
    - Recency (20%) - Publication freshness
    - Cluster popularity (15%) - Topic relevance
    """
    
    def __init__(self):
        self.weights = {
            'citations': 0.40,      # Citation impact
            'references': 0.25,     # Research quality
            'recency': 0.20,        # Publication freshness
            'cluster': 0.15         # Topic popularity
        }
    
    def calculate_citation_score(self, citation_count: int) -> float:
        """
        Calculate citation score with improved scaling
        Returns score 0-100
        """
        if citation_count == 0:
            return 0.0
        elif citation_count <= 5:
            # Linear for low citations
            return (citation_count / 5.0) * 30.0
        else:
            # Logarithmic + sqrt for higher citations
            log_score = math.log(citation_count + 1) / math.log(101) * 50.0
            sqrt_score = math.sqrt(citation_count) * 10.0
            return min(log_score + sqrt_score, 100.0)
    
    def calculate_reference_score(self, reference_count: int) -> float:
        """
        Calculate reference quality score
        Returns score 0-100
        """
        if reference_count == 0:
            return 0.0
        else:
            # Good scoring for 10-50 references
            normalized = min(reference_count / 50.0, 1.0)
            return normalized * 100.0
    
    def calculate_recency_score(self, publication_year: Optional[int]) -> float:
        """
        Calculate recency score
        Returns score 0-100
        """
        if not publication_year:
            return 10.0
        
        current_year = 2025
        
        # Validate year
        if publication_year > current_year:
            publication_year = current_year
        elif publication_year < 1950:
            return 5.0
        
        years_old = current_year - publication_year
        
        # Recency scoring
        if years_old <= 0:
            return 100.0
        elif years_old == 1:
            return 90.0
        elif years_old == 2:
            return 80.0
        elif years_old <= 5:
            return 70.0 - (years_old - 3) * 15.0
        else:
            # Exponential decay
            decay_factor = 4.0
            score = math.exp(-years_old / decay_factor) * 100.0
            return max(10.0, score)
    
    def calculate_cluster_score(self, cluster: Optional[str], conn) -> float:
        """
        Calculate cluster popularity score
        Returns score 0-100
        """
        if not cluster:
            return 50.0  # Neutral score
        
        try:
            cursor = conn.cursor()
            
            # Get cluster size
            cursor.execute("""
                SELECT COUNT(*) FROM paper WHERE cluster = %s
            """, (cluster,))
            cluster_size = cursor.fetchone()[0]
            
            # Get total papers
            cursor.execute("SELECT COUNT(*) FROM paper WHERE cluster IS NOT NULL")
            total_papers = cursor.fetchone()[0]
            
            if total_papers == 0:
                return 50.0
            
            # Cluster popularity (normalized to 0-100)
            popularity = (cluster_size / total_papers) * 100.0
            
            # Score based on cluster size (not too small, not too large)
            if cluster_size < 5:
                return 20.0  # Too small cluster
            elif cluster_size > total_papers * 0.3:
                return 70.0  # Very large cluster
            else:
                return min(50.0 + popularity * 2, 100.0)
                
        except Exception as e:
            logger.warning(f"Error calculating cluster score: {e}")
            return 50.0
    
    def calculate_paper_score(self, paper_data: Dict[str, Any]) -> float:
        """
        Calculate final paper score using weighted components
        """
        try:
            conn = connect()
            
            # Get paper metadata
            citation_count = paper_data.get('citation_count', 0)
            reference_count = paper_data.get('reference_count', 0)
            publication_year = paper_data.get('publication_year')
            cluster = paper_data.get('cluster')
            
            # Calculate component scores
            citation_score = self.calculate_citation_score(citation_count)
            reference_score = self.calculate_reference_score(reference_count)
            recency_score = self.calculate_recency_score(publication_year)
            cluster_score = self.calculate_cluster_score(cluster, conn)
            
            # Calculate weighted final score
            final_score = (
                citation_score * self.weights['citations'] +
                reference_score * self.weights['references'] +
                recency_score * self.weights['recency'] +
                cluster_score * self.weights['cluster']
            )
            
            close_connection(conn)
            
            return round(final_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating paper score: {e}")
            return 0.0
    
    def update_paper_score(self, paper_id: str, score: float) -> bool:
        """
        Update paper score in database
        """
        try:
            conn = connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE paper 
                SET score = %s, updated_at = CURRENT_TIMESTAMP
                WHERE paper_id = %s
            """, (score, paper_id))
            
            conn.commit()
            close_connection(conn)
            
            logger.info(f"✅ Updated score for paper {paper_id}: {score}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating score for paper {paper_id}: {e}")
            return False
    
    def calculate_and_update_single_paper(self, paper_id: str) -> Dict[str, Any]:
        """
        Calculate and update score for a single paper
        """
        try:
            conn = connect()
            cursor = conn.cursor()
            
            # Get paper data
            cursor.execute("""
                SELECT 
                    paper_id,
                    COALESCE(array_length(cited_by, 1), 0) as citation_count,
                    COALESCE(array_length(_references, 1), 0) as reference_count,
                    cluster,
                    COALESCE(
                        CASE 
                            WHEN json_data->>'published_date' ~ '^[0-9]{4}' 
                            THEN substring(json_data->>'published_date' from '^([0-9]{4})')::int
                        END,
                        CASE 
                            WHEN json_data->>'year' ~ '^[0-9]{4}$' 
                            THEN (json_data->>'year')::int
                        END,
                        LEAST(EXTRACT(YEAR FROM created_at)::int, 2025)
                    ) as publication_year
                FROM paper 
                WHERE paper_id = %s
            """, (paper_id,))
            
            result = cursor.fetchone()
            close_connection(conn)
            
            if not result:
                return {"success": False, "error": "Paper not found"}
            
            # Prepare paper data
            paper_data = {
                'paper_id': result[0],
                'citation_count': result[1],
                'reference_count': result[2],
                'cluster': result[3],
                'publication_year': result[4]
            }
            
            # Calculate score
            score = self.calculate_paper_score(paper_data)
            
            # Update database
            success = self.update_paper_score(paper_id, score)
            
            if success:
                return {
                    "success": True,
                    "paper_id": paper_id,
                    "score": score,
                    "components": {
                        "citation_score": self.calculate_citation_score(paper_data['citation_count']),
                        "reference_score": self.calculate_reference_score(paper_data['reference_count']),
                        "recency_score": self.calculate_recency_score(paper_data['publication_year']),
                        "cluster_score": self.calculate_cluster_score(paper_data['cluster'], connect())
                    },
                    "metadata": paper_data
                }
            else:
                return {"success": False, "error": "Failed to update score"}
                
        except Exception as e:
            logger.error(f"Error calculating score for paper {paper_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def batch_calculate_scores(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate and update scores for multiple papers
        Optimized with single database connection for batch processing
        """
        try:
            conn = connect()
            cursor = conn.cursor()
            
            # Get papers that need score calculation
            query = """
                SELECT 
                    paper_id,
                    COALESCE(array_length(cited_by, 1), 0) as citation_count,
                    COALESCE(array_length(_references, 1), 0) as reference_count,
                    cluster,
                    COALESCE(
                        CASE 
                            WHEN json_data->>'published_date' ~ '^[0-9]{4}' 
                            THEN substring(json_data->>'published_date' from '^([0-9]{4})')::int
                        END,
                        CASE 
                            WHEN json_data->>'year' ~ '^[0-9]{4}$' 
                            THEN (json_data->>'year')::int
                        END,
                        LEAST(EXTRACT(YEAR FROM created_at)::int, 2025)
                    ) as publication_year
                FROM paper 
                WHERE title IS NOT NULL
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            papers = cursor.fetchall()
            
            successful = 0
            failed = 0
            results = []
            
            # Batch update preparation
            update_data = []
            
            for paper in papers:
                paper_data = {
                    'paper_id': paper[0],
                    'citation_count': paper[1],
                    'reference_count': paper[2],
                    'cluster': paper[3],
                    'publication_year': paper[4]
                }
                
                try:
                    # Calculate score
                    score = self.calculate_paper_score(paper_data)
                    
                    # Prepare for batch update
                    update_data.append((score, paper[0]))
                    results.append({
                        "paper_id": paper[0],
                        "score": score
                    })
                    
                except Exception as e:
                    logger.error(f"Error calculating score for paper {paper[0]}: {e}")
                    failed += 1
            
            # Batch update all scores at once
            if update_data:
                try:
                    cursor.executemany(
                        "UPDATE paper SET score = %s, updated_at = NOW() WHERE paper_id = %s",
                        update_data
                    )
                    conn.commit()
                    successful = len(update_data)
                    
                    # Log successful updates
                    for score, paper_id in update_data[:10]:  # Log first 10
                        logger.info(f"✅ Updated score for paper {paper_id}: {score}")
                    
                    if len(update_data) > 10:
                        logger.info(f"✅ Successfully updated {len(update_data)} papers in batch")
                        
                except Exception as e:
                    logger.error(f"Error in batch update: {e}")
                    conn.rollback()
                    failed = len(update_data)
                    successful = 0
            
            close_connection(conn)
            
            return {
                "success": True,
                "total_processed": len(papers),
                "successful": successful,
                "failed": failed,
                "results": results[:10]  # Return first 10 results
            }
            
        except Exception as e:
            logger.error(f"Error in batch calculation: {e}")
            return {"success": False, "error": str(e)}


# Global instance
_score_calculator = None

def get_score_calculator() -> PaperScoreCalculator:
    """Get or create global score calculator instance"""
    global _score_calculator
    if _score_calculator is None:
        _score_calculator = PaperScoreCalculator()
    return _score_calculator
