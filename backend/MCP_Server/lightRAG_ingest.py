from MCP_Server.lightRAG_init import initialize_rag
from database.papers import get_all_paper_ids, get_md_content_by_paper_id

import asyncio

rag = None

async def ingest_papers(paper: str, paper_id: str):
    global rag
    if rag is None:
        rag = await initialize_rag()

    await rag.ainsert(paper, ids=paper_id)

if __name__ == "__main__":
    paper_ids = get_all_paper_ids()
    print(f"Total papers to ingest: {len(paper_ids)}")
    
    # Limit to 10 papers per run
    BATCH_SIZE = 10
    paper_ids_batch = paper_ids[:BATCH_SIZE]
    print(f"Processing batch of {len(paper_ids_batch)} papers")

    loop = asyncio.get_event_loop()
    tasks = []

    for pid in paper_ids_batch:
        md_content = get_md_content_by_paper_id(pid)
        if md_content:
            tasks.append(ingest_papers(md_content, pid))
            print(f"Ingesting paper ID: {pid}")
        else:
            print(f"Warning: No markdown content found for paper ID {pid}")

    loop.run_until_complete(asyncio.gather(*tasks))
    print(f"Ingestion completed. Processed {len(tasks)} papers out of {len(paper_ids)} total.")

