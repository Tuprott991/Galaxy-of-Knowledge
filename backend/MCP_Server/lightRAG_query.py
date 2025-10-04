from lightRAG_init import initialize_rag
from lightrag import QueryParam

import asyncio

rag = None # Global variable to hold the RAG instance

async def get_answer(query: str, doc_ids: list[str] = None, mode: str = "hybrid",
                     only_need_context: bool = True):
    global rag
    if rag is None:
        rag = await initialize_rag()

    params = QueryParam(mode=mode, only_need_context=only_need_context, ids=doc_ids)

    response = await rag.aquery(query, params)
    return response