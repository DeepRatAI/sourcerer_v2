from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import uuid

from ..models.api import APIResponse
from ..models.source import (
    CreateSourceRequest, UpdateSourceRequest, SourceInfo, 
    Source, SourceType, SourceStatus
)
from ..sources.manager import SourceManager
from ..sources.ingestion import IngestionEngine
from ..utils.logging import get_logger
from ..utils.validation import validate_url

router = APIRouter()
logger = get_logger("sourcerer.api.sources")


def get_source_manager() -> SourceManager:
    """Get source manager dependency"""
    return SourceManager()


def get_ingestion_engine() -> IngestionEngine:
    """Get ingestion engine dependency"""
    return IngestionEngine()


@router.get("")
async def list_sources(source_manager: SourceManager = Depends(get_source_manager)):
    """List all configured sources"""
    try:
        sources = source_manager.list_sources()
        
        # Convert to SourceInfo format
        source_infos = []
        for source in sources:
            next_refresh = None
            if source.last_fetch and source.status == SourceStatus.ACTIVE:
                from datetime import timedelta
                next_refresh = source.last_fetch + timedelta(seconds=source.refresh_interval_sec)
            
            source_infos.append(SourceInfo(
                id=source.id,
                alias=source.alias,
                type=source.type,
                status=source.status,
                item_count=len(source.items),
                last_fetch=source.last_fetch,
                fail_count=source.fail_count,
                next_refresh=next_refresh
            ))
        
        return APIResponse(data=source_infos)
        
    except Exception as e:
        logger.error(f"Failed to list sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sources: {e}")


@router.post("")
async def create_source(
    request: CreateSourceRequest,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Create a new source"""
    try:
        # Validation
        if not validate_url(str(request.url)):
            raise ValueError("Invalid URL format")
        
        # Create source object
        source_id = str(uuid.uuid4())[:8]
        source = Source(
            id=source_id,
            alias=request.alias,
            type=request.type,
            url=str(request.url),
            refresh_interval_sec=request.refresh_interval_sec,
            headers=request.headers,
            selectors=request.selectors,
            max_items=request.max_items,
            status=SourceStatus.ACTIVE
        )
        
        # Add source
        created_source = source_manager.add_source(source)
        
        # Trigger initial refresh
        try:
            ingestion_engine = IngestionEngine()
            items_added = await ingestion_engine.ingest_single_source(source_id, force=True)
            
            return APIResponse(data={
                "source": created_source.model_dump(),
                "message": f"Source created successfully",
                "initial_items": items_added
            })
        except Exception as refresh_error:
            logger.warning(f"Initial refresh failed for source {source_id}: {refresh_error}")
            return APIResponse(data={
                "source": created_source.model_dump(),
                "message": "Source created successfully (initial refresh failed)",
                "initial_items": 0,
                "refresh_error": str(refresh_error)
            })
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create source: {e}")


@router.get("/stats")
async def get_source_stats(source_manager: SourceManager = Depends(get_source_manager)):
    """Get source statistics"""
    try:
        stats = source_manager.get_source_stats()
        return APIResponse(data=stats)
    except Exception as e:
        logger.error(f"Failed to get source stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get source stats: {e}")


@router.get("/ingestion-status")
async def get_ingestion_status(ingestion_engine: IngestionEngine = Depends(get_ingestion_engine)):
    """Get ingestion status"""
    try:
        status = ingestion_engine.get_ingestion_status()
        return APIResponse(data=status)
    except Exception as e:
        logger.error(f"Failed to get ingestion status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion status: {e}")


@router.get("/items/recent")
async def get_recent_items(
    limit: int = 20,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Get recent items across all sources"""
    try:
        items = source_manager.get_recent_items(limit=limit)
        return APIResponse(data=[item.model_dump() for item in items])
    except Exception as e:
        logger.error(f"Failed to get recent items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent items: {e}")


@router.get("/items/search")
async def search_items(
    q: str,
    source_ids: Optional[str] = None,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Search items by content"""
    try:
        source_id_list = source_ids.split(',') if source_ids else None
        items = source_manager.search_items(q, source_id_list)
        
        return APIResponse(data={
            "query": q,
            "results": [item.model_dump() for item in items],
            "count": len(items)
        })
    except Exception as e:
        logger.error(f"Failed to search items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search items: {e}")


@router.get("/{source_id}")
async def get_source(
    source_id: str,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Get source details"""
    try:
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        return APIResponse(data=source.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get source: {e}")


@router.put("/{source_id}")
async def update_source(
    source_id: str,
    request: UpdateSourceRequest,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Update source"""
    try:
        # Build updates dict
        updates = {}
        for field, value in request.model_dump(exclude_unset=True).items():
            if value is not None:
                updates[field] = value
        
        # Validate URL if being updated
        if "url" in updates and not validate_url(str(updates["url"])):
            raise ValueError("Invalid URL format")
        
        # Apply updates
        updated_source = source_manager.update_source(source_id, updates)
        
        return APIResponse(data={
            "source": updated_source.model_dump(),
            "message": f"Source {source_id} updated successfully"
        })
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update source: {e}")


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Delete source"""
    try:
        source_manager.delete_source(source_id)
        return APIResponse(data={"message": f"Source {source_id} deleted successfully"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete source: {e}")


@router.post("/{source_id}/refresh")
async def refresh_source(
    source_id: str,
    force: bool = False,
    ingestion_engine: IngestionEngine = Depends(get_ingestion_engine)
):
    """Manually refresh source content"""
    try:
        items_added = await ingestion_engine.ingest_single_source(source_id, force=force)
        
        return APIResponse(data={
            "source_id": source_id,
            "items_added": items_added,
            "message": f"Source refreshed successfully"
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to refresh source: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh source: {e}")


@router.post("/refresh-all")
async def refresh_all_sources(ingestion_engine: IngestionEngine = Depends(get_ingestion_engine)):
    """Refresh all sources that need updating"""
    try:
        results = await ingestion_engine.ingest_all_sources()
        return APIResponse(data=results)
    except Exception as e:
        logger.error(f"Failed to refresh all sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh all sources: {e}")


@router.get("/{source_id}/items")
async def get_source_items(
    source_id: str,
    limit: int = 50,
    source_manager: SourceManager = Depends(get_source_manager)
):
    """Get items from a specific source"""
    try:
        source = source_manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Sort items by published date, most recent first
        items = sorted(source.items, key=lambda x: x.published_at, reverse=True)
        
        return APIResponse(data={
            "source_id": source_id,
            "items": [item.model_dump() for item in items[:limit]],
            "total_items": len(source.items)
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get source items: {e}")