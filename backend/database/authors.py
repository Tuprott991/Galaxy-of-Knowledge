import os
import json
from typing import List, Dict, Any, Optional, Set
import logging
from database.connect import connect, close_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthorDatabase:
    def __init__(self):
        self.conn = connect()
    
    def close(self):
        """Close database connection"""
        close_connection(self.conn)

    def insert_author(self, author_name: str) -> Optional[str]:
        """Insert an author into the database"""
        try:
            cursor = self.conn.cursor()
            
            # Check if author already exists
            cursor.execute("SELECT id FROM author WHERE author_name = %s", (author_name,))
            existing = cursor.fetchone()
            
            if existing:
                logger.info(f"Author '{author_name}' already exists with ID: {existing[0]}")
                cursor.close()
                return existing[0]
            
            # Insert new author
            insert_query = """
            INSERT INTO author (
                author_name,
                corresponding_of,
                writing_of,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            """
            
            cursor.execute(insert_query, (
                author_name,
                [],  # Empty array for corresponding_of
                []   # Empty array for writing_of
            ))
            
            author_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            
            logger.info(f"Inserted author '{author_name}' with ID: {author_id}")
            return author_id
            
        except Exception as e:
            logger.error(f"Error inserting author '{author_name}': {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def insert_authors_batch(self, author_names: List[str]) -> Dict[str, Optional[str]]:
        """Insert multiple authors in batch"""
        results = {}
        
        for author_name in author_names:
            if author_name and author_name.strip():  # Skip empty names
                author_id = self.insert_author(author_name.strip())
                results[author_name] = author_id
            else:
                logger.warning(f"Skipping empty author name")
                results[author_name] = None
        
        return results

    def get_author_by_name(self, author_name: str) -> Optional[Dict[str, Any]]:
        """Get author information by name"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, author_name, corresponding_of, writing_of, created_at, updated_at 
                FROM author 
                WHERE author_name = %s
            """, (author_name,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return {
                    'id': result[0],
                    'author_name': result[1],
                    'corresponding_of': result[2],
                    'writing_of': result[3],
                    'created_at': result[4],
                    'updated_at': result[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting author '{author_name}': {e}")
            return None

    def update_author_papers(self, author_name: str, paper_id: str, is_corresponding: bool = False):
        """Update author's paper lists"""
        try:
            cursor = self.conn.cursor()
            
            if is_corresponding:
                # Add to corresponding_of array
                cursor.execute("""
                    UPDATE author 
                    SET corresponding_of = array_append(corresponding_of, %s),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE author_name = %s 
                    AND NOT (%s = ANY(corresponding_of))
                """, (paper_id, author_name, paper_id))
            
            # Add to writing_of array
            cursor.execute("""
                UPDATE author 
                SET writing_of = array_append(writing_of, %s),
                    updated_at = CURRENT_TIMESTAMP
                WHERE author_name = %s 
                AND NOT (%s = ANY(writing_of))
            """, (paper_id, author_name, paper_id))
            
            self.conn.commit()
            cursor.close()
            
            logger.info(f"Updated author '{author_name}' with paper {paper_id}")
            
        except Exception as e:
            logger.error(f"Error updating author '{author_name}' papers: {e}")
            if self.conn:
                self.conn.rollback()

    def get_all_authors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all authors with pagination"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT id, author_name, corresponding_of, writing_of, created_at, updated_at 
                FROM author 
                ORDER BY author_name
                LIMIT %s
            """, (limit,))
            
            results = cursor.fetchall()
            cursor.close()
            
            authors = []
            for result in results:
                authors.append({
                    'id': result[0],
                    'author_name': result[1],
                    'corresponding_of': result[2],
                    'writing_of': result[3],
                    'created_at': result[4],
                    'updated_at': result[5]
                })
            
            return authors
            
        except Exception as e:
            logger.error(f"Error getting all authors: {e}")
            return []

def process_authors_from_folder(folder_path: str):
    """Main function to extract and insert all authors from JSON files"""
    
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return
    
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    logger.info(f"Found {len(json_files)} JSON files in folder")
    
    if not json_files:
        logger.warning("No JSON files found to process")
        return
    
    # Initialize database
    db = AuthorDatabase()
    
    try:
        total_authors_processed = 0
        successful_inserts = 0
        failed_inserts = 0
        
        print(f"\nProcessing {len(json_files)} JSON files...")
        
        # Process each JSON file
        for i, filename in enumerate(json_files, 1):
            file_path = os.path.join(folder_path, filename)
            logger.info(f"Processing file {i}/{len(json_files)}: {filename}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    
                    # Extract authors from this specific file
                    authors_data = data.get("authors", [])
                    if isinstance(authors_data, list):
                        
                        # Process each author in this file
                        for author in authors_data:
                            author_name = None
                            
                            if isinstance(author, dict) and "name" in author:
                                author_name = author["name"]
                            elif isinstance(author, str):
                                author_name = author
                            
                            if author_name and author_name.strip():
                                total_authors_processed += 1
                                author_id = db.insert_author(author_name.strip())
                                
                                if author_id:
                                    successful_inserts += 1
                                    logger.info(f"Author: {author_name}")
                                else:
                                    failed_inserts += 1
                                    logger.error(f"Failed: {author_name}")
                    
                    else:
                        logger.info(f"  No authors found in {filename}")
                        
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
        
        # Summary
        logger.info(f"""
        Author processing completed:
        - JSON files processed: {len(json_files)}
        - Total authors found: {total_authors_processed}
        - Successful inserts: {successful_inserts}
        - Failed inserts: {failed_inserts}
        """)
        
        print(f"Successfully processed {successful_inserts} authors from {len(json_files)} files")
        
        # Show some examples
        if successful_inserts > 0:
            print("\nSample authors in database:")
            sample_authors = db.get_all_authors(limit=5)
            for author in sample_authors:
                print(f"  - {author['author_name']} (ID: {author['id']})")
        
    except Exception as e:
        logger.error(f"Error during author processing: {e}")
    finally:
        db.close()

def main():
    """Main function - process all authors from JSON folder"""
    
    # Get folder path
    folder_path = "/home/nghia-duong/Downloads/PMC_articles_json (2)/PMC_articles_json"  # Default folder
    logger.info(f"Processing authors from folder: {folder_path}")
    
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return
    
    # Extract and insert all authors
    process_authors_from_folder(folder_path)

if __name__ == "__main__":
    main()
