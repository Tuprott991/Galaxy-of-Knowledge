import asyncio
import logging
import os
import time
from dotenv import load_dotenv

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete
from lightrag.llm.openai import openai_embed
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status
import asyncio

load_dotenv()

ROOT_DIR = os.getcwd()

WORKING_DIR = f"{ROOT_DIR}/gok-pg"

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

# Note: PostgreSQL/AGE configuration removed - using file-based storage instead
# This is because Neon doesn't support Apache AGE extension

async def initialize_rag():
    # Simplified configuration: embeddings-focused, minimal graph operations
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=gpt_4o_mini_complete,
        llm_model_name="gpt-4o-mini",
        llm_model_max_async=1,  # Reduce parallel LLM calls
        enable_llm_cache_for_entity_extract=False,  # Disable entity extraction caching
        embedding_func=openai_embed,
        embedding_batch_num=16,  # Process embeddings in batches
        embedding_func_max_async=8,  # Parallel embedding requests
        # File-based storage - no database dependencies
        kv_storage="JsonKVStorage",
        doc_status_storage="JsonDocStatusStorage", 
        vector_storage="NanoVectorDBStorage",  # Vector embeddings storage
        graph_storage="NetworkXStorage",  # Minimal file-based graph (required)
        # Disable entity extraction by setting addon to None or minimal
        addon_params={
            "entity_extract_max_gleaning": 0,  # Disable entity gleaning iterations
        },
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()  # Required for document processing pipeline

    return rag

async def initialize_rag_instance():
    global rag
    if rag is None:
        rag = await initialize_rag()
        logging.info("RAG instance initialized.")
    else:
        logging.info("RAG instance already initialized.")

    return rag

