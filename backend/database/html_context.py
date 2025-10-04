import os
import logging
from typing import List, Optional, Tuple
from database.connect import connect, close_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HTMLContextDatabase:
    def __init__(self):
        self.conn = connect()
    
    def close(self):
        """Close database connection"""
        close_connection(self.conn)

    def update_html_context(self, paper_id: str, html_content: str) -> bool:
        """
        Update the html_context field for a paper with the given paper_id
        
        Args:
            paper_id (str): The paper ID (e.g., 'PMC2824534')
            html_content (str): The HTML content to insert
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            # Update query - set html_context for the matching paper_id
            update_query = """
            UPDATE paper 
            SET html_context = %s, updated_at = CURRENT_TIMESTAMP
            WHERE paper_id = %s
            """
            
            cursor.execute(update_query, (html_content, paper_id))
            
            # Check if any row was updated
            rows_affected = cursor.rowcount
            
            self.conn.commit()
            cursor.close()
            
            if rows_affected > 0:
                logger.info(f"✅ Successfully updated html_context for paper_id: {paper_id}")
                return True
            else:
                logger.warning(f"⚠️  No paper found with paper_id: {paper_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating html_context for {paper_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def get_papers_without_html_context(self) -> List[str]:
        """
        Get list of paper_ids that don't have html_context set
        
        Returns:
            List[str]: List of paper IDs without html_context
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
            SELECT paper_id 
            FROM paper 
            WHERE html_context IS NULL OR html_context = ''
            ORDER BY paper_id
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            paper_ids = [row[0] for row in results]
            logger.info(f"Found {len(paper_ids)} papers without html_context")
            return paper_ids
            
        except Exception as e:
            logger.error(f"Error getting papers without html_context: {e}")
            return []

    def check_paper_exists(self, paper_id: str) -> bool:
        """
        Check if a paper with the given paper_id exists in the database
        
        Args:
            paper_id (str): The paper ID to check
            
        Returns:
            bool: True if paper exists, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            query = "SELECT 1 FROM paper WHERE paper_id = %s LIMIT 1"
            cursor.execute(query, (paper_id,))
            result = cursor.fetchone()
            cursor.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking if paper exists: {e}")
            return False

def read_html_file(file_path: str) -> Optional[str]:
    """
    Read the content of an HTML file
    
    Args:
        file_path (str): Path to the HTML file
        
    Returns:
        Optional[str]: File content or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            logger.debug(f"Successfully read file: {file_path}")
            return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

def extract_paper_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract paper ID from filename (e.g., 'PMC2824534.txt' -> 'PMC2824534')
    
    Args:
        filename (str): The filename
        
    Returns:
        Optional[str]: Paper ID or None if invalid format
    """
    if filename.endswith('.txt') and filename.startswith('PMC'):
        return filename[:-4]  # Remove .txt extension
    return None

def process_html_files_from_folder(folder_path: str, limit: Optional[int] = None) -> Tuple[int, int, int]:
    """
    Process all .txt files in the PMC_txt folder and insert their content as html_context
    
    Args:
        folder_path (str): Path to the PMC_txt folder
        limit (Optional[int]): Limit the number of files to process (for testing)
        
    Returns:
        Tuple[int, int, int]: (successful_updates, failed_updates, skipped_files)
    """
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return 0, 0, 0
    
    # Get all .txt files
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    logger.info(f"Found {len(txt_files)} .txt files in {folder_path}")
    
    if limit:
        txt_files = txt_files[:limit]
        logger.info(f"Processing limited to {limit} files")
    
    # Initialize database
    db = HTMLContextDatabase()
    
    successful_updates = 0
    failed_updates = 0
    skipped_files = 0
    
    try:
        for i, filename in enumerate(txt_files, 1):
            logger.info(f"Processing file {i}/{len(txt_files)}: {filename}")
            
            # Extract paper ID from filename
            paper_id = extract_paper_id_from_filename(filename)
            if not paper_id:
                logger.warning(f"⚠️  Skipping file with invalid name format: {filename}")
                skipped_files += 1
                continue
            
            # Check if paper exists in database
            if not db.check_paper_exists(paper_id):
                logger.warning(f"⚠️  Paper {paper_id} not found in database, skipping...")
                skipped_files += 1
                continue
            
            # Read file content
            file_path = os.path.join(folder_path, filename)
            html_content = read_html_file(file_path)
            
            if html_content is None:
                logger.error(f"❌ Failed to read file: {filename}")
                failed_updates += 1
                continue
            
            # Update database
            if db.update_html_context(paper_id, html_content):
                successful_updates += 1
            else:
                failed_updates += 1
                
        logger.info(f"""
        Processing completed:
        - Total files processed: {len(txt_files)}
        - Successful updates: {successful_updates}
        - Failed updates: {failed_updates}
        - Skipped files: {skipped_files}
        """)
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
    finally:
        db.close()
    
    return successful_updates, failed_updates, skipped_files

def update_specific_papers_html_context(folder_path: str, paper_ids: List[str]) -> Tuple[int, int, int]:
    """
    Update html_context for specific paper IDs only
    
    Args:
        folder_path (str): Path to the PMC_txt folder
        paper_ids (List[str]): List of paper IDs to update
        
    Returns:
        Tuple[int, int, int]: (successful_updates, failed_updates, skipped_files)
    """
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return 0, 0, 0
    
    db = HTMLContextDatabase()
    
    successful_updates = 0
    failed_updates = 0
    skipped_files = 0
    
    try:
        for i, paper_id in enumerate(paper_ids, 1):
            logger.info(f"Processing paper {i}/{len(paper_ids)}: {paper_id}")
            
            # Construct filename
            filename = f"{paper_id}.txt"
            file_path = os.path.join(folder_path, filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.warning(f"⚠️  File not found: {filename}")
                skipped_files += 1
                continue
            
            # Read file content
            html_content = read_html_file(file_path)
            
            if html_content is None:
                logger.error(f"❌ Failed to read file: {filename}")
                failed_updates += 1
                continue
            
            # Update database
            if db.update_html_context(paper_id, html_content):
                successful_updates += 1
            else:
                failed_updates += 1
                
        logger.info(f"""
        Processing completed:
        - Total papers: {len(paper_ids)}
        - Successful updates: {successful_updates}
        - Failed updates: {failed_updates}
        - Skipped files: {skipped_files}
        """)
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
    finally:
        db.close()
    
    return successful_updates, failed_updates, skipped_files

def main():
    """Example usage"""
    # Default folder path
    folder_path = "d:/Github Repos/Galaxy-of-Knowledge/backend/database/PMC_txt"
    
    print("HTML Context Insertion Tool")
    print("=" * 50)
    print("Options:")
    print("1. Process all files (be careful with large datasets)")
    print("2. Process first 10 files (for testing)")
    print("3. Process papers without html_context only")
    print("4. Process specific paper IDs")
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == "1":
        # Process all files
        logger.info("Processing all files...")
        process_html_files_from_folder(folder_path)
        
    elif choice == "2":
        # Process first 10 files for testing
        logger.info("Processing first 10 files for testing...")
        process_html_files_from_folder(folder_path, limit=10)
        
    elif choice == "3":
        # Process only papers that don't have html_context
        logger.info("Finding papers without html_context...")
        db = HTMLContextDatabase()
        paper_ids_to_update = db.get_papers_without_html_context()
        db.close()
        
        if paper_ids_to_update:
            logger.info(f"Found {len(paper_ids_to_update)} papers without html_context")
            update_specific_papers_html_context(folder_path, paper_ids_to_update)
        else:
            logger.info("All papers already have html_context set!")
            
    elif choice == "4":
        # Process specific paper IDs
        paper_ids_input = input("Enter paper IDs separated by commas (e.g., PMC2824534,PMC2897429): ").strip()
        if paper_ids_input:
            paper_ids = [pid.strip() for pid in paper_ids_input.split(',')]
            logger.info(f"Processing specific papers: {paper_ids}")
            update_specific_papers_html_context(folder_path, paper_ids)
        else:
            logger.warning("No paper IDs provided")
            
    else:
        logger.warning("Invalid choice")

if __name__ == "__main__":
    main()