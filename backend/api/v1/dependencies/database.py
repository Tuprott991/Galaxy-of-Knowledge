"""
Database dependency for FastAPI
"""
from functools import lru_cache
from typing import AsyncGenerator
import psycopg2
from psycopg2.extras import RealDictCursor

from database.connect import connect


def get_db():
    """Get database connection dependency"""
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def get_db_cursor():
    """Get database cursor dependency"""
    connection = connect()
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        yield cursor
    finally:
        connection.close()


def get_db_connection():
    """Get database connection (alias for connect)"""
    return connect()
