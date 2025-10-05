#!/usr/bin/env python3
"""
Step 2: Extract Key Knowledge from Projects

Use Gemini 2.5 Flash to extract structured summaries from project descriptions.
Usage: python step2_extract_knowledge.py [--limit N]
"""

import sys
import os
import logging
import argparse

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.extract_key_knowledge import extract_all_project_summaries
from database.project_database import ProjectDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to extract key knowledge from projects"""
    parser = argparse.ArgumentParser(description='Extract key knowledge from projects using LLM')
    parser.add_argument('--limit', type=int, help='Maximum number of projects to process')
    parser.add_argument('--check-only', action='store_true', help='Only check how many projects need processing')
    args = parser.parse_args()
    
    logger.info("🔍 Starting key knowledge extraction...")
    
    try:
        # Check current status
        db = ProjectDatabase()
        try:
            stats = db.get_project_statistics()
            total_projects = stats.get('total_projects', 0)
            with_summaries = stats.get('projects_with_summaries', 0)
            without_summaries = total_projects - with_summaries
            
            logger.info(f"📊 Current database status:")
            logger.info(f"   - Total projects: {total_projects}")
            logger.info(f"   - With summaries: {with_summaries}")
            logger.info(f"   - Need processing: {without_summaries}")
            
            if args.check_only:
                print(f"\n📊 STATUS CHECK:")
                print(f"   - Total projects: {total_projects}")
                print(f"   - Already processed: {with_summaries}")
                print(f"   - Need processing: {without_summaries}")
                return
            
            if without_summaries == 0:
                logger.info("✅ All projects already have summaries!")
                print("✅ All projects already have summaries!")
                return
            
            # Get projects that need processing
            projects_to_process = db.get_projects_without_summaries(args.limit)
            
            if not projects_to_process:
                logger.info("✅ No projects found that need summaries")
                print("✅ No projects found that need summaries")
                return
            
            logger.info(f"🔄 Will process {len(projects_to_process)} projects")
            
            if args.limit:
                logger.info(f"   (Limited to {args.limit} projects)")
            
        finally:
            db.close_connection()
        
        # Perform extraction
        logger.info("🤖 Starting LLM-based key knowledge extraction...")
        stats = extract_all_project_summaries(args.limit)
        
        logger.info("✅ Key knowledge extraction completed!")
        logger.info(f"📊 Results:")
        logger.info(f"   - Processed: {stats['processed']}")
        logger.info(f"   - Successful: {stats['successful']}")
        logger.info(f"   - Failed: {stats['failed']}")
        logger.info(f"   - Total cost: ${stats['total_cost_usd']:.4f}")
        logger.info(f"   - Input tokens: {stats['total_tokens_input']:,}")
        logger.info(f"   - Output tokens: {stats['total_tokens_output']:,}")
        
        # Show updated statistics
        db = ProjectDatabase()
        try:
            updated_stats = db.get_project_statistics()
            logger.info(f"📈 Updated database status:")
            logger.info(f"   - Total projects: {updated_stats.get('total_projects', 0)}")
            logger.info(f"   - With summaries: {updated_stats.get('projects_with_summaries', 0)}")
            
        finally:
            db.close_connection()
        
        logger.info("🎉 Step 2 completed successfully!")
        print(f"\n✅ SUCCESS: Processed {stats['processed']} projects")
        print(f"   - Successful: {stats['successful']}")
        print(f"   - Failed: {stats['failed']}")
        print(f"   - Cost: ${stats['total_cost_usd']:.4f}")
        
    except Exception as e:
        logger.error(f"❌ Error during knowledge extraction: {e}")
        print(f"\n❌ FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
