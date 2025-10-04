import os
import json
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaperDatabase:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Create database connection"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                port=os.getenv('DB_PORT', 5432)
            )
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def insert_paper(self, paper_data: Dict[str, Any]) -> Optional[int]:
        """Insert a paper into the database - only json_data, other fields will be filled later"""
        try:
            cursor = self.conn.cursor()
            
            # Extract title
            title = paper_data.get("title")
            paper_id = paper_data.get("PMCID")
            
            # Extract abstract from nested structure
            abstract = None
            sections = paper_data.get("sections", {})
            if sections and isinstance(sections, dict) and "abstract" in sections:
                if isinstance(sections["abstract"], dict) and "_content" in sections["abstract"]:
                    abstract = sections["abstract"]["_content"]
            
            # Insert paper with only json_data, other fields left empty for later processing
            insert_query = """
            INSERT INTO paper (
                paper_id,
                title,
                abstract,
                json_data,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING paper_id
            """
            
            cursor.execute(insert_query, (
                paper_id,
                title,
                abstract,
                Json(paper_data)  # Store entire JSON as json_data
            ))
            
            paper_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            
            logger.info(f"Inserted paper with ID: {paper_id} - Title: {title[:50]}...")
            return paper_id
            
        except Exception as e:
            logger.error(f"Error inserting paper: {e}")
            if self.conn:
                self.conn.rollback()
            return None

def load_json_files_from_folder(folder_path: str) -> List[Dict[str, Any]]:
    """Load all JSON files from a folder"""
    json_data_list = []
    
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return json_data_list
    
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    logger.info(f"Found {len(json_files)} JSON files in {folder_path}")
    
    for filename in json_files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file) # not need file_name
                json_data_list.append(data)
                logger.info(f"Loaded: {filename}")
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
    
    return json_data_list

def process_papers_from_folder(folder_path: str):
    """Main function to process all JSON files in a folder and insert into database"""
    # Load all JSON files
    papers_data = load_json_files_from_folder(folder_path)
    
    if not papers_data:
        logger.warning("No valid JSON files found to process")
        return
    
    # Initialize database
    db = PaperDatabase()
    
    try:
        successful_inserts = 0
        failed_inserts = 0
        
        for i, paper_data in enumerate(papers_data, 1):
            logger.info(f"Processing paper {i}/{len(papers_data)}: {paper_data.get('source_file', 'unknown')}")
            
            # Insert paper (only json_data for now)
            paper_id = db.insert_paper(paper_data)
            
            if paper_id:
                successful_inserts += 1
                logger.info(f"Successfully inserted paper {paper_id} from {paper_data.get('source_file', 'unknown')}")
            else:
                failed_inserts += 1
                logger.error(f"Failed to insert paper from {paper_data.get('source_file', 'unknown')}")
        
        logger.info(f"""
        Processing completed:
        - Total files: {len(papers_data)}
        - Successful inserts: {successful_inserts}
        - Failed inserts: {failed_inserts}
        """)
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
    finally:
        db.close()

def main():
    """Example usage"""
    # Example: process papers from a folder
    folder_path = "/home/nghia-duong/Downloads/schema"  # Default folder
    logger.info(f"Using default folder: {folder_path}")
    
    process_papers_from_folder(folder_path)

if __name__ == "__main__":
    main()