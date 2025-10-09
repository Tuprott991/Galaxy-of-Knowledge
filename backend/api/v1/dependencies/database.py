"""
Database dependency for FastAPI (Async)
"""
from typing import AsyncGenerator
import asyncpg

from database.connect import get_db_pool


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get async database connection dependency"""
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        yield connection


async def get_db_connection() -> asyncpg.Connection:
    """
    Get async database connection from pool
    Note: Caller is responsible for releasing connection
    """
    pool = await get_db_pool()
    return await pool.acquire()
