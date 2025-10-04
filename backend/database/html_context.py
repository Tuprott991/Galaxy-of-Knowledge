import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to import database connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connect import connect, close_connection

def update_html_context_from_pmc_files():
    """
    Scan PMC_txt folder and update html_context field for matching paper_ids
    """
    pmc_folder = Path("/home/nghia-duong/Downloads/PMC_txt")
    
    if not pmc_folder.exists():
        print(f"PMC folder not found: {pmc_folder}")
        return
    
    # Connect to PostgreSQL database
    try:
        conn = connect()
        cursor = conn.cursor()
        
        # Get statistics before update
        cursor.execute("SELECT COUNT(*) FROM paper")
        total_papers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM paper WHERE html_context IS NOT NULL AND html_context != ''")
        papers_with_context = cursor.fetchone()[0]
        
        print(f"Database statistics:")
        print(f"   Total papers in database: {total_papers}")
        print(f"   Papers with html_context: {papers_with_context}")
        
        # Get all txt files in PMC folder
        txt_files = list(pmc_folder.glob("*.txt"))
        print(f"Found {len(txt_files)} files in PMC_txt folder")
        
        matched_count = 0
        updated_count = 0
        error_count = 0
        
        for txt_file in txt_files:
            # Extract filename without extension as paper_id
            paper_id = txt_file.stem  # This will be like "PMC10020673"
            
            try:
                # Check if paper exists in database
                cursor.execute("SELECT id, html_context FROM paper WHERE paper_id = %s", (paper_id,))
                result = cursor.fetchone()
                
                if result:
                    matched_count += 1
                    paper_db_id, current_html_context = result
                    
                    # Read file content
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        file_content = f.read().strip()
                    
                    if file_content and (not current_html_context or current_html_context.strip() == ''):
                        # Update database record
                        cursor.execute(
                            "UPDATE paper SET html_context = %s, updated_at = CURRENT_TIMESTAMP WHERE paper_id = %s",
                            (file_content, paper_id)
                        )
                        updated_count += 1
                        print(f"Updated {paper_id} (size: {len(file_content):,} chars)")
                    elif current_html_context and current_html_context.strip():
                        print(f"Skipped {paper_id} (already has html_context)")
                    else:
                        print(f"Skipped {paper_id} (empty file content)")

            except Exception as e:
                error_count += 1
                print(f"Error processing {paper_id}: {e}")
        
        # Commit changes
        conn.commit()
        
        # Final statistics
        cursor.execute("SELECT COUNT(*) FROM paper WHERE html_context IS NOT NULL AND html_context != ''")
        final_papers_with_context = cursor.fetchone()[0]
        
        print(f"\nUpdate Summary:")
        print(f"   Files processed: {len(txt_files)}")
        print(f"   Papers matched in DB: {matched_count}")
        print(f"   Papers updated: {updated_count}")
        print(f"   Errors: {error_count}")
        print(f"   Papers with html_context (before): {papers_with_context}")
        print(f"   Papers with html_context (after): {final_papers_with_context}")
        print(f"   New papers with context: {final_papers_with_context - papers_with_context}")
        
    except Exception as e:
        print(f"Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
    
    finally:
        if 'conn' in locals():
            close_connection(conn)

if __name__ == "__main__":
    update_html_context_from_pmc_files()