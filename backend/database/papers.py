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
            
            # Skip papers without valid PMCID
            if not paper_id or paper_id.strip() == "":
                filename = paper_data.get('_source_filename', 'unknown_file')
                logger.warning(f"⚠️  SKIPPING - Empty PMCID in file: {filename} - Title: {title[:50]}...")
                return None
            
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
            
            # Ensure cited_list is not empty - use None if empty for PostgreSQL
            cited_by_final = cited_list if cited_list else None

            references = []
            references_data = paper_data.get("sections", {}).get("references", [])
            if isinstance(references_data, list):
                for reference in references_data:
                    if isinstance(reference, dict) and "title" in reference:
                        references.append(reference["title"])
                    elif isinstance(reference, str):
                        references.append(reference)
            
            # Ensure references is not empty - use None if empty for PostgreSQL
            references_final = references if references else None

            # full_text - extract ALL content from sections recursively
            sections_data = paper_data.get("sections", {})
            section_contents = []
            
            def extract_content_recursive(data, depth=0):
                """Recursively extract all _content from nested structure"""
                if depth > 10:  # Prevent infinite recursion
                    return
                    
                if isinstance(data, dict):
                    # If this dict has _content, add it
                    if "_content" in data and isinstance(data["_content"], str):
                        content = data["_content"].strip()
                        if content:  # Only add non-empty content
                            section_contents.append(content)
                    
                    # Recursively check all values in the dict
                    for key, value in data.items():
                        if key != "_content":  # Don't re-process _content
                            extract_content_recursive(value, depth + 1)
                            
                elif isinstance(data, list):
                    # Process each item in the list
                    for item in data:
                        extract_content_recursive(item, depth + 1)
            
            if isinstance(sections_data, dict):
                extract_content_recursive(sections_data)
            
            # Combine title with section contents
            full_text = title + "\n\n" + "\n\n".join(section_contents)

            # Insert or update paper using UPSERT (ON CONFLICT DO UPDATE) for duplicates
            upsert_query = """
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
            ON CONFLICT (paper_id) 
            DO UPDATE SET 
                author_list = EXCLUDED.author_list,
                title = EXCLUDED.title,
                abstract = EXCLUDED.abstract,
                cited_by = EXCLUDED.cited_by,
                _references = EXCLUDED._references,
                full_text = EXCLUDED.full_text,
                json_data = EXCLUDED.json_data,
                updated_at = CURRENT_TIMESTAMP
            RETURNING paper_id, (xmax = 0) AS inserted
            """
            
            cursor.execute(upsert_query, (
                author_list,    # author_list column
                title,          # title column  
                abstract,       # abstract column
                paper_id,       # paper_id column
                cited_by_final, # cited_by column - None if empty
                references_final, # references column - None if empty  
                full_text,      # full_text column
                Json(paper_data)  # json_data column
            ))

            # Get the result and check if it was insert or update
            result = cursor.fetchone()
            returned_paper_id = result[0]
            was_inserted = result[1]  # True if inserted, False if updated
            
            self.conn.commit()
            cursor.close()

            # Safe title display
            title_display = title[:50] + "..." if len(title) > 50 else title
            action = "Inserted" if was_inserted else "Updated"
            logger.info(f"{action} paper with ID: {returned_paper_id} - Title: {title_display}")
            return returned_paper_id

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
                data = json.load(file)
                # Add filename to data for tracking
                data['_source_filename'] = filename
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
            # Get title, PMCID and filename for logging
            title = paper_data.get('title', 'Unknown Title')
            pmcid = paper_data.get('PMCID', 'No PMCID')
            filename = paper_data.get('_source_filename', 'unknown_file')
            
            logger.info(f"Processing paper {i}/{len(papers_data)}: {filename} | {pmcid} - {title[:50]}...")
            
            # Insert paper (only json_data for now)
            paper_id = db.insert_paper(paper_data)
            
            if paper_id:
                successful_inserts += 1
                logger.info(f"Successfully inserted paper {paper_id}")
            else:
                failed_inserts += 1
                logger.warning(f"Failed to insert paper from file: {filename} | PMCID: {pmcid}")
        
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

# get the html_context field from the database base on the paper_id
def get_html_context_by_paper_id(paper_id: str) -> Optional[str]:
    """Get the html_context field from the database based on the paper_id"""
    try:
        conn = connect()
        cursor = conn.cursor()
        
        query = "SELECT html_context FROM paper WHERE paper_id = %s"
        cursor.execute(query, (paper_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            return result[0]
        else:
            logger.info(f"No html_context found for paper_id: {paper_id}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving html_context for paper_id {paper_id}: {e}")
        return None

def main():
    """Example usage"""
    # Example: process papers from a folder
    folder_path = "/home/nghia-duong/Downloads/PMC_articles_json (2)/PMC_articles_json"  # Default folder
    logger.info(f"Using default folder: {folder_path}")
    
    process_papers_from_folder(folder_path)

if __name__ == "__main__":
    main()