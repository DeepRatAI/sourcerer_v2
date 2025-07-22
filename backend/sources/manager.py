import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path

from ..config.paths import get_sources_dir
from ..models.source import Source, SourceItem, SourceType, SourceStatus
from ..utils.file_utils import safe_write_json, safe_read_json, ensure_directory
from ..utils.logging import get_logger
from .parsers import RSSParser, HTMLParser


class SourceManager:
    """Manages content sources and their persistence"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.sources.manager")
        self.sources_dir = get_sources_dir()
        ensure_directory(self.sources_dir)
        self.sources_file = self.sources_dir / "sources.json"
        self._sources: Dict[str, Source] = {}
        self._load_sources()
    
    def _load_sources(self) -> None:
        """Load sources from disk"""
        try:
            data = safe_read_json(self.sources_file)
            if data and 'sources' in data:
                for source_data in data['sources']:
                    source = Source(**source_data)
                    self._sources[source.id] = source
                
                self.logger.info(f"Loaded {len(self._sources)} sources")
            else:
                self.logger.info("No sources file found, starting with empty sources")
        except Exception as e:
            self.logger.error(f"Failed to load sources: {e}")
            self._sources = {}
    
    def _save_sources(self) -> None:
        """Save sources to disk"""
        try:
            sources_data = {
                'version': 1,
                'updated_at': datetime.now().isoformat(),
                'sources': [source.model_dump() for source in self._sources.values()]
            }
            safe_write_json(sources_data, self.sources_file)
            self.logger.debug(f"Saved {len(self._sources)} sources")
        except Exception as e:
            self.logger.error(f"Failed to save sources: {e}")
            raise
    
    def add_source(self, source: Source) -> Source:
        """Add a new source"""
        if source.id in self._sources:
            raise ValueError(f"Source with ID {source.id} already exists")
        
        # Set timestamps
        source.created_at = datetime.now()
        source.updated_at = datetime.now()
        
        self._sources[source.id] = source
        self._save_sources()
        
        # Register with scheduler
        from ..scheduler import add_source_refresh_job
        add_source_refresh_job(source.id, source.refresh_interval_sec)
        
        self.logger.info(f"Added source: {source.id} ({source.alias})")
        return source
    
    def update_source(self, source_id: str, updates: Dict[str, Any]) -> Source:
        """Update existing source"""
        if source_id not in self._sources:
            raise ValueError(f"Source {source_id} not found")
        
        source = self._sources[source_id]
        
        # Update fields
        for field, value in updates.items():
            if hasattr(source, field) and field not in ['id', 'created_at']:
                setattr(source, field, value)
        
        source.updated_at = datetime.now()
        self._save_sources()
        
        # Update scheduler if interval changed
        if 'refresh_interval_sec' in updates:
            from ..scheduler import add_source_refresh_job
            add_source_refresh_job(source.id, source.refresh_interval_sec)
        
        self.logger.info(f"Updated source: {source_id}")
        return source
    
    def delete_source(self, source_id: str) -> None:
        """Delete a source"""
        if source_id not in self._sources:
            raise ValueError(f"Source {source_id} not found")
        
        # Remove from scheduler
        from ..scheduler import remove_source_refresh_job
        remove_source_refresh_job(source_id)
        
        # Remove from memory and save
        source = self._sources.pop(source_id)
        self._save_sources()
        
        self.logger.info(f"Deleted source: {source_id} ({source.alias})")
    
    def get_source(self, source_id: str) -> Optional[Source]:
        """Get source by ID"""
        return self._sources.get(source_id)
    
    def list_sources(self) -> List[Source]:
        """Get all sources"""
        return list(self._sources.values())
    
    def get_sources_for_refresh(self) -> List[Source]:
        """Get sources that need refreshing"""
        now = datetime.now()
        sources_to_refresh = []
        
        for source in self._sources.values():
            if source.status != SourceStatus.ACTIVE:
                continue
            
            if source.last_fetch is None:
                # Never fetched before
                sources_to_refresh.append(source)
            else:
                # Check if enough time has passed
                time_since_fetch = now - source.last_fetch
                if time_since_fetch.total_seconds() >= source.refresh_interval_sec:
                    sources_to_refresh.append(source)
        
        return sources_to_refresh
    
    async def refresh_source(self, source_id: str, force: bool = False) -> int:
        """Refresh a specific source"""
        source = self.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        if source.status != SourceStatus.ACTIVE and not force:
            self.logger.warning(f"Source {source_id} is not active, skipping refresh")
            return 0
        
        try:
            self.logger.info(f"Refreshing source: {source_id} ({source.alias})")
            
            # Create appropriate parser
            parser = self._create_parser(source)
            
            # Parse content
            new_items = await parser.parse(source.url, source.headers)
            
            # Update source with new items
            existing_ids = {item.id for item in source.items}
            added_count = 0
            
            for item in new_items:
                if item.id not in existing_ids:
                    source.items.append(item)
                    added_count += 1
            
            # Limit number of items
            if len(source.items) > source.max_items:
                # Keep most recent items
                source.items.sort(key=lambda x: x.published_at, reverse=True)
                source.items = source.items[:source.max_items]
            
            # Update source metadata
            source.last_fetch = datetime.now()
            source.fail_count = 0
            source.status = SourceStatus.ACTIVE
            
            self._save_sources()
            
            self.logger.info(f"Successfully refreshed source {source_id}: {added_count} new items")
            return added_count
            
        except Exception as e:
            # Handle failure
            source.fail_count += 1
            source.last_fetch = datetime.now()
            
            if source.fail_count >= 3:
                source.status = SourceStatus.ERROR
                self.logger.error(f"Source {source_id} marked as error after {source.fail_count} failures")
            
            self._save_sources()
            
            self.logger.error(f"Failed to refresh source {source_id}: {e}")
            raise
    
    def _create_parser(self, source: Source):
        """Create appropriate parser for source type"""
        parser_config = {
            'type': source.type,
            'max_items': source.max_items,
            'selectors': source.selectors
        }
        
        if source.type == SourceType.RSS:
            return RSSParser(parser_config)
        elif source.type == SourceType.HTML:
            return HTMLParser(parser_config)
        else:
            raise ValueError(f"Unsupported source type: {source.type}")
    
    def get_recent_items(self, limit: int = 50) -> List[SourceItem]:
        """Get recent items across all sources"""
        all_items = []
        
        for source in self._sources.values():
            all_items.extend(source.items)
        
        # Sort by published date, most recent first
        all_items.sort(key=lambda x: x.published_at, reverse=True)
        
        return all_items[:limit]
    
    def search_items(self, query: str, source_ids: List[str] = None) -> List[SourceItem]:
        """Search items by text content"""
        query_lower = query.lower()
        matching_items = []
        
        sources_to_search = [self._sources[sid] for sid in (source_ids or self._sources.keys()) if sid in self._sources]
        
        for source in sources_to_search:
            for item in source.items:
                # Search in title, content, and summary
                searchable_text = f"{item.title} {item.content or ''} {item.summary or ''}".lower()
                
                if query_lower in searchable_text:
                    matching_items.append(item)
        
        # Sort by relevance (simple scoring)
        def relevance_score(item):
            score = 0
            text_fields = [item.title, item.content or '', item.summary or '']
            
            for field in text_fields:
                field_lower = field.lower()
                score += field_lower.count(query_lower)
                
                # Bonus for title matches
                if field == item.title and query_lower in field_lower:
                    score += 5
            
            return score
        
        matching_items.sort(key=relevance_score, reverse=True)
        return matching_items
    
    def get_source_stats(self) -> Dict[str, Any]:
        """Get statistics about sources"""
        stats = {
            'total_sources': len(self._sources),
            'active_sources': sum(1 for s in self._sources.values() if s.status == SourceStatus.ACTIVE),
            'error_sources': sum(1 for s in self._sources.values() if s.status == SourceStatus.ERROR),
            'paused_sources': sum(1 for s in self._sources.values() if s.status == SourceStatus.PAUSED),
            'total_items': sum(len(s.items) for s in self._sources.values()),
            'sources_by_type': {}
        }
        
        # Count by type
        for source in self._sources.values():
            source_type = source.type.value
            if source_type not in stats['sources_by_type']:
                stats['sources_by_type'][source_type] = 0
            stats['sources_by_type'][source_type] += 1
        
        return stats