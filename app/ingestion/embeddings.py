"""
Embedding Generation Module for HR Data Pipeline

Generates vector embeddings for text chunks using sentence-transformers.
Uses all-MiniLM-L6-v2 model (384 dimensions, CPU-optimized).

Related:
- FR-009: Store embeddings with chunks in vector database
- Research: all-MiniLM-L6-v2 chosen for balance of quality/speed (80MB, 5ms/chunk)
- Data Model: embedding_vector (384 floats)
"""

import logging
import numpy as np
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError(
        "sentence-transformers is required. Install with: pip install sentence-transformers>=2.2.0"
    )


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embeddings: List[List[float]]
    model_name: str
    model_version: str
    dimension: int
    total_chunks: int


class EmbeddingGenerator:
    """
    Generate embeddings for text chunks using sentence-transformers.
    
    Uses all-MiniLM-L6-v2 model:
    - 384 dimensions (efficient storage)
    - 80MB model size
    - ~5ms per chunk on CPU
    - 0.78 STS benchmark score
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Sentence transformer model to use (default: all-MiniLM-L6-v2)
            batch_size: Number of chunks to process in each batch (default: 32)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        
        logger.info(f"Loading sentence transformer model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.dimension}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def generate_embeddings(
        self,
        texts: List[str],
        show_progress: bool = True,
        normalize: bool = True
    ) -> EmbeddingResult:
        """
        Generate embeddings for a list of text chunks.
        
        Args:
            texts: List of text strings to embed
            show_progress: Whether to show progress bar (useful for large batches)
            normalize: Whether to L2-normalize embeddings (recommended for cosine similarity)
            
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        if not texts:
            logger.warning("Empty text list provided, returning empty embeddings")
            return EmbeddingResult(
                embeddings=[],
                model_name=self.model_name,
                model_version=self._get_model_version(),
                dimension=self.dimension,
                total_chunks=0
            )
        
        logger.info(f"Generating embeddings for {len(texts)} chunks (batch_size={self.batch_size})")
        
        try:
            # Generate embeddings using sentence-transformers
            embeddings_array = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )
            
            # Convert numpy array to list of lists for ChromaDB compatibility
            embeddings_list = embeddings_array.tolist()
            
            logger.info(f"Successfully generated {len(embeddings_list)} embeddings")
            
            return EmbeddingResult(
                embeddings=embeddings_list,
                model_name=self.model_name,
                model_version=self._get_model_version(),
                dimension=self.dimension,
                total_chunks=len(embeddings_list)
            )
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def generate_single_embedding(self, text: str, normalize: bool = True) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Useful for query embeddings or real-time operations.
        
        Args:
            text: Text string to embed
            normalize: Whether to L2-normalize embedding
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=normalize
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate single embedding: {e}")
            raise
    
    def _get_model_version(self) -> str:
        """
        Get the model version string.
        
        Returns model name if version info not available.
        """
        try:
            # Try to get version from model metadata
            if hasattr(self.model, '__version__'):
                return self.model.__version__
            elif hasattr(self.model, '_model_card_vars'):
                return self.model._model_card_vars.get('version', self.model_name)
            else:
                return self.model_name
        except Exception:
            return self.model_name
    
    def validate_embedding_dimension(self, embedding: List[float]) -> bool:
        """
        Validate that an embedding has the correct dimension.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if dimension matches, False otherwise
        """
        return len(embedding) == self.dimension
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            Dict with model metadata
        """
        return {
            "model_name": self.model_name,
            "model_version": self._get_model_version(),
            "embedding_dimension": self.dimension,
            "batch_size": self.batch_size,
            "max_sequence_length": self.model.max_seq_length if hasattr(self.model, 'max_seq_length') else None
        }
