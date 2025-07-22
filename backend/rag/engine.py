from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from ..models.source import SourceItem
from ..utils.logging import get_logger
from .embeddings import EmbeddingManager
from .storage import VectorStore
from .retrieval import RetrievalEngine


class RAGEngine:
    """Main RAG (Retrieval-Augmented Generation) engine"""
    
    def __init__(self):
        self.logger = get_logger("sourcerer.rag.engine")
        self.embedding_manager = EmbeddingManager()
        self.vector_store = VectorStore(self.embedding_manager.embedding_dim)
        self.retrieval_engine = RetrievalEngine()
        
    async def index_items(self, items: List[SourceItem]):
        """Index a list of source items"""
        if not items:
            return
        
        try:
            self.logger.info(f"Indexing {len(items)} items")
            
            # Prepare texts and metadata
            texts = []
            metadata_list = []
            
            for item in items:
                # Skip if already indexed (check by item ID)
                if self.vector_store.get_embedding_metadata(item.id):
                    self.logger.debug(f"Item {item.id} already indexed, skipping")
                    continue
                
                # Combine title, summary, and content for embedding
                text_parts = []
                
                if item.title:
                    text_parts.append(f"Title: {item.title}")
                
                if item.summary:
                    text_parts.append(f"Summary: {item.summary}")
                
                if item.content:
                    # Limit content length for embedding
                    content = item.content[:5000] if len(item.content) > 5000 else item.content
                    text_parts.append(f"Content: {content}")
                
                combined_text = "\n".join(text_parts)
                
                if not combined_text.strip():
                    self.logger.warning(f"Item {item.id} has no text content, skipping")
                    continue
                
                texts.append(combined_text)
                
                # Create metadata
                metadata = self.embedding_manager.create_embedding_metadata(
                    item_id=item.id,
                    text=combined_text,
                    source_id=item.raw.get('source_id') if item.raw else None
                )
                
                # Add additional item metadata
                metadata.update({
                    'title': item.title,
                    'url': item.url,
                    'published_at': item.published_at.isoformat(),
                    'author': item.author,
                    'tags': item.tags
                })
                
                metadata_list.append(metadata)
            
            if not texts:
                self.logger.info("No new items to index")
                return
            
            # Generate embeddings in batches
            embeddings = self.embedding_manager.encode_batch(texts)
            
            # Store in vector database
            self.vector_store.add_embeddings(embeddings, metadata_list)
            
            self.logger.info(f"Successfully indexed {len(texts)} new items")
            
        except Exception as e:
            self.logger.error(f"Failed to index items: {e}")
            raise
    
    async def index_source_items(self, source_items: List[SourceItem]):
        """Index items from a specific source"""
        return await self.index_items(source_items)
    
    async def update_item_index(self, item: SourceItem):
        """Update index for a single item"""
        try:
            # Prepare text for embedding
            text_parts = []
            
            if item.title:
                text_parts.append(f"Title: {item.title}")
            
            if item.summary:
                text_parts.append(f"Summary: {item.summary}")
            
            if item.content:
                content = item.content[:5000] if len(item.content) > 5000 else item.content
                text_parts.append(f"Content: {content}")
            
            combined_text = "\n".join(text_parts)
            
            if not combined_text.strip():
                self.logger.warning(f"Item {item.id} has no text content")
                return
            
            # Generate embedding
            embedding = self.embedding_manager.encode_text(combined_text)
            
            # Create metadata
            metadata = self.embedding_manager.create_embedding_metadata(
                item_id=item.id,
                text=combined_text,
                source_id=item.raw.get('source_id') if item.raw else None
            )
            
            metadata.update({
                'title': item.title,
                'url': item.url,
                'published_at': item.published_at.isoformat(),
                'author': item.author,
                'tags': item.tags
            })
            
            # Update in vector store
            self.vector_store.update_embedding(item.id, embedding, metadata)
            
            self.logger.debug(f"Updated index for item {item.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update item index: {e}")
    
    async def remove_item_index(self, item_id: str):
        """Remove item from index"""
        try:
            self.vector_store.remove_embedding(item_id)
            self.logger.debug(f"Removed item {item_id} from index")
        except Exception as e:
            self.logger.error(f"Failed to remove item from index: {e}")
    
    async def search_similar_content(self, 
                                   query: str,
                                   max_results: int = 5,
                                   min_similarity: float = 0.3,
                                   source_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for content similar to query"""
        return await self.retrieval_engine.retrieve_context(
            query=query,
            max_items=max_results,
            min_similarity=min_similarity,
            source_filter=source_filter
        )
    
    async def get_context_for_generation(self,
                                       query: str,
                                       max_context_items: int = 5) -> Dict[str, Any]:
        """Get context specifically formatted for content generation"""
        
        try:
            # Retrieve relevant items
            relevant_items = await self.search_similar_content(
                query=query,
                max_results=max_context_items,
                min_similarity=0.2  # Lower threshold for generation context
            )
            
            # Create formatted context
            context_prompt = self.retrieval_engine.create_context_prompt(
                query=query,
                retrieved_items=relevant_items
            )
            
            return {
                'context_prompt': context_prompt,
                'relevant_items': relevant_items,
                'item_count': len(relevant_items),
                'query': query
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get generation context: {e}")
            return {
                'context_prompt': '',
                'relevant_items': [],
                'item_count': 0,
                'query': query
            }
    
    async def bulk_reindex(self, force: bool = False):
        """Reindex all content from sources"""
        try:
            self.logger.info("Starting bulk reindex of all content")
            
            if force:
                # Clear existing index
                self.vector_store._create_new_index()
                self.vector_store._save_index()
            
            # Get all items from sources
            from ..sources.manager import SourceManager
            
            source_manager = SourceManager()
            all_items = []
            
            for source in source_manager.list_sources():
                all_items.extend(source.items)
            
            if all_items:
                await self.index_items(all_items)
                self.logger.info(f"Bulk reindex completed: {len(all_items)} items processed")
            else:
                self.logger.info("No items found for bulk reindex")
            
        except Exception as e:
            self.logger.error(f"Failed to perform bulk reindex: {e}")
            raise
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get comprehensive RAG system statistics"""
        try:
            vector_stats = self.vector_store.get_stats()
            retrieval_stats = self.retrieval_engine.get_retrieval_stats()
            
            return {
                'vector_store': vector_stats,
                'retrieval_engine': retrieval_stats,
                'model_info': {
                    'embedding_model': self.embedding_manager.model_name,
                    'embedding_dimension': self.embedding_manager.embedding_dim,
                    'model_loaded': self.embedding_manager._model_loaded
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get index stats: {e}")
            return {}
    
    async def cleanup_index(self):
        """Clean up deleted embeddings and optimize index"""
        try:
            self.logger.info("Starting index cleanup")
            self.vector_store.cleanup_deleted()
            self.logger.info("Index cleanup completed")
        except Exception as e:
            self.logger.error(f"Failed to cleanup index: {e}")