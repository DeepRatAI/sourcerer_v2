import faiss
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pickle

from ..config.paths import get_memory_dir
from ..utils.file_utils import ensure_directory, safe_write_json, safe_read_json
from ..utils.logging import get_logger


class VectorStore:
    """FAISS-based vector storage for embeddings"""
    
    def __init__(self, dimension: int = 384):
        self.logger = get_logger("sourcerer.rag.storage")
        self.dimension = dimension
        self.memory_dir = get_memory_dir()
        self.vector_dir = self.memory_dir / "vector_store"
        ensure_directory(self.vector_dir)
        
        # Storage files
        self.index_file = self.vector_dir / "faiss_index.bin"
        self.metadata_file = self.vector_dir / "metadata.json"
        self.mapping_file = self.vector_dir / "id_mapping.json"
        
        # FAISS index and metadata
        self.index: Optional[faiss.Index] = None
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self.id_to_faiss: Dict[str, int] = {}  # item_id -> faiss_index
        self.faiss_to_id: Dict[int, str] = {}  # faiss_index -> item_id
        self.next_faiss_id = 0
        
        self._load_index()
    
    def _load_index(self):
        """Load existing index and metadata"""
        try:
            if self.index_file.exists() and self.metadata_file.exists():
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_file))
                
                # Load metadata
                metadata_data = safe_read_json(self.metadata_file)
                if metadata_data:
                    # Convert string keys back to integers
                    self.metadata = {int(k): v for k, v in metadata_data.items()}
                
                # Load ID mappings
                mapping_data = safe_read_json(self.mapping_file)
                if mapping_data:
                    self.id_to_faiss = mapping_data.get('id_to_faiss', {})
                    # Convert string keys to int for reverse mapping
                    faiss_to_id = mapping_data.get('faiss_to_id', {})
                    self.faiss_to_id = {int(k): v for k, v in faiss_to_id.items()}
                    self.next_faiss_id = mapping_data.get('next_faiss_id', 0)
                
                self.logger.info(f"Loaded vector index with {self.index.ntotal} embeddings")
            else:
                # Create new index
                self._create_new_index()
                
        except Exception as e:
            self.logger.error(f"Failed to load vector index: {e}")
            # Create fresh index
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        try:
            # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = {}
            self.id_to_faiss = {}
            self.faiss_to_id = {}
            self.next_faiss_id = 0
            
            self.logger.info(f"Created new vector index with dimension {self.dimension}")
            
        except Exception as e:
            self.logger.error(f"Failed to create vector index: {e}")
            raise
    
    def add_embeddings(self, embeddings: np.ndarray, metadata_list: List[Dict[str, Any]]):
        """Add embeddings to the index"""
        if len(embeddings) != len(metadata_list):
            raise ValueError("Number of embeddings must match number of metadata entries")
        
        if len(embeddings) == 0:
            return
        
        try:
            # Normalize embeddings for cosine similarity
            normalized_embeddings = self._normalize_embeddings(embeddings)
            
            # Add to FAISS index
            start_id = self.next_faiss_id
            self.index.add(normalized_embeddings)
            
            # Store metadata and mappings
            for i, metadata in enumerate(metadata_list):
                faiss_id = start_id + i
                item_id = metadata['item_id']
                
                self.metadata[faiss_id] = metadata
                self.id_to_faiss[item_id] = faiss_id
                self.faiss_to_id[faiss_id] = item_id
                
            self.next_faiss_id += len(embeddings)
            
            # Save to disk
            self._save_index()
            
            self.logger.info(f"Added {len(embeddings)} embeddings to vector store")
            
        except Exception as e:
            self.logger.error(f"Failed to add embeddings: {e}")
            raise
    
    def update_embedding(self, item_id: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """Update existing embedding"""
        if item_id in self.id_to_faiss:
            # Remove old embedding
            self.remove_embedding(item_id)
        
        # Add new embedding
        self.add_embeddings(embedding.reshape(1, -1), [metadata])
    
    def remove_embedding(self, item_id: str):
        """Remove embedding (logical deletion)"""
        if item_id not in self.id_to_faiss:
            return
        
        faiss_id = self.id_to_faiss[item_id]
        
        # Mark as deleted in metadata
        if faiss_id in self.metadata:
            self.metadata[faiss_id]['deleted'] = True
        
        # Remove from mappings
        del self.id_to_faiss[item_id]
        
        self._save_index()
        self.logger.debug(f"Marked embedding {item_id} as deleted")
    
    def search(self, query_embedding: np.ndarray, k: int = 5, min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        if self.index.ntotal == 0:
            return []
        
        try:
            # Normalize query embedding
            normalized_query = self._normalize_embeddings(query_embedding.reshape(1, -1))
            
            # Search in FAISS
            similarities, indices = self.index.search(normalized_query, min(k * 2, self.index.ntotal))
            
            results = []
            for similarity, faiss_id in zip(similarities[0], indices[0]):
                # Skip if below threshold
                if similarity < min_similarity:
                    continue
                
                # Skip if deleted
                if faiss_id in self.metadata:
                    metadata = self.metadata[faiss_id]
                    if metadata.get('deleted', False):
                        continue
                    
                    # Add result
                    result = metadata.copy()
                    result['similarity'] = float(similarity)
                    results.append(result)
                
                # Stop if we have enough results
                if len(results) >= k:
                    break
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search embeddings: {e}")
            return []
    
    def get_embedding_metadata(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for an item"""
        if item_id not in self.id_to_faiss:
            return None
        
        faiss_id = self.id_to_faiss[item_id]
        metadata = self.metadata.get(faiss_id)
        
        if metadata and not metadata.get('deleted', False):
            return metadata
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        total_embeddings = self.index.ntotal if self.index else 0
        active_embeddings = len([m for m in self.metadata.values() if not m.get('deleted', False)])
        deleted_embeddings = len([m for m in self.metadata.values() if m.get('deleted', False)])
        
        return {
            'total_embeddings': total_embeddings,
            'active_embeddings': active_embeddings, 
            'deleted_embeddings': deleted_embeddings,
            'dimension': self.dimension,
            'index_type': type(self.index).__name__ if self.index else None
        }
    
    def cleanup_deleted(self):
        """Remove deleted embeddings and rebuild index"""
        if not self.metadata:
            return
        
        try:
            # Collect active embeddings
            active_items = []
            active_metadata = []
            
            for faiss_id, metadata in self.metadata.items():
                if not metadata.get('deleted', False):
                    item_id = self.faiss_to_id.get(faiss_id)
                    if item_id:
                        active_items.append(item_id)
                        active_metadata.append(metadata)
            
            if not active_items:
                # No active items, create fresh index
                self._create_new_index()
                self._save_index()
                return
            
            # This would require re-computing embeddings, which is expensive
            # For now, just log the cleanup request
            deleted_count = len([m for m in self.metadata.values() if m.get('deleted', False)])
            self.logger.info(f"Cleanup requested: {deleted_count} deleted embeddings marked")
            
            # TODO: Implement full cleanup when needed
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup deleted embeddings: {e}")
    
    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalize embeddings for cosine similarity"""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return embeddings / norms
    
    def _save_index(self):
        """Save index and metadata to disk"""
        try:
            # Save FAISS index
            if self.index:
                faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            safe_write_json(self.metadata, self.metadata_file)
            
            # Save ID mappings
            mapping_data = {
                'id_to_faiss': self.id_to_faiss,
                'faiss_to_id': {str(k): v for k, v in self.faiss_to_id.items()},
                'next_faiss_id': self.next_faiss_id
            }
            safe_write_json(mapping_data, self.mapping_file)
            
            self.logger.debug("Saved vector index to disk")
            
        except Exception as e:
            self.logger.error(f"Failed to save vector index: {e}")
            raise