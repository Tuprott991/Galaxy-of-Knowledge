"""
Paper Recommendation Service
Implements hybrid multi-signal recommendation system
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import math
import time
from datetime import datetime

from database.connect import connect, close_connection
from database.search import PaperSearch
from utils.embedding_provider import get_embedding_model

logger = logging.getLogger(__name__)


class PaperRecommendationEngine:
    """
    Hybrid recommendation engine combining multiple signals:
    1. Semantic similarity (40%) - Content relevance
    2. Citation authority (30%) - Quality and impact  
    3. Publication recency (20%) - Temporal relevance
    4. Topic diversity (10%) - Exploration bonus
    """
    
    def __init__(self):
        self.weights = {
            'semantic': 0.4,      # Content relevance
            'authority': 0.3,     # Citation-based quality
            'recency': 0.2,       # Publication freshness
            'diversity': 0.1      # Topic exploration
        }
        
        # Context-specific weight adjustments
        self.context_weights = {
            'literature_review': {
                'semantic': 0.35,
                'authority': 0.40,    # Emphasize high-impact papers
                'recency': 0.15,
                'diversity': 0.10
            },
            'recent_research': {
                'semantic': 0.30,
                'authority': 0.20,
                'recency': 0.40,      # Emphasize recent papers
                'diversity': 0.10
            },
            'methodology': {
                'semantic': 0.45,     # Focus on content match
                'authority': 0.25,
                'recency': 0.15,
                'diversity': 0.15
            }
        }
        
        self.search_engine = None
        self.embedding_model = None
        
    def initialize(self):
        """Initialize search engine and embedding model"""
        try:
            self.search_engine = PaperSearch()
            self.search_engine.initialize()
            self.embedding_model = get_embedding_model()
            logger.info("✅ Recommendation engine initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize recommendation engine: {e}")
            raise
    
    def close(self):
        """Close connections"""
        if self.search_engine:
            self.search_engine.close()
    
    def _preprocess_query(self, query: str) -> str:
        """
        Enhance query for better semantic matching
        """
        query = query.lower().strip()
        
        # Expand common ML terms
        ml_expansions = {
            'machine learning': 'machine learning artificial intelligence ML AI neural networks deep learning',
            'ml': 'machine learning artificial intelligence neural networks deep learning',
            'ai': 'artificial intelligence machine learning neural networks deep learning',
            'neural network': 'neural networks deep learning machine learning artificial intelligence',
            'deep learning': 'deep learning neural networks machine learning artificial intelligence',
            'data science': 'data science machine learning statistics analytics artificial intelligence',
            'nlp': 'natural language processing NLP text mining machine learning',
            'computer vision': 'computer vision image processing machine learning deep learning',
            'reinforcement learning': 'reinforcement learning machine learning AI artificial intelligence'
        }
        
        for term, expansion in ml_expansions.items():
            if term in query:
                query = query.replace(term, expansion)
        
        return query
    
    def _boost_semantic_score(self, base_score: float, query: str, title: str, abstract: str) -> float:
        """
        Boost semantic score based on keyword matching
        """
        try:
            query_terms = set(query.lower().split())
            title_terms = set(title.lower().split()) if title else set()
            abstract_terms = set(abstract.lower().split()) if abstract else set()
            
            # Calculate term overlap
            title_overlap = len(query_terms.intersection(title_terms)) / max(len(query_terms), 1)
            abstract_overlap = len(query_terms.intersection(abstract_terms)) / max(len(query_terms), 1)
            
            # Apply boosts
            keyword_boost = (title_overlap * 0.3) + (abstract_overlap * 0.2)
            final_score = base_score + keyword_boost
            
            return min(final_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.warning(f"Error boosting semantic score: {e}")
            return base_score
        """Adjust scoring weights based on context"""
        if context in self.context_weights:
            return self.context_weights[context]
        return self.weights
    
    def _calculate_semantic_score(
        self, 
        query_embedding: List[float], 
        paper_embedding: List[float]
    ) -> float:
        """
        Calculate semantic similarity using cosine similarity
        Returns score between 0-1 where 1 = perfect match
        """
        try:
            # Cosine similarity = 1 - cosine_distance
            # Database returns cosine_distance, so we convert
            dot_product = sum(a * b for a, b in zip(query_embedding, paper_embedding))
            norm_a = math.sqrt(sum(a * a for a in query_embedding))
            norm_b = math.sqrt(sum(b * b for b in paper_embedding))
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
                
            cosine_similarity = dot_product / (norm_a * norm_b)
            return max(0.0, min(1.0, cosine_similarity))  # Clamp to [0,1]
            
        except Exception as e:
            logger.warning(f"Error calculating semantic score: {e}")
            return 0.0
    
    def _calculate_authority_score(
        self, 
        citation_count: int, 
        reference_count: int,
        paper_score: float,
        cluster_size: int = 1
    ) -> float:
        """
        Calculate authority score based on:
        - Citation count (60%) - How often cited (improved scaling)
        - Reference quality (25%) - How well researched  
        - Existing paper score (15%) - Pre-computed authority
        
        Returns normalized score 0-1
        """
        try:
            # Citation component (60%) - improved scaling with sqrt + log
            if citation_count == 0:
                citation_component = 0.0
            elif citation_count <= 5:
                # Linear scaling for low citations to give them fair chance
                citation_component = (citation_count / 5.0) * 0.3
            else:
                # Logarithmic + sqrt scaling for higher citations
                log_citations = math.log(citation_count + 1) / math.log(101)  # Base scaling
                sqrt_citations = math.sqrt(citation_count) / 10.0  # Additional boost
                citation_component = min((log_citations + sqrt_citations) * 0.6, 0.6)
            
            # Reference quality component (25%) - enhanced scoring
            if reference_count == 0:
                ref_component = 0.0
            else:
                # Better scaling: papers with 10-30 refs get good scores
                ref_normalized = min(reference_count / 30.0, 1.0)  # Cap at 30 references
                ref_component = ref_normalized * 0.25
            
            # Existing authority score (15%) - reduced weight since many papers have score=0
            authority_component = min(paper_score / 100.0, 1.0) * 0.15
            
            total_score = citation_component + ref_component + authority_component
            
            # Boost for papers with some authority signals
            if citation_count >= 3 or reference_count >= 10:
                total_score = min(total_score * 1.2, 1.0)  # 20% boost, cap at 1.0
            
            return max(0.0, min(1.0, total_score))
            
        except Exception as e:
            logger.warning(f"Error calculating authority score: {e}")
            return 0.0
    
    def _calculate_recency_score(self, publication_year: Optional[int]) -> float:
        """
        Calculate recency score with exponential decay
        Recent papers get higher scores, with half-life of 3 years
        
        Returns score 0-1 where 1 = very recent
        """
        try:
            if not publication_year:
                return 0.1  # Low score for unknown publication year
            
            current_year = 2025  # Fixed current year
            
            # Validate publication year (reasonable range)
            if publication_year > current_year:
                logger.warning(f"Future publication year detected: {publication_year}, capping at {current_year}")
                publication_year = current_year
            elif publication_year < 1950:
                logger.warning(f"Very old publication year: {publication_year}, setting low recency")
                return 0.05
                
            years_old = current_year - publication_year
            
            # Improved recency scoring
            if years_old <= 0:  # Current year
                return 1.0
            elif years_old == 1:  # Last year
                return 0.9
            elif years_old == 2:  # 2 years ago
                return 0.8
            elif years_old <= 5:  # 3-5 years ago
                return 0.7 - (years_old - 3) * 0.15  # Gradual decay
            else:
                # Exponential decay with half-life of 4 years for older papers
                decay_factor = 4.0
                recency_score = math.exp(-years_old / decay_factor)
                return max(0.1, recency_score)  # Minimum 0.1 for very old papers
            
        except Exception as e:
            logger.warning(f"Error calculating recency score: {e}")
            return 0.1
    
    def _calculate_diversity_score(
        self, 
        paper_cluster: Optional[str],
        user_clusters: List[str],
        paper_topic: Optional[str] = None
    ) -> float:
        """
        Calculate diversity bonus to encourage exploration
        - Bonus for papers in new clusters
        - Penalty for over-representation of same cluster
        
        Returns score 0-1
        """
        try:
            if not paper_cluster:
                return 0.05  # Small neutral score
            
            if not user_clusters:
                return 0.1   # Small exploration bonus for new users
            
            # Diversity bonus for exploring new clusters
            if paper_cluster not in user_clusters:
                return 0.15  # Exploration bonus
            else:
                # Check cluster frequency to avoid over-representation
                cluster_frequency = user_clusters.count(paper_cluster) / len(user_clusters)
                if cluster_frequency > 0.5:  # Over 50% from same cluster
                    return 0.05  # Penalty for over-concentration
                else:
                    return 0.1   # Normal score for familiar clusters
                    
        except Exception as e:
            logger.warning(f"Error calculating diversity score: {e}")
            return 0.05
    
    def _get_recommendation_reason(
        self, 
        semantic_score: float,
        authority_score: float, 
        recency_score: float,
        diversity_score: float,
        context: str
    ) -> str:
        """Generate human-readable reason for recommendation"""
        
        reasons = []
        
        # Primary reason (highest score)
        scores = {
            'semantic': semantic_score,
            'authority': authority_score,
            'recency': recency_score,
            'diversity': diversity_score
        }
        
        max_component = max(scores, key=scores.get)
        max_score = scores[max_component]
        
        if max_component == 'semantic' and semantic_score > 0.7:
            reasons.append("High content relevance to your query")
        elif max_component == 'authority' and authority_score > 0.6:
            reasons.append("Highly cited and influential paper")
        elif max_component == 'recency' and recency_score > 0.6:
            reasons.append("Recent publication with current insights")
        elif max_component == 'diversity':
            reasons.append("Explores related research areas")
        
        # Secondary reasons
        if authority_score > 0.5 and max_component != 'authority':
            reasons.append("well-established research")
        if recency_score > 0.5 and max_component != 'recency':
            reasons.append("recent findings")
        if semantic_score > 0.6 and max_component != 'semantic':
            reasons.append("strong content match")
            
        # Context-specific reasons
        if context == 'literature_review' and authority_score > 0.6:
            reasons.append("essential for literature review")
        elif context == 'recent_research' and recency_score > 0.7:
            reasons.append("cutting-edge research")
        
        return "; ".join(reasons) if reasons else "Relevant to your research interests"
    
    def recommend_papers(
        self,
        query: str,
        limit: int = 10,
        context: str = "general",
        user_clusters: List[str] = None,
        exclude_papers: List[str] = None,
        min_score: float = 0.0
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Main recommendation function
        
        Returns:
            Tuple of (recommendations_list, statistics_dict)
        """
        start_time = time.time()
        
        if user_clusters is None:
            user_clusters = []
        if exclude_papers is None:
            exclude_papers = []
            
        # Adjust weights based on context
        current_weights = self._adjust_weights_for_context(context)
        
        try:
            # Step 0: Preprocess query for better matching
            enhanced_query = self._preprocess_query(query)
            logger.info(f"Enhanced query: '{enhanced_query}' from original: '{query}'")
            
            # Step 1: Get semantic candidates (broader search)
            semantic_candidates = self.search_engine.search(
                enhanced_query, 
                top_k=min(limit * 8, 150),  # Get more candidates for better filtering
                distance_threshold=0.7      # More lenient threshold for ML queries
            )
            
            logger.info(f"Found {len(semantic_candidates)} semantic candidates")
            
            if not semantic_candidates:
                return [], {"error": "No semantic matches found"}
            
            # Step 2: Score each candidate with batch processing
            conn = connect()
            cursor = conn.cursor()
            
            # Batch query for better performance
            paper_ids = [candidate['paper_id'] for candidate in semantic_candidates[:limit*3]]  # Limit candidates for performance
            
            if not paper_ids:
                return [], {"error": "No valid paper IDs found"}
            
            # Single batch query instead of individual queries
            placeholders = ','.join(['%s'] * len(paper_ids))
            batch_query = f"""
                SELECT 
                    paper_id, title, abstract, author_list,
                    COALESCE(array_length(cited_by, 1), 0) as citation_count,
                    COALESCE(array_length(_references, 1), 0) as reference_count,
                    COALESCE(score, 0) as paper_score,
                    cluster, topic,
                    -- Better year extraction with multiple fallbacks
                    COALESCE(
                        -- Try published_date field first (format: "2014 Aug 18")
                        CASE 
                            WHEN json_data->>'published_date' ~ '^[0-9]{{4}}' 
                            THEN substring(json_data->>'published_date' from '^([0-9]{{4}})')::int
                        END,
                        -- Try year field
                        CASE 
                            WHEN json_data->>'year' ~ '^[0-9]{{4}}$' 
                            THEN (json_data->>'year')::int
                        END,
                        -- Try publication_date field
                        CASE 
                            WHEN json_data->>'publication_date' ~ '[0-9]{{4}}' 
                            THEN substring(json_data->>'publication_date' from '[0-9]{{4}}')::int
                        END,
                        -- Fallback to created_at but cap at current year
                        LEAST(EXTRACT(YEAR FROM created_at)::int, 2025)
                    ) as publication_year
                FROM paper 
                WHERE paper_id IN ({placeholders})
            """
            
            cursor.execute(batch_query, paper_ids)
            paper_results = cursor.fetchall()
            
            # Create lookup dict for O(1) access
            paper_data_dict = {row[0]: row for row in paper_results}
            
            recommendations = []
            
            for candidate in semantic_candidates:
                paper_id = candidate['paper_id']
                
                # Skip excluded papers
                if paper_id in exclude_papers:
                    continue
                
                # Get paper data from batch results
                paper_data = paper_data_dict.get(paper_id)
                if not paper_data:
                    continue
                
                # Calculate individual scores
                base_semantic_score = candidate.get('similarity_score', 0.0)
                
                # Boost semantic score with keyword matching
                semantic_score = self._boost_semantic_score(
                    base_semantic_score, 
                    enhanced_query, 
                    paper_data[1],  # title
                    paper_data[2]   # abstract
                )
                
                authority_score = self._calculate_authority_score(
                    citation_count=paper_data[4],
                    reference_count=paper_data[5], 
                    paper_score=paper_data[6],
                    cluster_size=1  # Could be enhanced with cluster size calculation
                )
                
                recency_score = self._calculate_recency_score(
                    publication_year=int(paper_data[9]) if paper_data[9] else None
                )
                
                diversity_score = self._calculate_diversity_score(
                    paper_cluster=paper_data[7],
                    user_clusters=user_clusters,
                    paper_topic=paper_data[8]
                )
                
                # Calculate final weighted score
                final_score = (
                    semantic_score * current_weights['semantic'] +
                    authority_score * current_weights['authority'] +
                    recency_score * current_weights['recency'] +
                    diversity_score * current_weights['diversity']
                ) * 100  # Scale to 0-100
                
                # Filter by minimum score
                if final_score < min_score:
                    continue
                
                # Generate recommendation reason
                reason = self._get_recommendation_reason(
                    semantic_score, authority_score, recency_score, 
                    diversity_score, context
                )
                
                recommendation = {
                    'paper_id': paper_data[0],
                    'title': paper_data[1],
                    'abstract': paper_data[2],
                    'authors': paper_data[3] or [],
                    'final_score': round(final_score, 2),
                    'semantic_score': round(semantic_score, 3),
                    'authority_score': round(authority_score, 3),
                    'recency_score': round(recency_score, 3),
                    'diversity_score': round(diversity_score, 3),
                    'publication_year': int(paper_data[9]) if paper_data[9] else None,
                    'cluster': paper_data[7],
                    'topic': paper_data[8],
                    'citation_count': paper_data[4],
                    'reference_count': paper_data[5],
                    'paper_score': paper_data[6],
                    'recommendation_reason': reason
                }
                
                recommendations.append(recommendation)
            
            # Step 3: Sort by final score and limit results
            recommendations.sort(key=lambda x: x['final_score'], reverse=True)
            final_recommendations = recommendations[:limit]
            
            # Step 4: Calculate statistics
            execution_time = (time.time() - start_time) * 1000  # ms
            
            if final_recommendations:
                avg_scores = {
                    'semantic': sum(r['semantic_score'] for r in final_recommendations) / len(final_recommendations),
                    'authority': sum(r['authority_score'] for r in final_recommendations) / len(final_recommendations),
                    'recency': sum(r['recency_score'] for r in final_recommendations) / len(final_recommendations),
                    'diversity': sum(r['diversity_score'] for r in final_recommendations) / len(final_recommendations)
                }
                
                cluster_dist = {}
                for rec in final_recommendations:
                    cluster = rec.get('cluster', 'Unknown')
                    cluster_dist[cluster] = cluster_dist.get(cluster, 0) + 1
            else:
                avg_scores = {'semantic': 0, 'authority': 0, 'recency': 0, 'diversity': 0}
                cluster_dist = {}
            
            statistics = {
                'execution_time_ms': round(execution_time, 2),
                'semantic_candidates': len(semantic_candidates),
                'total_scored': len(recommendations),
                'final_recommendations': len(final_recommendations),
                'avg_scores': avg_scores,
                'cluster_distribution': cluster_dist,
                'context_weights': current_weights
            }
            
            close_connection(conn)
            
            logger.info(f"✅ Generated {len(final_recommendations)} recommendations in {execution_time:.1f}ms")
            return final_recommendations, statistics
            
        except Exception as e:
            logger.error(f"❌ Error in recommendation generation: {e}")
            raise
    
    def get_user_preference_clusters(self, user_id: str) -> List[str]:
        """
        Get user's preferred clusters based on interaction history
        This is a placeholder - would be implemented with user tracking
        """
        # TODO: Implement user interaction tracking
        # For now, return empty list
        return []


# Global instance
_recommendation_engine = None

def get_recommendation_engine() -> PaperRecommendationEngine:
    """Get or create global recommendation engine instance"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = PaperRecommendationEngine()
    return _recommendation_engine
