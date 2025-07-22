import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..utils.logging import get_logger
from .manager import SourceManager


class IngestionEngine:
    """Orchestrates source ingestion and content processing"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.sources.ingestion")
        self.source_manager = SourceManager()
        self.max_concurrent = 5
        
    async def ingest_all_sources(self) -> Dict[str, Any]:
        """Ingest all sources that need refreshing"""
        sources_to_refresh = self.source_manager.get_sources_for_refresh()
        
        if not sources_to_refresh:
            self.logger.info("No sources need refreshing")
            return {
                'sources_processed': 0,
                'items_added': 0,
                'errors': []
            }
        
        self.logger.info(f"Starting ingestion for {len(sources_to_refresh)} sources")
        
        # Process sources with limited concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = []
        
        for source in sources_to_refresh:
            task = self._ingest_source_with_semaphore(semaphore, source.id)
            tasks.append(task)
        
        # Wait for all ingestion tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_items_added = 0
        errors = []
        successful_sources = 0
        
        for i, result in enumerate(results):
            source = sources_to_refresh[i]
            
            if isinstance(result, Exception):
                error_msg = f"Source {source.id}: {str(result)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
            else:
                items_added = result
                total_items_added += items_added
                successful_sources += 1
                self.logger.info(f"Source {source.id}: {items_added} new items")
        
        # Trigger RAG indexing for new items if available
        if total_items_added > 0:
            await self._trigger_rag_indexing()
        
        summary = {
            'sources_processed': successful_sources,
            'items_added': total_items_added,
            'errors': errors,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Ingestion complete: {successful_sources} sources, {total_items_added} new items")
        return summary
    
    async def _ingest_source_with_semaphore(self, semaphore: asyncio.Semaphore, source_id: str) -> int:
        """Ingest single source with concurrency control"""
        async with semaphore:
            return await self.source_manager.refresh_source(source_id)
    
    async def ingest_single_source(self, source_id: str, force: bool = False) -> int:
        """Ingest a single source"""
        try:
            items_added = await self.source_manager.refresh_source(source_id, force=force)
            
            # Trigger RAG indexing if items were added
            if items_added > 0:
                await self._trigger_rag_indexing(source_ids=[source_id])
            
            return items_added
            
        except Exception as e:
            self.logger.error(f"Failed to ingest source {source_id}: {e}")
            raise
    
    async def _trigger_rag_indexing(self, source_ids: Optional[List[str]] = None):
        """Trigger RAG system to index new content"""
        try:
            # Import here to avoid circular imports
            from ..rag import RAGEngine
            
            rag_engine = RAGEngine()
            
            if source_ids:
                # Index specific sources
                for source_id in source_ids:
                    source = self.source_manager.get_source(source_id)
                    if source:
                        await rag_engine.index_source_items(source.items)
            else:
                # Index recent items from all sources
                recent_items = self.source_manager.get_recent_items(limit=100)
                if recent_items:
                    await rag_engine.index_items(recent_items)
            
            self.logger.info("Triggered RAG indexing for new content")
            
        except ImportError:
            # RAG system not available yet
            self.logger.debug("RAG system not available for indexing")
        except Exception as e:
            self.logger.error(f"Failed to trigger RAG indexing: {e}")
    
    def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current ingestion status"""
        sources = self.source_manager.list_sources()
        stats = self.source_manager.get_source_stats()
        
        # Calculate next refresh times
        next_refreshes = []
        now = datetime.now()
        
        for source in sources:
            if source.status.value == 'active' and source.last_fetch:
                next_refresh = source.last_fetch + timedelta(seconds=source.refresh_interval_sec)
                if next_refresh > now:
                    next_refreshes.append({
                        'source_id': source.id,
                        'source_alias': source.alias,
                        'next_refresh': next_refresh.isoformat(),
                        'minutes_remaining': int((next_refresh - now).total_seconds() / 60)
                    })
        
        # Sort by next refresh time
        next_refreshes.sort(key=lambda x: x['next_refresh'])
        
        return {
            'stats': stats,
            'next_refreshes': next_refreshes[:5],  # Next 5 refreshes
            'sources_needing_refresh': len(self.source_manager.get_sources_for_refresh())
        }