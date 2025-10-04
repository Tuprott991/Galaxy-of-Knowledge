import asyncio
import logging
import os
import time
from dotenv import load_dotenv

from lightrag import LightRAG, QueryParam
from lightrag.llm.zhipu import zhipu_complete
from lightrag.llm.openai import openai_complete, gpt_4o_mini_complete
from lightrag.llm.openai import openai_embed
# from lightrag.llm.ollama import ollama_embedding
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status
import asyncio

load_dotenv()

ROOT_DIR = os.getcwd()

WORKING_DIR = f"{ROOT_DIR}/gok-pg"

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

# AGE
os.environ["AGE_GRAPH_NAME"] = "gok"

os.environ["POSTGRES_HOST"] = os.getenv("DB_HOST", "localhost")
os.environ["POSTGRES_PORT"] = os.getenv("DB_PORT", "5432")
os.environ["POSTGRES_USER"] = os.getenv("DB_USER", "rag")
os.environ["POSTGRES_PASSWORD"] = os.getenv("DB_PASSWORD", "rag")
os.environ["POSTGRES_DATABASE"] = os.getenv("DB_NAME", "rag")

async def initialize_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=gpt_4o_mini_complete,
        llm_model_name="gpt-4o-mini",
        llm_model_max_async=4,
        llm_model_max_token_size=32768,
        enable_llm_cache_for_entity_extract=True,
        embedding_func= openai_embed,
        kv_storage="PGKVStorage",
        doc_status_storage="PGDocStatusStorage",
        graph_storage="PGGraphStorage",
        vector_storage="PGVectorStorage",
        auto_manage_storages_states=False,
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag

rag = None

async def initialize_rag_instance():
    global rag
    if rag is None:
        rag = await initialize_rag()
        logging.info("RAG instance initialized.")
    else:
        logging.info("RAG instance already initialized.")

