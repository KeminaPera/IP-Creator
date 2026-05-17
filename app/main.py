""" 
IP Creator - Main FastAPI Application

Configurable Multi-LLM Localized AI Cartoon IP Video Generation System
"""
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import init_db, close_db, get_db_session
from app.core.llm_manager import llm_manager
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.utils.logger import logger, PerformanceTimer
from app.models.llm_model import LLMConfig
from app.models.ip_asset import IPAsset
from app.models.lora_model import LoRAModel
from app.models.task import TaskRecord

# Import WebSocket components
from app.websocket.instances import ws_manager, redis_listener

# Import API routers
from app.api.v1 import llm_router
from app.api.v1 import auth_router
from app.api.v1 import ip_router
from app.api.v1 import llm_provider_router
from app.api.v1 import dataset_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Manages startup and shutdown events.
    """
    # Startup
    logger.info("Starting IP Creator application...")
    
    # Security check: validate keys
    security_warnings = settings.validate_security_keys()
    if security_warnings:
        for warning in security_warnings:
            logger.warning(warning)
        if not settings.DEBUG:
            logger.error(
                "SECURITY ERROR: Running with default security keys in non-debug mode! "
                "Please configure proper keys in .env file."
            )
            raise RuntimeError("Default security keys detected in production mode")
    
    # Ensure storage directories exist
    settings.ensure_directories()
    
    # Initialize database
    with PerformanceTimer("Database initialization"):
        await init_db()
    logger.info("Database initialized")
    
    # Initialize LLM models
    await llm_manager.initialize_models()
    logger.info("LLM models initialized")
    
    # Start Redis progress listener
    try:
        await redis_listener.start()
        logger.info("Redis progress listener started")
    except Exception as e:
        logger.warning(f"Failed to start Redis listener: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down IP Creator application...")
    
    # Stop Redis listener
    await redis_listener.stop()
    logger.info("Redis progress listener stopped")
    
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Configurable Multi-LLM Localized AI Cartoon IP Video Generation System",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Vue SPA frontend paths
vue_dist_path = Path(__file__).parent.parent / "frontend-vue" / "dist"

# Mount Vue SPA assets (must be before catch-all route)
if vue_dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(vue_dist_path / "assets")), name="vue-assets")
    # Mount provider SVG icons
    providers_path = vue_dist_path / "providers"
    if providers_path.exists():
        app.mount("/providers", StaticFiles(directory=str(providers_path)), name="providers")

# Mount dataset images (for development)
datasets_path = Path(settings.STORAGE_PATH) / "datasets"
if datasets_path.exists():
    app.mount("/datasets", StaticFiles(directory=str(datasets_path)), name="datasets")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from app.api.v1 import llm_router, auth_router, ip_router, task_router, generation_router, lora_router, content_router, system_health, settings_router, dataset_router, ip_feature_router, training_websocket, resource_router

# Include API routers
app.include_router(llm_router.router)
app.include_router(auth_router.router)
app.include_router(ip_router.router)
app.include_router(ip_feature_router.router)
app.include_router(task_router.router)
app.include_router(generation_router.router)
app.include_router(lora_router.router)
app.include_router(llm_provider_router.router)
app.include_router(content_router.router)
app.include_router(system_health.router)
app.include_router(settings_router.router)
app.include_router(dataset_router.router)
app.include_router(resource_router.router)

# Include WebSocket routers
app.include_router(training_websocket.router)

# Register unified exception handlers
register_exception_handlers(app)
logger.info("Unified exception handlers registered")


from app.utils.response import success_response

# Dashboard stats API (for Vue SPA)
@app.get("/api/v1/dashboard/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db_session)):
    """Get dashboard statistics."""
    llm_count_result = await db.execute(select(func.count(LLMConfig.id)))
    llm_count = llm_count_result.scalar()
    
    active_llm_result = await db.execute(
        select(func.count(LLMConfig.id)).where(LLMConfig.is_active == True)
    )
    active_llm_count = active_llm_result.scalar()
    
    ip_count_result = await db.execute(select(func.count(IPAsset.id)))
    ip_count = ip_count_result.scalar()
    
    task_count_result = await db.execute(select(func.count(TaskRecord.id)))
    task_count = task_count_result.scalar()
    
    lora_count_result = await db.execute(select(func.count(LoRAModel.id)))
    lora_count = lora_count_result.scalar()
    
    return success_response(
        data={
            "llm_count": llm_count or 0,
            "active_llm_count": active_llm_count or 0,
            "ip_count": ip_count or 0,
            "task_count": task_count or 0,
            "lora_count": lora_count or 0,
            "version": settings.APP_VERSION,
            "status": "running",
        }
    )


# SPA catch-all route - serve index.html for all non-API routes
@app.get("/{path:path}", response_class=HTMLResponse)
async def serve_spa(path: str):
    """Serve Vue SPA - return index.html for all non-API routes."""
    # Exclude all /api/ paths - they should be handled by API routers
    if path.startswith("api/") or path == "api":
        return JSONResponse(
            {"error": f"API endpoint not found: /{path}"}, 
            status_code=404
        )
    
    index_file = vue_dist_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"error": "Frontend not built. Run 'npm run build' in frontend-vue/"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
