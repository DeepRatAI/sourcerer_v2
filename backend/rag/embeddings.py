import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import hashlib

from ..utils.logging import get_logger


class EmbeddingManager:
    """Manages text embeddings using sentence-transformers"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.logger = get_logger("sourcerer.rag.embeddings")
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 embedding dimension
        self._model_loaded = False
    
    def _load_model(self):
        """Load the embedding model lazily"""
        if self._model_loaded:
            return
        
        try:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self._model_loaded = True
            
            # Get actual embedding dimension
            test_embedding = self.model.encode(["test"])
            self.embedding_dim = test_embedding.shape[1]
            
            self.logger.info(f"Embedding model loaded, dimension: {self.embedding_dim}")
            
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode_text(self, text: str) -> np.ndarray:
        """Encode single text into embedding"""
        self._load_model()
        
        if not text or not text.strip():
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        try:
            # Clean and truncate text
            cleaned_text = self._clean_text(text)
            embedding = self.model.encode([cleaned_text], convert_to_numpy=True)[0]
            return embedding.astype(np.float32)
            
        except Exception as e:
            self.logger.error(f"Failed to encode text: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode multiple texts efficiently"""
        self._load_model()
        
        if not texts:
            return np.empty((0, self.embedding_dim), dtype=np.float32)
        
        try:
            # Clean texts
            cleaned_texts = [self._clean_text(text) for text in texts]
            
            # Process in batches
            embeddings = []
            for i in range(0, len(cleaned_texts), batch_size):
                batch = cleaned_texts[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch, 
                    convert_to_numpy=True,
                    batch_size=batch_size
                )
                embeddings.append(batch_embeddings)
            
            # Concatenate all batches
            all_embeddings = np.vstack(embeddings).astype(np.float32)
            
            self.logger.debug(f"Encoded {len(texts)} texts into embeddings")
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to encode batch: {e}")
            # Return zero embeddings as fallback
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for embedding"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Truncate to reasonable length (models have token limits)
        max_chars = 8000  # Conservative limit
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "..."
        
        return cleaned
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Compute cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(np.clip(similarity, -1.0, 1.0))
            
        except Exception as e:
            self.logger.error(f"Failed to compute similarity: {e}")
            return 0.0
    
    def get_text_hash(self, text: str) -> str:
        """Generate hash for text content"""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def create_embedding_metadata(self, item_id: str, text: str, source_id: str = None) -> Dict[str, Any]:
        """Create metadata for embedding storage"""
        return {
            'item_id': item_id,
            'text_hash': self.get_text_hash(text),
            'source_id': source_id,
            'text_length': len(text),
            'created_at': np.datetime64('now').astype('datetime64[s]').astype(str)
        }