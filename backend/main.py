"""
Galaxy of Knowledge Backend API
Main entry point for the FastAPI application
"""
import os
import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import HTTPException

# Import routers and async DB
from api.v1.home import router as papers_router
from api.v1.graph import router as graph_router
from api.v1.paper_analysis import router as paper_analysis_router
from database.connect import init_db_pool, close_db_pool, test_connection


# ======================
# ===== Logging setup ===
# ======================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("backend.main")

# ======================
# ===== FastAPI app ====
# ======================
app = FastAPI(
    title="Galaxy of Knowledge API",
    description="Research paper knowledge graph and visualization API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ======================
# ===== CORS setup =====
# ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://galaxy-of-knowledge-eta.vercel.app",  # Production frontend
        "http://localhost:5173",  # Local Vite dev server
        "http://localhost:3000",  # Alternative local dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# ===== Health check ===
# ======================
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if await test_connection():
            db_status = "connected"
        else:
            db_status = "failed"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "service": "Galaxy of Knowledge API",
        "version": "1.0.0",
        "database": db_status
    }

# ======================
# ===== Routers ========
# ======================
app.include_router(papers_router, prefix="/api/v1", tags=["papers"])
app.include_router(graph_router, prefix="/api/v1", tags=["graph"])
app.include_router(paper_analysis_router, prefix="/api/v1", tags=["paper-analysis"])

# ======================
# === ADK Agent Proxy ==
# ======================
ADK_AGENT_URL = os.getenv("ADK_AGENT_URL", "http://localhost:8082")

@app.api_route("/apps/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_to_adk(path: str, request: Request):
    """Proxy requests to ADK Agent running on port 8082"""
    try:
        # Build target URL
        target_url = f"{ADK_AGENT_URL}/apps/{path}"
        logger.info(f"Proxying {request.method} request to: {target_url}")
        
        # Get request body if present
        body = await request.body()
        
        # Forward the request to ADK Agent
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']},
                content=body,
                params=request.query_params
            )
            
            logger.info(f"ADK Agent response status: {response.status_code}")
            
            # Return the response
            return JSONResponse(
                content=response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except httpx.ConnectError as e:
        logger.error(f"Cannot connect to ADK Agent at {ADK_AGENT_URL}: {e}")
        raise HTTPException(status_code=503, detail=f"ADK Agent is not running at {ADK_AGENT_URL}")
    except httpx.RequestError as e:
        logger.error(f"Error proxying to ADK Agent: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to connect to ADK Agent: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in ADK proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_sse")
async def proxy_run_sse(request: Request):
    """Proxy SSE streaming requests to ADK Agent"""
    logger.info(f"Starting SSE proxy to {ADK_AGENT_URL}/run_sse")
    
    try:
        body = await request.body()
        logger.info(f"Received SSE request body length: {len(body)}")
        
        async def stream_proxy():
            """Generator to proxy SSE events"""
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    logger.info("Opening SSE stream to ADK Agent...")
                    async with client.stream(
                        method="POST",
                        url=f"{ADK_AGENT_URL}/run_sse",
                        headers={
                            "Content-Type": request.headers.get("content-type", "application/json"),
                            "Accept": "text/event-stream",
                        },
                        content=body
                    ) as response:
                        logger.info(f"SSE stream opened, status: {response.status_code}")
                        # Stream the response line by line
                        async for chunk in response.aiter_text():
                            logger.debug(f"SSE chunk: {chunk[:100]}...")  # Log first 100 chars
                            yield chunk
                logger.info("SSE stream completed")
            except httpx.ConnectError as e:
                logger.error(f"Cannot connect to ADK Agent for SSE: {e}")
                yield f"data: {{\"error\": \"ADK Agent not running at {ADK_AGENT_URL}\"}}\n\n"
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        
        # Return streaming response with proper SSE headers
        return StreamingResponse(
            stream_proxy(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    except Exception as e:
        logger.error(f"Error proxying SSE to ADK Agent: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to connect to ADK Agent: {str(e)}")

# ======================
# === Exception Handler
# ======================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "An error occurred"
        }
    )

# ======================
# ===== Events =========
# ======================
@app.on_event("startup")
async def startup_event():
    """Application startup - Initialize async database pool"""
    logger.info("Galaxy of Knowledge API starting up...")
    try:
        # Initialize async connection pool
        await init_db_pool(min_size=10, max_size=20)
        logger.info("✅ Database connection pool initialized")
        
        # Test connection
        if await test_connection():
            logger.info("✅ Database connection test successful")
        else:
            logger.error("❌ Database connection test failed")
    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown - Close async database pool"""
    logger.info("Galaxy of Knowledge API shutting down...")
    try:
        await close_db_pool()
        logger.info("✅ Database connection pool closed")
    except Exception as e:
        logger.error(f"Error closing database pool: {e}")

# ======================
# ===== Entry point ====
# ======================
def main():
    """Main function to run the application"""
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Docs available at: http://{host}:{port}/docs")

    uvicorn.run(
        "backend.main:app",   # ✅ MUST include package path
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info"
    )


if __name__ == "__main__":
    main()
