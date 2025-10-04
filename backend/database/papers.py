import os
import json
from psycopg2.extras import Json
from typing import List, Dict, Any, Optional
import logging
from database.connect import connect, close_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaperDatabase:
    def __init__(self):
        self.conn = connect()
    
    def close(self):
        """Close database connection"""
        close_connection(self.conn)

    def insert_paper(self, paper_data: Dict[str, Any]) -> Optional[int]:
        """Insert a paper into the database - only json_data, other fields will be filled later"""
        try:
            cursor = self.conn.cursor()
            
            # Extract basic info
            title = paper_data.get("title", "")
            paper_id = paper_data.get("PMCID", "")
            
            # Extract abstract from nested structure
            abstract = None
            sections = paper_data.get("sections", {})
            if sections and isinstance(sections, dict) and "abstract" in sections:
                if isinstance(sections["abstract"], dict) and "_content" in sections["abstract"]:
                    abstract = sections["abstract"]["_content"]
            
            # Extract author names from authors array
            author_list = []
            authors_data = paper_data.get("authors", [])
            if isinstance(authors_data, list):
                for author in authors_data:
                    if isinstance(author, dict) and "name" in author:
                        author_list.append(author["name"])
                    elif isinstance(author, str):
                        author_list.append(author)

            cited_list = []
            cite_data = paper_data.get("cited_by", [])
            if isinstance(cite_data, list):
                for citation in cite_data:
                    if isinstance(citation, dict) and "title" in citation:
                        cited_list.append(citation["title"])
                    elif isinstance(citation, str):
                        cited_list.append(citation)

            references = []
            references_data = paper_data.get("sections", {}).get("references", [])
            if isinstance(references_data, list):
                for reference in references_data:
                    if isinstance(reference, dict) and "title" in reference:
                        references.append(reference["title"])
                    elif isinstance(reference, str):
                        references.append(reference)

            # full_text - extract from sections and get first 6 items
            sections_data = paper_data.get("sections", {})
            section_contents = []
            
            if isinstance(sections_data, dict):
                # Get first 6 sections from the sections dictionary
                section_items = list(sections_data.items())[:6]
                for section_name, section_content in section_items:
                    if isinstance(section_content, dict) and "_content" in section_content:
                        section_contents.append(section_content["_content"])
            
            full_text = "\n\n".join(filter(None, section_contents))

            # Insert paper - let paper_id auto-increment
            insert_query = """
            INSERT INTO paper (
                author_list,
                title,
                abstract,
                paper_id,
                cited_by,
                _references,
                full_text,
                json_data,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING paper_id
            """
            
            cursor.execute(insert_query, (
                author_list,    # author_list column
                title,          # title column  
                abstract,       # abstract column
                paper_id,       # paper_id column
                cited_list,     # cited_by column
                references,     # references column
                full_text,      # full_text column
                Json(paper_data)  # json_data column
            ))

            # Get the auto-generated paper_id
            inserted_paper_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()

            # Safe title display
            title_display = title[:50] + "..." if len(title) > 50 else title
            logger.info(f"Inserted paper with ID: {inserted_paper_id} - Title: {title_display}")
            return inserted_paper_id

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