"""
Galaxy of Knowledge Backend API
Main entry point for the FastAPI application
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
