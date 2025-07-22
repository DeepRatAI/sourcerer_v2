from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from ..models.source import SourceItem
from ..utils.logging import get_logger
from .embeddings import EmbeddingManager
from .storage import VectorStore


class RetrievalEngine:
    """Handles retrieval and ranking of relevant content"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.rag.retrieval")
        self.embedding_manager = EmbeddingManager()
        self.vector_store = VectorStore(self.embedding_manager.embedding_dim)
    
    async def retrieve_context(
        self, 
        query: str, 
        max_items: int = 5,
        min_similarity: float = 0.3,
        source_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query"""
        
        if not query or not query.strip():
            return []
        
        try:
            self.logger.debug(f"Retrieving context for query: {query[:100]}...")
            
            # Generate query embedding
            query_embedding = self.embedding_manager.encode_text(query)
            
            # Search vector store
            results = self.vector_store.search(
                query_embedding, 
                k=max_items * 2,  # Get more candidates for filtering
                min_similarity=min_similarity
            )
            
            # Filter by source if specified
            if source_filter:
                results = [r for r in results if r.get('source_id') in source_filter]
            
            # Limit results
            results = results[:max_items]
            
            # Enrich results with full item data
            enriched_results = await self._enrich_results(results)
            
            self.logger.debug(f"Retrieved {len(enriched_results)} relevant contexts")
            return enriched_results
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve context: {e}")
            return []
    
    async def _enrich_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich search results with full item data"""
        enriched = []
        
        for result in results:
            try:
                item_id = result.get('item_id')
                if not item_id:
                    continue
                
                # Get full item data from sources
                item_data = await self._get_item_data(item_id)
                
                if item_data:
                    enriched_result = {
                        'item_id': item_id,
                        'similarity': result.get('similarity', 0.0),
                        'title': item_data.get('title', 'Untitled'),
                        'content': item_data.get('content', ''),
                        'summary': item_data.get('summary', ''),
                        'url': item_data.get('url', ''),
                        'source_id': result.get('source_id'),
                        'published_at': item_data.get('published_at'),
                        'author': item_data.get('author'),
                        'tags': item_data.get('tags', [])
                    }
                    enriched.append(enriched_result)
                    
            except Exception as e:
                self.logger.warning(f"Failed to enrich result {result}: {e}")
                continue
        
        return enriched
    
    async def _get_item_data(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get full item data by ID"""
        try:
            # Import here to avoid circular imports
            from ..sources.manager import SourceManager
            
            source_manager = SourceManager()
            sources = source_manager.list_sources()
            
            # Search through all sources for the item
            for source in sources:
                for item in source.items:
                    if item.id == item_id:
                        return item.model_dump()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get item data for {item_id}: {e}")
            return None
    
    def create_context_prompt(self, 
                            query: str, 
                            retrieved_items: List[Dict[str, Any]], 
                            max_context_length: int = 3000) -> str:
        """Create context prompt from retrieved items"""
        
        if not retrieved_items:
            return ""
        
        context_parts = []
        context_parts.append("Based on the following relevant information:")
        context_parts.append("")
        
        current_length = len("\n".join(context_parts))
        
        for i, item in enumerate(retrieved_items, 1):
            # Create item summary
            item_summary = f"Source {i} (similarity: {item.get('similarity', 0):.2f}):"
            
            if item.get('title'):
                item_summary += f"\nTitle: {item['title']}"
            
            if item.get('url'):
                item_summary += f"\nURL: {item['url']}"
            
            if item.get('author'):
                item_summary += f"\nAuthor: {item['author']}"
            
            # Add content or summary
            content = item.get('content', '') or item.get('summary', '')
            if content:
                # Truncate content if needed
                remaining_space = max_context_length - current_length - len(item_summary) - 100
                if remaining_space > 100:
                    if len(content) > remaining_space:
                        content = content[:remaining_space] + "..."
                    item_summary += f"\nContent: {content}"
            
            item_summary += "\n"
            
            # Check if we have space for this item
            if current_length + len(item_summary) > max_context_length:
                break
            
            context_parts.append(item_summary)
            current_length += len(item_summary)
        
        context_parts.append(f"Query: {query}")
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval engine statistics"""
        vector_stats = self.vector_store.get_stats()
        
        return {
            'vector_store': vector_stats,
            'embedding_model': self.embedding_manager.model_name,
            'embedding_dimension': self.embedding_manager.embedding_dim
        }