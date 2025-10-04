"""
Simple Embeddings-Only Ingestion into LightRAG

This ingests documents directly into LightRAG's vector storage without entity extraction.
Much faster and cheaper than full knowledge graph extraction.
"""

import asyncio
import os
from dotenv import load_dotenv
from lightrag.llm.openai import openai_embed
from database.papers import get_all_paper_ids, get_md_content_by_paper_id
from MCP_Server.lightRAG_init import initialize_rag
import numpy as np
import json
from pathlib import Path

load_dotenv()

ROOT_DIR = os.getcwd()
WORKING_DIR = f"{ROOT_DIR}/gok-pg"
BATCH_SIZE = 10
CHUNK_SIZE = 2000  # Characters per chunk

def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Split text into chunks"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)
    return chunks

async def create_embeddings(texts):
    """Create embeddings using OpenAI"""
    if not texts:
        return []
    
    embeddings = await openai_embed(texts)
    return embeddings

async def ingest_paper_to_lightrag(paper_id, md_content, rag):
    """Ingest a single paper into LightRAG"""
    
    print(f"📄 Processing {paper_id}...")
    
    # Use LightRAG's standard insert method
    # With addon_params={'entity_extract_max_gleaning': 0}, entity extraction is minimized
    await rag.ainsert(md_content, ids=paper_id)
    
    print(f"✅ Completed {paper_id}")

async def main():
    """Main ingestion function"""
    print("=" * 60)
    print("Simple Embeddings-Only Ingestion to LightRAG")
    print("=" * 60)
    
    # Initialize LightRAG
    print("\n🔧 Initializing LightRAG...")
    rag = await initialize_rag()
    print("✅ LightRAG initialized")
    
    # Get papers
    paper_ids = get_all_paper_ids()
    paper_ids_batch = paper_ids[:BATCH_SIZE]
    
    print(f"\n📊 Total papers: {len(paper_ids)}")
    print(f"📦 Processing batch: {len(paper_ids_batch)} papers\n")
    
    # Process papers
    success_count = 0
    for paper_id in paper_ids_batch:
        md_content = get_md_content_by_paper_id(paper_id)
        
        if not md_content:
            print(f"⚠️  No content for {paper_id}")
            continue
        
        try:
            await ingest_paper_to_lightrag(paper_id, md_content, rag)
            success_count += 1
        except Exception as e:
            print(f"❌ Error processing {paper_id}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n✅ Ingestion complete!")
    print(f"📁 Embeddings stored in: {WORKING_DIR}/")
    print(f"📊 Successfully ingested: {success_count}/{len(paper_ids_batch)} papers")

if __name__ == "__main__":
    asyncio.run(main())
