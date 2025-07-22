from fastapi import APIRouter
from .config import router as config_router
from .providers import router as providers_router
from .sources import router as sources_router
from .chat import router as chat_router
from .content import router as content_router
from .export_import import router as export_import_router

router = APIRouter()

# Include all sub-routers
router.include_router(config_router, prefix="/config", tags=["config"])
router.include_router(providers_router, prefix="/providers", tags=["providers"])
router.include_router(sources_router, prefix="/sources", tags=["sources"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(content_router, prefix="/content", tags=["content"])
router.include_router(export_import_router, prefix="/export", tags=["export"])

__all__ = ["router"]