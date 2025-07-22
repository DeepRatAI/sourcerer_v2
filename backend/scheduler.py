import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

from .utils.logging import get_logger
from .config import ConfigManager

logger = get_logger("sourcerer.scheduler")
scheduler: AsyncIOScheduler = None


async def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    
    if scheduler and scheduler.running:
        return
    
    scheduler = AsyncIOScheduler()
    
    # Add periodic tasks
    scheduler.add_job(
        cleanup_old_data,
        IntervalTrigger(hours=24),  # Run daily
        id="cleanup_old_data",
        replace_existing=True
    )
    
    scheduler.add_job(
        refresh_model_caches,
        IntervalTrigger(hours=6),  # Run every 6 hours
        id="refresh_model_caches", 
        replace_existing=True
    )
    
    scheduler.add_job(
        ingest_sources,
        IntervalTrigger(minutes=30),  # Run every 30 minutes
        id="ingest_sources",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started")


async def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def cleanup_old_data():
    """Clean up old data files"""
    logger.info("Starting data cleanup")
    
    try:
        from .config.paths import get_cache_dir, get_chats_dir
        import os
        from pathlib import Path
        
        # Clean old research documents (>30 days)
        cache_dir = get_cache_dir()
        cutoff_time = datetime.now() - timedelta(days=30)
        
        if cache_dir.exists():
            for file_path in cache_dir.glob("research_*.json"):
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
                    logger.debug(f"Deleted old research document: {file_path}")
        
        # Archive old chats (>60 days without activity)
        chats_dir = get_chats_dir()
        archives_dir = chats_dir / "archives"
        archives_dir.mkdir(exist_ok=True)
        
        archive_cutoff = datetime.now() - timedelta(days=60)
        
        if chats_dir.exists():
            for chat_dir in chats_dir.iterdir():
                if chat_dir.is_dir() and chat_dir.name != "archives":
                    messages_file = chat_dir / "messages.jsonl"
                    if messages_file.exists():
                        if messages_file.stat().st_mtime < archive_cutoff.timestamp():
                            # Move to archives
                            archive_path = archives_dir / chat_dir.name
                            if not archive_path.exists():
                                chat_dir.rename(archive_path)
                                logger.debug(f"Archived old chat: {chat_dir.name}")
        
        logger.info("Data cleanup completed")
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")


async def refresh_model_caches():
    """Refresh model caches for providers"""
    logger.info("Starting model cache refresh")
    
    try:
        config_manager = ConfigManager()
        
        # Skip if no providers configured
        if not config_manager.config.providers:
            return
        
        from .providers import get_provider_adapter
        from datetime import datetime
        
        for provider_id, provider_config in config_manager.config.providers.items():
            try:
                # Skip if cache is fresh (less than 6 hours old)
                if provider_config.models_cache:
                    age = datetime.now() - provider_config.models_cache.fetched_at
                    if age.total_seconds() < 6 * 3600:  # 6 hours
                        continue
                
                # Refresh models
                api_key = config_manager.get_provider_api_key(provider_id)
                adapter = get_provider_adapter(provider_id, provider_config, api_key)
                
                models = await adapter.list_models()
                
                # Update cache
                from .models.config import ModelsCache
                provider_config.models_cache = ModelsCache(
                    fetched_at=datetime.now(),
                    ids=[model.id for model in models]
                )
                
                logger.info(f"Refreshed {len(models)} models for provider {provider_id}")
                
            except Exception as e:
                logger.warning(f"Failed to refresh models for provider {provider_id}: {e}")
        
        # Save updated config
        config_manager.save_config()
        logger.info("Model cache refresh completed")
        
    except Exception as e:
        logger.error(f"Model cache refresh failed: {e}")


async def ingest_sources():
    """Ingest content from configured sources"""
    logger.info("Starting scheduled source ingestion")
    
    try:
        from .sources.ingestion import IngestionEngine
        
        ingestion_engine = IngestionEngine()
        results = await ingestion_engine.ingest_all_sources()
        
        if results['sources_processed'] > 0:
            logger.info(f"Scheduled ingestion: {results['sources_processed']} sources, {results['items_added']} new items")
        
        if results['errors']:
            logger.warning(f"Ingestion errors: {len(results['errors'])} sources failed")
            for error in results['errors'][:3]:  # Log first 3 errors
                logger.error(error)
        
    except Exception as e:
        logger.error(f"Source ingestion failed: {e}")


def add_source_refresh_job(source_id: str, refresh_interval: int):
    """Add a specific refresh job for a source"""
    if not scheduler:
        return
    
    scheduler.add_job(
        lambda: asyncio.create_task(ingest_single_source(source_id)),
        IntervalTrigger(seconds=refresh_interval),
        id=f"source_refresh_{source_id}",
        replace_existing=True
    )
    logger.info(f"Added refresh job for source {source_id} (interval: {refresh_interval}s)")


def remove_source_refresh_job(source_id: str):
    """Remove refresh job for a source"""
    if not scheduler:
        return
    
    try:
        scheduler.remove_job(f"source_refresh_{source_id}")
        logger.info(f"Removed refresh job for source {source_id}")
    except Exception:
        pass  # Job doesn't exist


async def ingest_single_source(source_id: str):
    """Ingest content from a single source"""
    logger.debug(f"Scheduled ingestion for source: {source_id}")
    
    try:
        from .sources.ingestion import IngestionEngine
        
        ingestion_engine = IngestionEngine()
        items_added = await ingestion_engine.ingest_single_source(source_id)
        
        if items_added > 0:
            logger.info(f"Source {source_id}: {items_added} new items ingested")
            
    except Exception as e:
        logger.error(f"Failed to ingest source {source_id}: {e}")