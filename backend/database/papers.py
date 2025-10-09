import os
import json
from typing import List, Dict, Any, Optional
import logging
import asyncpg
from database.connect import get_db_pool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaperDatabase:
    """Async Paper Database Operations"""
    
    def __init__(self):
        """Initialize PaperDatabase - pool should be initialized separately"""
        pass
    
    async def close(self):
        """Close database connection - now handled by pool"""
        pass

    async def insert_paper(self, paper_data: Dict[str, Any]) -> Optional[int]:
        """Insert a paper into the database - only json_data, other fields will be filled later"""
        pool = await get_db_pool()
        
        try:
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
            # Note: asyncpg uses $1, $2, etc. instead of %s
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
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
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
            
            # asyncpg handles JSON natively, no need for Json() wrapper
            async with pool.acquire() as conn:
                result = await conn.fetchrow(
                    upsert_query,
                    author_list,     # $1
                    title,           # $2
                    abstract,        # $3
                    paper_id,        # $4
                    cited_by_final,  # $5
                    references_final,# $6
                    full_text,       # $7
                    json.dumps(paper_data)  # $8 - convert to JSON string
                )

            # Get the result and check if it was insert or update
            returned_paper_id = result['paper_id']
            was_inserted = result['inserted']  # True if inserted, False if updated

            # Safe title display
            title_display = title[:50] + "..." if len(title) > 50 else title
            action = "Inserted" if was_inserted else "Updated"
            logger.info(f"{action} paper with ID: {returned_paper_id} - Title: {title_display}")
            return returned_paper_id

        except Exception as e:
            logger.error(f"Error inserting paper: {e}")
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

async def process_papers_from_folder(folder_path: str):
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
            paper_id = await db.insert_paper(paper_data)
            
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
        await db.close()

# get the html_context field from the database base on the paper_id
async def get_html_context_by_paper_id(paper_id: str) -> Optional[str]:
    """Get the html_context field from the database based on the paper_id"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            query = "SELECT html_context FROM paper WHERE paper_id = $1"
            result = await conn.fetchval(query, paper_id)
            
            if result:
                return result
            else:
                logger.info(f"No html_context found for paper_id: {paper_id}")
                return None
    except Exception as e:
        logger.error(f"Error retrieving html_context for paper_id {paper_id}: {e}")
        return None
    
async def get_md_content_by_paper_id(paper_id: str) -> Optional[str]:
    """Get the md_context field from the database based on the paper_id"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            query = "SELECT md_context FROM paper WHERE paper_id = $1"
            result = await conn.fetchval(query, paper_id)
            
            if result:
                return result
            else:
                logger.info(f"No md_context found for paper_id: {paper_id}")
                return None
    except Exception as e:
        logger.error(f"Error retrieving md_context for paper_id {paper_id}: {e}")
        return None

async def get_all_paper_ids() -> List[str]:
    """Get all paper_ids from the database"""
    paper_ids = []
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            query = "SELECT paper_id FROM paper"
            results = await conn.fetch(query)
            paper_ids = [row['paper_id'] for row in results if row['paper_id']]
            
            logger.info(f"Retrieved {len(paper_ids)} paper_ids from database")
            return paper_ids
    except Exception as e:
        logger.error(f"Error retrieving paper_ids: {e}")
        return paper_ids
    


async def main():
    """Example usage"""
    from database.connect import init_db_pool, close_db_pool
    
    # Initialize database pool
    await init_db_pool()
    
    try:
        # Example: process papers from a folder
        folder_path = "/home/nghia-duong/Downloads/PMC_articles_json (2)/PMC_articles_json"  # Default folder
        logger.info(f"Using default folder: {folder_path}")
        
        await process_papers_from_folder(folder_path)
    finally:
        await close_db_pool()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())