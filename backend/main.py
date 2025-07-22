import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uuid

from .utils.logging import setup_logger, get_logger, set_request_id, generate_request_id
from .config.paths import get_logs_dir, initialize_directories
from .api import router as api_router
from .models.api import APIResponse, APIError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger = get_logger("sourcerer.main")
    logger.info("Starting Sourcerer application")
    
    # Initialize directories
    initialize_directories()
    
    # Start background tasks (scheduler, etc.)
    from .scheduler import start_scheduler
    await start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sourcerer application")
    from .scheduler import stop_scheduler
    await stop_scheduler()


app = FastAPI(
    title="Sourcerer API",
    description="AI-powered content aggregation and generation system",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add request ID to all requests"""
    request_id = generate_request_id()
    set_request_id(request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger = get_logger("sourcerer.api")
    logger.error(f"Unhandled exception: {exc}")
    
    return APIError(
        error={
            "code": "INTERNAL_ERROR",
            "message": "An internal server error occurred",
            "details": {} if not app.debug else {"exception": str(exc)}
        }
    )


# Mount API routes
app.include_router(api_router, prefix="/api/v1")

# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir / "static"), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(frontend_dir / "index.html")
    
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        # Serve frontend routes (SPA routing)
        return FileResponse(frontend_dir / "index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return APIResponse(data={"status": "healthy", "version": "1.0.0"})


def setup_logging():
    """Setup application logging"""
    logs_dir = get_logs_dir()
    
    # Setup main logger
    setup_logger(
        "sourcerer",
        log_file=logs_dir / "app.log",
        level=20  # INFO
    )
    
    # Setup component loggers
    setup_logger("sourcerer.api", log_file=logs_dir / "app.log")
    setup_logger("sourcerer.config", log_file=logs_dir / "app.log")
    setup_logger("sourcerer.providers", log_file=logs_dir / "inference.log")
    setup_logger("sourcerer.sources", log_file=logs_dir / "app.log")
    setup_logger("sourcerer.generation", log_file=logs_dir / "content_generation.log")
    setup_logger("sourcerer.security", log_file=logs_dir / "security.log")


def cli():
    """CLI entry point"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Sourcerer - AI Content Generation System")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--doctor", action="store_true", help="Run diagnostics")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    if args.doctor:
        # Run diagnostics
        asyncio.run(run_doctor())
        sys.exit(0)
    
    # Set debug mode
    app.debug = args.debug
    
    # Start server
    logger = get_logger("sourcerer.main")
    logger.info(f"Starting server on {args.host}:{args.port}")
    
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=None  # Use our custom logging
    )


async def run_doctor():
    """Run diagnostic tests"""
    logger = get_logger("sourcerer.doctor")
    logger.info("Running Sourcerer diagnostics...")
    
    # Test configuration
    from .config import ConfigManager
    try:
        config_manager = ConfigManager()
        errors = config_manager.validate_config()
        if errors:
            logger.error(f"Configuration errors: {errors}")
        else:
            logger.info("✓ Configuration is valid")
    except Exception as e:
        logger.error(f"✗ Configuration error: {e}")
    
    # Test providers
    if not config_manager.config.providers:
        logger.warning("No providers configured")
    else:
        from .providers import get_provider_adapter
        for provider_id, provider_config in config_manager.config.providers.items():
            try:
                api_key = config_manager.get_provider_api_key(provider_id)
                adapter = get_provider_adapter(provider_id, provider_config, api_key)
                
                if await adapter.test_auth():
                    logger.info(f"✓ Provider {provider_id} authentication successful")
                else:
                    logger.error(f"✗ Provider {provider_id} authentication failed")
            except Exception as e:
                logger.error(f"✗ Provider {provider_id} error: {e}")
    
    # Test directory permissions
    from .config.paths import get_config_dir, get_data_dir
    for directory in [get_config_dir(), get_data_dir()]:
        if directory.exists() and directory.is_dir():
            # Test write permissions
            test_file = directory / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
                logger.info(f"✓ Directory {directory} is writable")
            except Exception as e:
                logger.error(f"✗ Directory {directory} write test failed: {e}")
        else:
            logger.error(f"✗ Directory {directory} does not exist or is not a directory")
    
    logger.info("Diagnostics complete")


if __name__ == "__main__":
    cli()