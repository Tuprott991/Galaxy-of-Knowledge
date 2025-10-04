from lightRAG_init import initialize_rag

import asyncio

rag = None

async def ingest_papers(paper: str, paper_id: str):
    global rag
    if rag is None:
        rag = await initialize_rag()

    await rag.ainsert(paper, ids=paper_id)

    
if __name__ == "__main__":
    sample_paper = ""