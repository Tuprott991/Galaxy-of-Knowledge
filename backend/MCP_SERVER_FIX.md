# MCP Server Database Pool Fix

## Issue
The MCP Server (`sse_server.py`) was throwing this error:
```
ERROR:database.papers:Error retrieving md_context for paper_id PMC4169763: Database pool not initialized. Call init_db_pool() first.
```

## Root Cause
The MCP Server was calling `get_md_content_by_paper_id()` which requires an initialized database connection pool. However, the pool was never initialized when the server started.

## Solution
Added database pool initialization and cleanup to the MCP Server startup/shutdown lifecycle:

### Changes Made to `backend/MCP_Server/sse_server.py`:

1. **Added Imports**:
   ```python
   from database.connect import init_db_pool, close_db_pool
   ```

2. **Added Startup Event Handler**:
   ```python
   async def startup():
       """Initialize database pool on startup"""
       await init_db_pool()
       print("✅ Database pool initialized")
   ```

3. **Added Shutdown Event Handler**:
   ```python
   async def shutdown():
       """Close database pool on shutdown"""
       await close_db_pool()
       print("✅ Database pool closed")
   ```

4. **Registered Event Handlers**:
   ```python
   starlette_app.add_event_handler("startup", startup)
   starlette_app.add_event_handler("shutdown", shutdown)
   ```

## Result
✅ Database pool is now initialized when MCP Server starts
✅ Database pool is properly closed when MCP Server shuts down
✅ All database queries in MCP tools will work correctly

## Testing
Start the MCP Server:
```bash
python backend/MCP_Server/sse_server.py
```

You should see:
```
✅ Database pool initialized
INFO:     Uvicorn running on http://0.0.0.0:8081 (Press CTRL+C to quit)
```

Now when you call the `get_document_content` tool with a paper ID like "PMC4169763", it should work without errors.

## Related Files Fixed
This completes the async migration. All database operations now properly use the connection pool:
- ✅ FastAPI main app (`main.py`) - Pool initialized on startup
- ✅ MCP Server (`sse_server.py`) - Pool initialized on startup
- ✅ Standalone scripts - Use proper async/await patterns
