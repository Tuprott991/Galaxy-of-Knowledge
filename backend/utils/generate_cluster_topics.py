#!/usr/bin/env python3
"""
Script to generate topics for all clusters and save to database
"""

import sys
import os
import logging
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connect import connect, close_connection
from services.topic_generator import get_topic_generator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClusterTopicUpdater:
    """Class to generate and update cluster topics in database"""
    
    def __init__(self):
        self.conn = None
        self.topic_generator = None
    
    def connect_db(self):
        """Connect to database"""
        try:
            self.conn = connect()
            logger.info("✅ Connected to database")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def initialize_topic_generator(self):
        """Initialize AI topic generator"""
        try:
            self.topic_generator = get_topic_generator()
            logger.info("✅ Topic generator initialized")
        except Exception as e:
            logger.error(f"❌ Topic generator initialization failed: {e}")
            raise
    
    def get_clusters_without_topics(self, min_papers: int = 3) -> List[Tuple]:
        """Get clusters that don't have topics yet"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                cluster,
                COUNT(*) as paper_count,
                array_agg(title ORDER BY paper_id) as titles
            FROM paper 
            WHERE cluster IS NOT NULL 
              AND title IS NOT NULL
              AND (topic IS NULL OR topic = '')
            GROUP BY cluster
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
        """
        
        cursor.execute(query, (min_papers,))
        results = cursor.fetchall()
        cursor.close()
        
        logger.info(f"📊 Found {len(results)} clusters without topics (min {min_papers} papers each)")
        return results
    
    def get_all_clusters(self, min_papers: int = 3) -> List[Tuple]:
        """Get all clusters (for force update)"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                cluster,
                COUNT(*) as paper_count,
                array_agg(title ORDER BY paper_id) as titles
            FROM paper 
            WHERE cluster IS NOT NULL 
              AND title IS NOT NULL
            GROUP BY cluster
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC
        """
        
        cursor.execute(query, (min_papers,))
        results = cursor.fetchall()
        cursor.close()
        
        logger.info(f"📊 Found {len(results)} total clusters (min {min_papers} papers each)")
        return results
    
    def update_cluster_topic(self, cluster_id: str, topic: str, confidence: float) -> bool:
        """Update topic for all papers in a cluster"""
        try:
            cursor = self.conn.cursor()
            
            # Update all papers in the cluster
            update_query = """
                UPDATE paper 
                SET topic = %s, updated_at = CURRENT_TIMESTAMP
                WHERE cluster = %s
            """
            
            cursor.execute(update_query, (topic, cluster_id))
            updated_count = cursor.rowcount
            
            self.conn.commit()
            cursor.close()
            
            logger.info(f"✅ Updated {updated_count} papers in cluster {cluster_id[:8]}... with topic '{topic}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update cluster {cluster_id}: {e}")
            self.conn.rollback()
            return False
    
    def generate_and_save_topics(self, force_update: bool = False, min_papers: int = 3):
        """Main function to generate and save all topics"""
        logger.info("🚀 Starting cluster topic generation and database update")
        logger.info(f"   Force update: {force_update}")
        logger.info(f"   Min papers per cluster: {min_papers}")
        
        # Get clusters to process
        if force_update:
            clusters = self.get_all_clusters(min_papers)
            logger.info("🔄 Force update mode: processing ALL clusters")
        else:
            clusters = self.get_clusters_without_topics(min_papers)
            logger.info("➕ Incremental mode: processing only clusters without topics")
        
        if not clusters:
            logger.info("✨ No clusters to process. All done!")
            return
        
        # Process each cluster
        success_count = 0
        failed_count = 0
        
        logger.info(f"📋 Processing {len(clusters)} clusters...")
        
        for i, (cluster_id, paper_count, titles) in enumerate(clusters, 1):
            logger.info(f"\n{i}/{len(clusters)}. Processing cluster {cluster_id[:8]}... ({paper_count} papers)")
            
            try:
                # Generate topic using AI
                topic_name, confidence = self.topic_generator.generate_topic_from_titles(
                    titles, cluster_id
                )
                
                logger.info(f"   🧠 Generated: '{topic_name}' (confidence: {confidence:.2f})")
                
                # Save to database
                if self.update_cluster_topic(cluster_id, topic_name, confidence):
                    success_count += 1
                else:
                    failed_count += 1
                
            except Exception as e:
                logger.error(f"   ❌ Failed to process cluster {cluster_id}: {e}")
                failed_count += 1
        
        # Summary
        logger.info(f"\n🏁 Topic generation completed!")
        logger.info(f"   ✅ Successful: {success_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        logger.info(f"   📊 Total processed: {len(clusters)}")
        
        if success_count > 0:
            logger.info(f"🎉 {success_count} clusters now have AI-generated topics!")
    
    def get_topic_statistics(self):
        """Get statistics about topics in database"""
        cursor = self.conn.cursor()
        
        # Total papers
        cursor.execute("SELECT COUNT(*) FROM paper")
        total_papers = cursor.fetchone()[0]
        
        # Papers with topics
        cursor.execute("SELECT COUNT(*) FROM paper WHERE topic IS NOT NULL AND topic != ''")
        papers_with_topics = cursor.fetchone()[0]
        
        # Unique topics
        cursor.execute("SELECT COUNT(DISTINCT topic) FROM paper WHERE topic IS NOT NULL AND topic != ''")
        unique_topics = cursor.fetchone()[0]
        
        # Top topics
        cursor.execute("""
            SELECT topic, COUNT(*) as paper_count
            FROM paper 
            WHERE topic IS NOT NULL AND topic != ''
            GROUP BY topic
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        top_topics = cursor.fetchall()
        
        cursor.close()
        
        logger.info(f"\n📊 DATABASE TOPIC STATISTICS")
        logger.info(f"   📄 Total papers: {total_papers}")
        logger.info(f"   🏷️  Papers with topics: {papers_with_topics}")
        logger.info(f"   📈 Coverage: {(papers_with_topics/total_papers*100):.1f}%")
        logger.info(f"   🎯 Unique topics: {unique_topics}")
        
        if top_topics:
            logger.info(f"\n🏆 TOP TOPICS:")
            for i, (topic, count) in enumerate(top_topics, 1):
                logger.info(f"   {i:2d}. {topic} ({count} papers)")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            close_connection(self.conn)
            logger.info("🔒 Database connection closed")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate and save cluster topics")
    parser.add_argument("--force", action="store_true", help="Force update all clusters (not just empty ones)")
    parser.add_argument("--min-papers", type=int, default=3, help="Minimum papers per cluster")
    parser.add_argument("--stats-only", action="store_true", help="Only show statistics, don't generate topics")
    
    args = parser.parse_args()
    
    updater = ClusterTopicUpdater()
    
    try:
        # Connect to database
        updater.connect_db()
        
        if args.stats_only:
            # Only show statistics
            updater.get_topic_statistics()
        else:
            # Initialize topic generator
            updater.initialize_topic_generator()
            
            # Generate and save topics
            updater.generate_and_save_topics(
                force_update=args.force,
                min_papers=args.min_papers
            )
            
            # Show final statistics
            updater.get_topic_statistics()
    
    except Exception as e:
        logger.error(f"💥 Script failed: {e}")
        return 1
    
    finally:
        updater.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
