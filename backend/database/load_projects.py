#!/usr/bin/env python3
"""
Step 1: Load Projects from Excel

Load NASA/research project data from Excel files into the database.
Usage: python step1_load_projects.py <excel_file_path>
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.project_loader import load_projects_from_excel
from database.project_database import ProjectDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to load projects from Excel file"""
    if len(sys.argv) != 2:
        print("Usage: python step1_load_projects.py <excel_file_path>")
        print("Example: python step1_load_projects.py /path/to/projects.xlsx")
        sys.exit(1)
    
    excel_file_path = sys.argv[1]
    
    # Validate file exists
    if not os.path.exists(excel_file_path):
        logger.error(f"File not found: {excel_file_path}")
        sys.exit(1)
    
    # Validate file extension
    if not excel_file_path.endswith(('.xlsx', '.xls')):
        logger.error("File must be an Excel file (.xlsx or .xls)")
        sys.exit(1)
    
    logger.info(f"🔄 Starting project loading from: {excel_file_path}")
    
    try:
        # Load projects from Excel
        logger.info("📊 Loading projects from Excel file...")
        projects = load_projects_from_excel(excel_file_path)
        
        if not projects:
            logger.error("❌ No valid projects found in Excel file")
            sys.exit(1)
        
        logger.info(f"✅ Successfully loaded {len(projects)} projects from Excel")
        
        # Insert projects into database
        logger.info("💾 Inserting projects into database...")
        db = ProjectDatabase()
        
        try:
            inserted, updated = db.insert_projects(projects)
            
            logger.info(f"✅ Database operation completed:")
            logger.info(f"   - New projects inserted: {inserted}")
            logger.info(f"   - Existing projects updated: {updated}")
            logger.info(f"   - Total projects processed: {len(projects)}")
            
            # Show statistics
            stats = db.get_project_statistics()
            logger.info(f"📈 Current database status:")
            logger.info(f"   - Total projects in database: {stats.get('total_projects', 0)}")
            logger.info(f"   - Projects with summaries: {stats.get('projects_with_summaries', 0)}")
            logger.info(f"   - Projects with embeddings: {stats.get('projects_with_embeddings', 0)}")
            
        finally:
            db.close_connection()
        
        logger.info("🎉 Step 1 completed successfully!")
        print(f"\n✅ SUCCESS: Loaded {len(projects)} projects")
        print(f"   - Inserted: {inserted} new projects")
        print(f"   - Updated: {updated} existing projects")
        
    except Exception as e:
        logger.error(f"❌ Error during project loading: {e}")
        print(f"\n❌ FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
