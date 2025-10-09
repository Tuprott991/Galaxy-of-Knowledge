import os
import asyncpg
from dotenv import load_dotenv
import logging
from typing import Optional

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool(
    min_size: int = 10,
    max_size: int = 20,
    command_timeout: float = 60.0
) -> asyncpg.Pool:
    """
    Initialize async database connection pool
    
    Args:
        min_size: Minimum number of connections in pool
        max_size: Maximum number of connections in pool
        command_timeout: Command timeout in seconds
        
    Returns:
        asyncpg.Pool instance
    """
    global _pool
    
    if _pool is not None:
        logger.info("Database pool already initialized")
        return _pool
    
    try:
        _pool = await asyncpg.create_pool(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 5432)),
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout
        )
        logger.info(f"Database pool initialized successfully (min={min_size}, max={max_size})")
        return _pool
    except Exception as e:
        logger.error(f"Error initializing database pool: {e}")
        raise


async def get_db_pool() -> asyncpg.Pool:
    """
    Get the database connection pool
    
    Returns:
        asyncpg.Pool instance
        
    Raises:
        RuntimeError if pool not initialized
    """
    global _pool
    
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    
    return _pool


async def close_db_pool():
    """Close the database connection pool"""
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed successfully")


async def get_db_connection() -> asyncpg.Connection:
    """
    Get a connection from the pool
    
    Returns:
        asyncpg.Connection instance
    """
    pool = await get_db_pool()
    return await pool.acquire()


async def release_db_connection(conn: asyncpg.Connection):
    """
    Release a connection back to the pool
    
    Args:
        conn: Connection to release
    """
    pool = await get_db_pool()
    await pool.release(conn)


async def test_connection() -> bool:
    """Test database connection"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            logger.info("Database connection test successful")
            return result == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


# Legacy sync connection for backward compatibility (deprecated)
# Use async functions instead for production
def connect():
    """
    DEPRECATED: Use async functions instead
    Legacy sync connection for backward compatibility only
    """
    import psycopg2
    logger.warning("Using deprecated sync connect(). Please migrate to async connections.")
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT', 5432)
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def close_connection(conn):
    """
    DEPRECATED: Use async functions instead
    Close database connection (legacy sync)
    """
    if conn:
        conn.close()


if __name__ == "__main__":
    import asyncio
    
    async def main():
        await init_db_pool()
        if await test_connection():
            print("Database connection successful!")
        else:
            print("Database connection failed!")
        await close_db_pool()
    
    asyncio.run(main())