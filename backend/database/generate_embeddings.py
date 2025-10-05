#!/usr/bin/env python3
"""
Step 3: Generate Project Embeddings

Generate vector embeddings for project summaries using text-multilingual-embedding-002.
Usage: python step3_generate_embeddings.py [--limit N] [--batch-size N]
"""

import sys
import os
import logging
import argparse

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.embed_projects import embed_all_projects, ProjectEmbeddingGenerator
from database.project_database import ProjectDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to generate embeddings for projects"""
    parser = argparse.ArgumentParser(description='Generate embeddings for project summaries')
    parser.add_argument('--limit', type=int, help='Maximum number of projects to process')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing (default: 10)')
    parser.add_argument('--check-only', action='store_true', help='Only check how many projects need processing')
    args = parser.parse_args()
    
    logger.info("🔮 Starting embedding generation...")
    
    try:
        # Check current status
        db = ProjectDatabase()
        try:
            stats = db.get_project_statistics()
            total_projects = stats.get('total_projects', 0)
            with_summaries = stats.get('projects_with_summaries', 0)
            with_embeddings = stats.get('projects_with_embeddings', 0)
            need_embeddings = with_summaries - with_embeddings
            
            logger.info(f"📊 Current database status:")
            logger.info(f"   - Total projects: {total_projects}")
            logger.info(f"   - With summaries: {with_summaries}")
            logger.info(f"   - With embeddings: {with_embeddings}")
            logger.info(f"   - Need embeddings: {need_embeddings}")
            
            if args.check_only:
                print(f"\n📊 STATUS CHECK:")
                print(f"   - Total projects: {total_projects}")
                print(f"   - With summaries: {with_summaries}")
                print(f"   - With embeddings: {with_embeddings}")
                print(f"   - Need processing: {need_embeddings}")
                return
            
            if need_embeddings <= 0:
                logger.info("✅ All projects with summaries already have embeddings!")
                print("✅ All projects with summaries already have embeddings!")
                return
            
            if with_summaries == 0:
                logger.warning("⚠️  No projects have summaries yet. Run step2_extract_knowledge.py first.")
                print("⚠️  No projects have summaries yet. Run step2_extract_knowledge.py first.")
                return
            
            # Get projects that need embeddings
            projects_to_process = db.get_projects_without_embeddings(args.limit)
            
            if not projects_to_process:
                logger.info("✅ No projects found that need embeddings")
                print("✅ No projects found that need embeddings")
                return
            
            logger.info(f"🔄 Will process {len(projects_to_process)} projects")
            logger.info(f"   Batch size: {args.batch_size}")
            
            if args.limit:
                logger.info(f"   (Limited to {args.limit} projects)")
            
        finally:
            db.close_connection()
        
        # Perform embedding generation
        logger.info("🤖 Starting embedding generation...")
        stats = embed_all_projects(args.limit, args.batch_size)
        
        logger.info("✅ Embedding generation completed!")
        logger.info(f"📊 Results:")
        logger.info(f"   - Processed: {stats['processed']}")
        logger.info(f"   - Successful: {stats['successful']}")
        logger.info(f"   - Failed: {stats['failed']}")
        logger.info(f"   - Total cost: ${stats['total_cost_usd']:.4f}")
        logger.info(f"   - Total tokens: {stats['total_tokens']:,}")
        
        # Show updated statistics
        generator = ProjectEmbeddingGenerator()
        try:
            embedding_stats = generator.get_embedding_statistics()
            logger.info(f"📈 Updated database status:")
            logger.info(f"   - Total projects: {embedding_stats.get('total_projects', 0)}")
            logger.info(f"   - With summaries: {embedding_stats.get('projects_with_summaries', 0)}")
            logger.info(f"   - With embeddings: {embedding_stats.get('projects_with_embeddings', 0)}")
            logger.info(f"   - Embedding coverage: {embedding_stats.get('embedding_coverage', 0):.1f}%")
        finally:
            generator.db.close_connection()
        
        logger.info("🎉 Step 3 completed successfully!")
        print(f"\n✅ SUCCESS: Processed {stats['processed']} projects")
        print(f"   - Successful: {stats['successful']}")
        print(f"   - Failed: {stats['failed']}")
        print(f"   - Cost: ${stats['total_cost_usd']:.4f}")
        print(f"   - Coverage: {embedding_stats.get('embedding_coverage', 0):.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Error during embedding generation: {e}")
        print(f"\n❌ FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
