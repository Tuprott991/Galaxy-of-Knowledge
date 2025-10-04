"""
Embedding Ingestion Script
This script reads papers from the database, creates embeddings from title + abstract,
and updates the embeddings field in the corresponding paper records.
"""

import sys
import os
import logging
from typing import List, Dict, Any, Optional
import time

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


class EmbeddingIngestion:
    """
    Class to handle embedding generation and ingestion for papers
    """
    
    def __init__(self, batch_size: int = 10):
        """
        Initialize the embedding ingestion service
        
        Args:
            batch_size: Number of papers to process in each batch
        """
        self.batch_size = batch_size
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
    
    def get_papers_without_embeddings(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch papers that don't have embeddings yet
        
        Args:
            limit: Maximum number of papers to fetch (None for all)
            
        Returns:
            List of paper dictionaries with id, paper_id, title, and abstract
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
                SELECT id, paper_id, title, abstract
                FROM paper
                WHERE embeddings IS NULL 
                AND title IS NOT NULL
                ORDER BY id
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            papers = cursor.fetchall()
            
            papers_list = [
                {
                    'id': paper[0],
                    'paper_id': paper[1],
                    'title': paper[2],
                    'abstract': paper[3] or ''  # Use empty string if abstract is None
                }
                for paper in papers
            ]
            
            cursor.close()
            logger.info(f"Found {len(papers_list)} papers without embeddings")
            return papers_list
            
        except Exception as e:
            logger.error(f"Error fetching papers: {e}")
            raise
    
    def create_text_for_embedding(self, title: str, abstract: str) -> str:
        """
        Create combined text from title and abstract for embedding
        
        Args:
            title: Paper title
            abstract: Paper abstract
            
        Returns:
            Combined text string
        """
        # Combine title and abstract with a separator
        text = f"Title: {title}\n\nAbstract: {abstract}"
        return text.strip()
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for given text using the embedding model
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Generate embedding using Vertex AI model
            embeddings = self.embedding_model.get_embeddings([text])
            
            # Extract the embedding values
            embedding_vector = embeddings[0].values
            
            return embedding_vector
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def update_paper_embedding(self, paper_id: int, embedding: List[float]) -> bool:
        """
        Update paper with generated embedding
        
        Args:
            paper_id: Database ID of the paper
            embedding: Embedding vector to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            # Convert embedding list to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            
            query = """
                UPDATE paper
                SET embeddings = %s::vector,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            cursor.execute(query, (embedding_str, paper_id))
            self.conn.commit()
            cursor.close()
            
            logger.debug(f"Updated embedding for paper ID {paper_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating paper {paper_id}: {e}")
            self.conn.rollback()
            return False
    
    def process_papers(self, limit: Optional[int] = None, delay: float = 0.5):
        """
        Process papers in batches to generate and store embeddings
        
        Args:
            limit: Maximum number of papers to process (None for all)
            delay: Delay in seconds between API calls to avoid rate limiting
        """
        try:
            # Fetch papers without embeddings
            papers = self.get_papers_without_embeddings(limit=limit)
            
            if not papers:
                logger.info("No papers found that need embeddings")
                return
            
            total_papers = len(papers)
            successful = 0
            failed = 0
            
            logger.info(f"Starting to process {total_papers} papers...")
            
            # Process papers in batches
            for idx, paper in enumerate(papers, 1):
                try:
                    # Create text for embedding
                    text = self.create_text_for_embedding(
                        paper['title'], 
                        paper['abstract']
                    )
                    
                    # Generate embedding
                    logger.info(f"Processing paper {idx}/{total_papers}: {paper['paper_id']}")
                    embedding = self.generate_embedding(text)
                    
                    # Update database
                    if self.update_paper_embedding(paper['id'], embedding):
                        successful += 1
                        logger.info(f"✓ Successfully processed paper {paper['paper_id']} ({idx}/{total_papers})")
                    else:
                        failed += 1
                        logger.warning(f"✗ Failed to update paper {paper['paper_id']}")
                    
                    # Add delay to avoid rate limiting
                    if idx < total_papers:
                        time.sleep(delay)
                    
                    # Progress update every 10 papers
                    if idx % 10 == 0:
                        logger.info(f"Progress: {idx}/{total_papers} papers processed")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error processing paper {paper.get('paper_id', 'unknown')}: {e}")
                    continue
            
            # Final summary
            logger.info("=" * 60)
            logger.info(f"Processing complete!")
            logger.info(f"Total papers: {total_papers}")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error in process_papers: {e}")
            raise
    
    def get_embedding_stats(self) -> Dict[str, int]:
        """
        Get statistics about embeddings in the database
        
        Returns:
            Dictionary with counts of papers with/without embeddings
        """
        try:
            cursor = self.conn.cursor()
            
            # Count papers with embeddings
            cursor.execute("SELECT COUNT(*) FROM paper WHERE embeddings IS NOT NULL")
            with_embeddings = cursor.fetchone()[0]
            
            # Count papers without embeddings
            cursor.execute("SELECT COUNT(*) FROM paper WHERE embeddings IS NULL")
            without_embeddings = cursor.fetchone()[0]
            
            # Count total papers
            cursor.execute("SELECT COUNT(*) FROM paper")
            total = cursor.fetchone()[0]
            
            cursor.close()
            
            return {
                'total': total,
                'with_embeddings': with_embeddings,
                'without_embeddings': without_embeddings,
                'percentage_complete': round((with_embeddings / total * 100) if total > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise


def main():
    """Main function to run embedding ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate and ingest embeddings for papers')
    parser.add_argument('--limit', type=int, default=None, 
                        help='Limit number of papers to process (default: all)')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Batch size for processing (default: 10)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between API calls in seconds (default: 0.5)')
    parser.add_argument('--stats', action='store_true',
                        help='Show embedding statistics and exit')
    
    args = parser.parse_args()
    
    # Initialize embedding ingestion
    ingestion = EmbeddingIngestion(batch_size=args.batch_size)
    
    try:
        ingestion.initialize()
        
        if args.stats:
            # Show statistics
            stats = ingestion.get_embedding_stats()
            print("\n" + "=" * 60)
            print("Embedding Statistics")
            print("=" * 60)
            print(f"Total papers: {stats['total']}")
            print(f"With embeddings: {stats['with_embeddings']}")
            print(f"Without embeddings: {stats['without_embeddings']}")
            print(f"Completion: {stats['percentage_complete']}%")
            print("=" * 60 + "\n")
        else:
            # Process papers
            ingestion.process_papers(limit=args.limit, delay=args.delay)
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        ingestion.close()


if __name__ == "__main__":
    main()
