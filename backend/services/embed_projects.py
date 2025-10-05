"""
Step 4: Generate Embeddings and Save to Database

Uses text-multilingual-embedding-002 to create vector embeddings for project summaries.
Stores vectors in PostgreSQL using pgvector for future semantic search.
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional
import sys
import os

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embedding_provider import get_embedding_model
from database.project_database import ProjectDatabase

logger = logging.getLogger(__name__)


class ProjectEmbeddingGenerator:
    """Class to generate and store embeddings for project summaries"""
    
    def __init__(self):
        self.embedding_model = get_embedding_model()
        self.db = ProjectDatabase()
        
        # Cost estimation for text-multilingual-embedding-002
        self.cost_per_1k_tokens = 0.00025  # $0.25 per 1M tokens
    
    def embed_all_projects(self, limit: Optional[int] = None, batch_size: int = 10) -> Dict[str, Any]:
        """
        Generate embeddings for all projects that have summaries but no embeddings
        
        Args:
            limit: Maximum number of projects to process
            batch_size: Number of projects to process in each batch
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get projects that need embeddings
            projects = self.db.get_projects_without_embeddings(limit)
            
            if not projects:
                logger.info("No projects found that need embeddings")
                return {
                    'processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'total_cost_usd': 0.0
                }
            
            logger.info(f"Processing {len(projects)} projects for embedding generation")
            
            stats = {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'total_cost_usd': 0.0,
                'total_tokens': 0
            }
            
            # Process projects in batches
            for i in range(0, len(projects), batch_size):
                batch = projects[i:i + batch_size]
                batch_stats = self._process_batch(batch)
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                # Progress logging
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(projects) + batch_size - 1)//batch_size}")
                logger.info(f"Batch stats: {batch_stats['successful']} successful, {batch_stats['failed']} failed")
                
                # Small delay between batches to avoid rate limiting
                time.sleep(1.0)
            
            logger.info(f"Embedding generation completed: {stats['successful']} successful, {stats['failed']} failed")
            logger.info(f"Total cost: ${stats['total_cost_usd']:.4f}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in embed_all_projects: {e}")
            return stats
        finally:
            self.db.close_connection()
    
    def _process_batch(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of projects for embedding generation
        
        Args:
            projects: List of project dictionaries
            
        Returns:
            Batch processing statistics
        """
        batch_stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'total_cost_usd': 0.0,
            'total_tokens': 0
        }
        
        try:
            # Prepare texts for embedding
            texts_for_embedding = []
            project_ids = []
            
            for project in projects:
                text = self._prepare_text_for_embedding(project)
                if text:
                    texts_for_embedding.append(text)
                    project_ids.append(project['project_id'])
                else:
                    logger.warning(f"No text to embed for project {project['project_id']}")
                    batch_stats['failed'] += 1
                    batch_stats['processed'] += 1
            
            if not texts_for_embedding:
                return batch_stats
            
            # Generate embeddings for the batch
            start_time = time.time()
            embeddings, cost_info = self._generate_embeddings_batch(texts_for_embedding)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if embeddings and len(embeddings) == len(project_ids):
                # Store embeddings in database
                for i, (project_id, embedding) in enumerate(zip(project_ids, embeddings)):
                    try:
                        success = self.db.update_project_embedding(project_id, embedding)
                        
                        if success:
                            batch_stats['successful'] += 1
                            
                            # Log cost for this project
                            project_cost = cost_info['cost_usd'] / len(project_ids)
                            project_tokens = cost_info['total_tokens'] // len(project_ids)
                            
                            self.db.log_cost(
                                operation_type='embedding',
                                tokens_input=project_tokens,
                                cost_usd=project_cost,
                                response_time_ms=response_time_ms // len(project_ids),
                                paper_id=project_id
                            )
                        else:
                            batch_stats['failed'] += 1
                        
                        batch_stats['processed'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error storing embedding for project {project_id}: {e}")
                        batch_stats['failed'] += 1
                        batch_stats['processed'] += 1
                
                batch_stats['total_cost_usd'] += cost_info['cost_usd']
                batch_stats['total_tokens'] += cost_info['total_tokens']
            else:
                logger.error(f"Embedding generation failed for batch of {len(project_ids)} projects")
                batch_stats['failed'] += len(project_ids)
                batch_stats['processed'] += len(project_ids)
            
            return batch_stats
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            batch_stats['failed'] += len(projects) - batch_stats['processed']
            batch_stats['processed'] = len(projects)
            return batch_stats
    
    def _prepare_text_for_embedding(self, project: Dict[str, Any]) -> str:
        """
        Prepare text for embedding by combining summary and key metadata
        
        Args:
            project: Project dictionary
            
        Returns:
            Text string optimized for embedding
        """
        text_parts = []
        
        # Use structured summary if available
        summary = project.get('summary')
        if summary and isinstance(summary, dict):
            # Extract key fields from structured summary
            objective = summary.get('objective', '')
            methodology = summary.get('methodology', '')
            key_findings = summary.get('key_findings', '')
            potential_benefit = summary.get('potential_benefit', '')
            technical_domain = summary.get('technical_domain', '')
            
            if objective:
                text_parts.append(f"Objective: {objective}")
            if methodology:
                text_parts.append(f"Methodology: {methodology}")
            if key_findings and key_findings != 'Ongoing research':
                text_parts.append(f"Findings: {key_findings}")
            if potential_benefit:
                text_parts.append(f"Benefits: {potential_benefit}")
            if technical_domain:
                text_parts.append(f"Domain: {technical_domain}")
        
        # Add title and abstract as fallback
        if not text_parts:
            title = project.get('title', '').strip()
            abstract = project.get('abstract', '').strip()
            
            if title:
                text_parts.append(f"Title: {title}")
            if abstract:
                text_parts.append(f"Abstract: {abstract}")
        
        # Join all parts
        full_text = ' '.join(text_parts)
        
        # Truncate if too long (embedding models usually have token limits)
        max_chars = 8000  # Conservative limit for text-multilingual-embedding-002
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + '...'
        
        return full_text.strip()
    
    def _generate_embeddings_batch(self, texts: List[str]) -> tuple[Optional[List[List[float]]], Dict[str, Any]]:
        """
        Generate embeddings for a batch of texts
        
        Args:
            texts: List of text strings
            
        Returns:
            Tuple of (embeddings_list, cost_info)
        """
        try:
            # Estimate tokens (rough approximation)
            total_chars = sum(len(text) for text in texts)
            estimated_tokens = total_chars // 4  # Rough approximation
            
            # Generate embeddings
            embeddings = self.embedding_model.get_embeddings(texts)
            
            if embeddings and len(embeddings) == len(texts):
                # Extract the embedding vectors
                embedding_vectors = [emb.values for emb in embeddings]
                
                # Calculate cost
                cost_usd = (estimated_tokens / 1000) * self.cost_per_1k_tokens
                
                cost_info = {
                    'total_tokens': estimated_tokens,
                    'cost_usd': cost_usd
                }
                
                logger.info(f"Generated {len(embedding_vectors)} embeddings, estimated cost: ${cost_usd:.6f}")
                return embedding_vectors, cost_info
            else:
                logger.error(f"Embedding generation failed. Expected {len(texts)} embeddings, got {len(embeddings) if embeddings else 0}")
                return None, {'total_tokens': estimated_tokens, 'cost_usd': 0.0}
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return None, {'total_tokens': 0, 'cost_usd': 0.0}
    
    def embed_single_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text (used for paper analysis)
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None
        """
        try:
            embeddings, _ = self._generate_embeddings_batch([text])
            
            if embeddings and len(embeddings) == 1:
                return embeddings[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error generating single embedding: {e}")
            return None
    
    def get_embedding_statistics(self) -> Dict[str, Any]:
        """Get statistics about embeddings in the database"""
        try:
            stats = self.db.get_project_statistics()
            
            embedding_stats = {
                'total_projects': stats.get('total_projects', 0),
                'projects_with_embeddings': stats.get('projects_with_embeddings', 0),
                'projects_with_summaries': stats.get('projects_with_summaries', 0),
                'embedding_coverage': 0.0
            }
            
            if embedding_stats['total_projects'] > 0:
                embedding_stats['embedding_coverage'] = (
                    embedding_stats['projects_with_embeddings'] / embedding_stats['total_projects']
                ) * 100
            
            return embedding_stats
            
        except Exception as e:
            logger.error(f"Error getting embedding statistics: {e}")
            return {}
        finally:
            self.db.close_connection()


def embed_all_projects(limit: Optional[int] = None, batch_size: int = 10) -> Dict[str, Any]:
    """
    Convenience function to generate embeddings for all projects
    
    Args:
        limit: Maximum number of projects to process
        batch_size: Batch size for processing
        
    Returns:
        Processing statistics
    """
    generator = ProjectEmbeddingGenerator()
    return generator.embed_all_projects(limit, batch_size)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Generate embeddings for projects')
    parser.add_argument('--limit', type=int, help='Maximum number of projects to process')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    args = parser.parse_args()
    
    # Run embedding generation
    print("🔮 Starting embedding generation...")
    stats = embed_all_projects(args.limit, args.batch_size)
    
    print(f"\n📊 EMBEDDING RESULTS")
    print(f"   - Processed: {stats['processed']}")
    print(f"   - Successful: {stats['successful']}")
    print(f"   - Failed: {stats['failed']}")
    print(f"   - Total cost: ${stats['total_cost_usd']:.4f}")
    print(f"   - Total tokens: {stats['total_tokens']:,}")
    
    # Show embedding statistics
    generator = ProjectEmbeddingGenerator()
    embedding_stats = generator.get_embedding_statistics()
    
    print(f"\n📈 DATABASE STATUS")
    print(f"   - Total projects: {embedding_stats.get('total_projects', 0)}")
    print(f"   - With summaries: {embedding_stats.get('projects_with_summaries', 0)}")
    print(f"   - With embeddings: {embedding_stats.get('projects_with_embeddings', 0)}")
    print(f"   - Embedding coverage: {embedding_stats.get('embedding_coverage', 0):.1f}%")
