import os
import logging
from typing import List, Optional, Tuple
from database.connect import connect, close_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarkdownContextDatabase:
    def __init__(self):
        self.conn = connect()
    
    def close(self):
        """Close database connection"""
        close_connection(self.conn)

    def update_md_context(self, paper_id: str, md_content: str) -> bool:
        """
        Update the md_context field for a paper with the given paper_id
        
        Args:
            paper_id (str): The paper ID (e.g., 'PMC2824534')
            md_content (str): The Markdown content to insert
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            # Update query - set md_context for the matching paper_id
            update_query = """
            UPDATE paper 
            SET md_context = %s, updated_at = CURRENT_TIMESTAMP
            WHERE paper_id = %s
            """
            
            cursor.execute(update_query, (md_content, paper_id))
            
            # Check if any row was updated
            rows_affected = cursor.rowcount
            
            self.conn.commit()
            cursor.close()
            
            if rows_affected > 0:
                logger.info(f"✅ Successfully updated md_context for paper_id: {paper_id}")
                return True
            else:
                logger.warning(f"⚠️  No paper found with paper_id: {paper_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating md_context for {paper_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def get_papers_without_md_context(self) -> List[str]:
        """
        Get list of paper_ids that don't have md_context set
        
        Returns:
            List[str]: List of paper IDs without md_context
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
            SELECT paper_id 
            FROM paper 
            WHERE md_context IS NULL OR md_context = ''
            ORDER BY paper_id
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            
            paper_ids = [row[0] for row in results]
            logger.info(f"Found {len(paper_ids)} papers without md_context")
            return paper_ids
            
        except Exception as e:
            logger.error(f"Error getting papers without md_context: {e}")
            return []

    def get_papers_with_available_md_files(self, md_folder_path: str) -> List[str]:
        """
        Get list of paper_ids that exist in database and have corresponding .md files
        
        Args:
            md_folder_path (str): Path to the PMC_md folder
            
        Returns:
            List[str]: List of paper IDs that have both database entry and MD file
        """
        try:
            # Get all paper IDs from database
            cursor = self.conn.cursor()
            query = "SELECT paper_id FROM paper ORDER BY paper_id"
            cursor.execute(query)
            db_paper_ids = set(row[0] for row in cursor.fetchall())
            cursor.close()
            
            # Get all available .md files
            if not os.path.exists(md_folder_path):
                logger.error(f"MD folder not found: {md_folder_path}")
                return []
            
            md_files = [f for f in os.listdir(md_folder_path) if f.endswith('.md')]
            file_paper_ids = set()
            
            for filename in md_files:
                paper_id = extract_paper_id_from_filename(filename)
                if paper_id:
                    file_paper_ids.add(paper_id)
            
            # Find intersection (papers that exist in both database and file system)
            available_paper_ids = list(db_paper_ids.intersection(file_paper_ids))
            available_paper_ids.sort()
            
            logger.info(f"Found {len(available_paper_ids)} papers with both database entry and MD file")
            logger.info(f"Database papers: {len(db_paper_ids)}, MD files: {len(file_paper_ids)}")
            
            return available_paper_ids
            
        except Exception as e:
            logger.error(f"Error getting papers with available MD files: {e}")
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

    def get_md_context_status(self) -> dict:
        """
        Get statistics about md_context field in the database
        
        Returns:
            dict: Statistics about md_context status
        """
        try:
            cursor = self.conn.cursor()
            
            # Total papers
            cursor.execute("SELECT COUNT(*) FROM paper")
            total_papers = cursor.fetchone()[0]
            
            # Papers with md_context
            cursor.execute("SELECT COUNT(*) FROM paper WHERE md_context IS NOT NULL AND md_context != ''")
            papers_with_md = cursor.fetchone()[0]
            
            # Papers without md_context
            papers_without_md = total_papers - papers_with_md
            
            cursor.close()
            
            return {
                'total_papers': total_papers,
                'papers_with_md_context': papers_with_md,
                'papers_without_md_context': papers_without_md,
                'completion_percentage': (papers_with_md / total_papers * 100) if total_papers > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting md_context status: {e}")
            return {}

def read_md_file(file_path: str) -> Optional[str]:
    """
    Read the content of a Markdown file
    
    Args:
        file_path (str): Path to the Markdown file
        
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
    Extract paper ID from filename (e.g., 'PMC2824534.md' -> 'PMC2824534')
    
    Args:
        filename (str): The filename
        
    Returns:
        Optional[str]: Paper ID or None if invalid format
    """
    if filename.endswith('.md') and filename.startswith('PMC'):
        return filename[:-3]  # Remove .md extension
    return None

def process_md_files_from_folder(folder_path: str, limit: Optional[int] = None) -> Tuple[int, int, int]:
    """
    Process all .md files in the PMC_md folder and insert their content as md_context
    
    Args:
        folder_path (str): Path to the PMC_md folder
        limit (Optional[int]): Limit the number of files to process (for testing)
        
    Returns:
        Tuple[int, int, int]: (successful_updates, failed_updates, skipped_files)
    """
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return 0, 0, 0
    
    # Get all .md files
    md_files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
    logger.info(f"Found {len(md_files)} .md files in {folder_path}")
    
    if limit:
        md_files = md_files[:limit]
        logger.info(f"Processing limited to {limit} files")
    
    # Initialize database
    db = MarkdownContextDatabase()
    
    successful_updates = 0
    failed_updates = 0
    skipped_files = 0
    
    try:
        for i, filename in enumerate(md_files, 1):
            logger.info(f"Processing file {i}/{len(md_files)}: {filename}")
            
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
            md_content = read_md_file(file_path)
            
            if md_content is None:
                logger.error(f"❌ Failed to read file: {filename}")
                failed_updates += 1
                continue
            
            # Update database
            if db.update_md_context(paper_id, md_content):
                successful_updates += 1
            else:
                failed_updates += 1
                
        logger.info(f"""
        Processing completed:
        - Total files processed: {len(md_files)}
        - Successful updates: {successful_updates}
        - Failed updates: {failed_updates}
        - Skipped files: {skipped_files}
        """)
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
    finally:
        db.close()
    
    return successful_updates, failed_updates, skipped_files

def update_specific_papers_md_context(folder_path: str, paper_ids: List[str]) -> Tuple[int, int, int]:
    """
    Update md_context for specific paper IDs only
    
    Args:
        folder_path (str): Path to the PMC_md folder
        paper_ids (List[str]): List of paper IDs to update
        
    Returns:
        Tuple[int, int, int]: (successful_updates, failed_updates, skipped_files)
    """
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return 0, 0, 0
    
    db = MarkdownContextDatabase()
    
    successful_updates = 0
    failed_updates = 0
    skipped_files = 0
    
    try:
        for i, paper_id in enumerate(paper_ids, 1):
            logger.info(f"Processing paper {i}/{len(paper_ids)}: {paper_id}")
            
            # Construct filename
            filename = f"{paper_id}.md"
            file_path = os.path.join(folder_path, filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.warning(f"⚠️  File not found: {filename}")
                skipped_files += 1
                continue
            
            # Read file content
            md_content = read_md_file(file_path)
            
            if md_content is None:
                logger.error(f"❌ Failed to read file: {filename}")
                failed_updates += 1
                continue
            
            # Update database
            if db.update_md_context(paper_id, md_content):
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

def update_all_available_md_context(folder_path: str, batch_size: int = 100) -> Tuple[int, int, int]:
    """
    Update md_context for all papers that have both database entry and MD file available
    
    Args:
        folder_path (str): Path to the PMC_md folder
        batch_size (int): Number of papers to process in each batch
        
    Returns:
        Tuple[int, int, int]: (successful_updates, failed_updates, skipped_files)
    """
    db = MarkdownContextDatabase()
    
    try:
        # Get all papers with available MD files
        available_papers = db.get_papers_with_available_md_files(folder_path)
        
        if not available_papers:
            logger.warning("No papers found with both database entry and MD file")
            return 0, 0, 0
        
        logger.info(f"Found {len(available_papers)} papers to update")
        
        # Process in batches
        total_successful = 0
        total_failed = 0
        total_skipped = 0
        
        for i in range(0, len(available_papers), batch_size):
            batch = available_papers[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(available_papers) + batch_size - 1)//batch_size}")
            
            successful, failed, skipped = update_specific_papers_md_context(folder_path, batch)
            total_successful += successful
            total_failed += failed
            total_skipped += skipped
        
        logger.info(f"""
        All batches completed:
        - Total papers processed: {len(available_papers)}
        - Total successful updates: {total_successful}
        - Total failed updates: {total_failed}
        - Total skipped files: {total_skipped}
        """)
        
        return total_successful, total_failed, total_skipped
        
    except Exception as e:
        logger.error(f"Error during batch processing: {e}")
        return 0, 0, 0
    finally:
        db.close()

def main():
    """Example usage"""
    # Default folder path
    folder_path = "d:/Github Repos/Galaxy-of-Knowledge/backend/database/PMC_md"
    
    print("Markdown Context Update Tool")
    print("=" * 50)
    
    # Show current status
    db = MarkdownContextDatabase()
    status = db.get_md_context_status()
    db.close()
    
    if status:
        print(f"Current Database Status:")
        print(f"  Total papers: {status['total_papers']}")
        print(f"  Papers with md_context: {status['papers_with_md_context']}")
        print(f"  Papers without md_context: {status['papers_without_md_context']}")
        print(f"  Completion: {status['completion_percentage']:.1f}%")
        print()
    
    print("Options:")
    print("1. Update all available papers (recommended)")
    print("2. Process first 10 files (for testing)")
    print("3. Process papers without md_context only")
    print("4. Process specific paper IDs")
    print("5. Show detailed status")
    
    choice = input("Enter your choice (1-5): ").strip()
    
    if choice == "1":
        # Update all available papers
        logger.info("Updating all papers with available MD files...")
        update_all_available_md_context(folder_path)
        
    elif choice == "2":
        # Process first 10 files for testing
        logger.info("Processing first 10 files for testing...")
        process_md_files_from_folder(folder_path, limit=10)
        
    elif choice == "3":
        # Process only papers that don't have md_context
        logger.info("Finding papers without md_context...")
        db = MarkdownContextDatabase()
        paper_ids_to_update = db.get_papers_without_md_context()
        
        if paper_ids_to_update:
            logger.info(f"Found {len(paper_ids_to_update)} papers without md_context")
            # Filter to only those with available MD files
            available_papers = db.get_papers_with_available_md_files(folder_path)
            papers_to_process = list(set(paper_ids_to_update).intersection(set(available_papers)))
            db.close()
            
            if papers_to_process:
                logger.info(f"Processing {len(papers_to_process)} papers that need md_context and have MD files")
                update_specific_papers_md_context(folder_path, papers_to_process)
            else:
                logger.info("No papers found that need md_context and have available MD files")
        else:
            logger.info("All papers already have md_context set!")
            db.close()
            
    elif choice == "4":
        # Process specific paper IDs
        paper_ids_input = input("Enter paper IDs separated by commas (e.g., PMC2824534,PMC2897429): ").strip()
        if paper_ids_input:
            paper_ids = [pid.strip() for pid in paper_ids_input.split(',')]
            logger.info(f"Processing specific papers: {paper_ids}")
            update_specific_papers_md_context(folder_path, paper_ids)
        else:
            logger.warning("No paper IDs provided")
            
    elif choice == "5":
        # Show detailed status
        db = MarkdownContextDatabase()
        available_papers = db.get_papers_with_available_md_files(folder_path)
        papers_without_md = db.get_papers_without_md_context()
        
        print(f"\nDetailed Status:")
        print(f"  Papers in database: {status['total_papers']}")
        print(f"  Papers with MD files available: {len(available_papers)}")
        print(f"  Papers without md_context: {len(papers_without_md)}")
        
        # Papers that can be updated
        updateable = list(set(papers_without_md).intersection(set(available_papers)))
        print(f"  Papers that can be updated: {len(updateable)}")
        
        if updateable:
            print(f"  Sample papers that can be updated: {updateable[:10]}")
        
        db.close()
            
    else:
        logger.warning("Invalid choice")

if __name__ == "__main__":
    main()