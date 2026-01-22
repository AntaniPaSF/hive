"""
ChromaDB Client Wrapper

Provides a clean interface to ChromaDB vector database for storing
and querying document chunks with embeddings.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import uuid

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError("chromadb is required. Install with: pip install chromadb==0.4.22")

from app.core.config import AppConfig

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """Wrapper for ChromaDB operations."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize ChromaDB client.
        
        Args:
            config: Application configuration. If None, loads from environment.
        """
        self.config = config or AppConfig.validate()
        self.logger = logger
        
        # Initialize ChromaDB client
        db_path = Path(self.config.vector_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.logger.info(f"Initialized ChromaDB at {db_path}")
        self.collection_name = "hr_policies"
        self.collection = None
    
    def get_or_create_collection(self) -> chromadb.Collection:
        """
        Get existing collection or create new one (text-only, no embeddings).
        
        Returns:
            ChromaDB collection object
        """
        if self.collection is None:
            # Use a dummy embedding function to avoid downloads
            # This allows text storage without actual vector embeddings
            class DummyEmbeddingFunction:
                def __call__(self, input):
                    # Return zero vectors - we're only using text storage
                    return [[0.0] * 384 for _ in input]
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=DummyEmbeddingFunction(),
                metadata={
                    "hnsw:space": "cosine",  # Cosine similarity
                    "hnsw:construction_ef": 100,
                    "hnsw:search_ef": 50,
                    "hnsw:M": 16
                }
            )
            self.logger.info(f"Collection '{self.collection_name}' ready ({self.collection.count()} chunks)")
        
        return self.collection
    
    def add_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        metadatas: List[Dict]
    ):
        """
        Add document chunks to vector database (text-based storage).
        
        Args:
            chunk_ids: List of unique chunk identifiers
            texts: List of chunk text content
            metadatas: List of metadata dicts
        """
        collection = self.get_or_create_collection()
        
        try:
            # Store without embeddings - ChromaDB will use text-based search
            collection.add(
                ids=chunk_ids,
                documents=texts,
                metadatas=metadatas
            )
            self.logger.info(f"Added {len(chunk_ids)} chunks to collection (text-only mode)")
        except Exception as e:
            self.logger.error(f"Failed to add chunks: {e}")
            raise
    
    def query(
        self,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        n_results: int = 5,
        where: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> Dict:
        """
        Query vector database for similar chunks.
        
        Args:
            query_embeddings: Pre-computed query embeddings
            query_texts: Text queries (will compute embeddings)
            n_results: Number of results to return
            where: Metadata filters
            include: Fields to include in results
            
        Returns:
            Query results dict with documents, metadatas, distances
        """
        collection = self.get_or_create_collection()
        
        if include is None:
            include = ['documents', 'metadatas', 'distances']
        
        try:
            if query_embeddings is not None:
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    include=include
                )
            elif query_texts is not None:
                results = collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where,
                    include=include
                )
            else:
                raise ValueError("Must provide either query_embeddings or query_texts")
            
            return results
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise
    
    def get_by_ids(self, ids: List[str]) -> Dict:
        """
        Retrieve specific chunks by ID.
        
        Args:
            ids: List of chunk IDs
            
        Returns:
            Dict with documents and metadatas
        """
        collection = self.get_or_create_collection()
        
        try:
            results = collection.get(
                ids=ids,
                include=['documents', 'metadatas', 'embeddings']
            )
            return results
        except Exception as e:
            self.logger.error(f"Failed to get chunks by ID: {e}")
            raise
    
    def delete_by_ids(self, ids: List[str]):
        """Delete chunks by ID."""
        collection = self.get_or_create_collection()
        
        try:
            collection.delete(ids=ids)
            self.logger.info(f"Deleted {len(ids)} chunks")
        except Exception as e:
            self.logger.error(f"Failed to delete chunks: {e}")
            raise
    
    def count(self) -> int:
        """Get total number of chunks in collection."""
        collection = self.get_or_create_collection()
        return collection.count()
    
    def reset(self):
        """Delete all chunks from collection (use with caution)."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = None
            self.logger.warning(f"Collection '{self.collection_name}' deleted")
        except Exception as e:
            self.logger.error(f"Failed to reset collection: {e}")
            raise
    
    def health_check(self) -> Dict:
        """
        Check vector database health.
        
        Returns:
            Dict with status, chunk count, and collection name
        """
        try:
            collection = self.get_or_create_collection()
            chunk_count = collection.count()
            
            return {
                "status": "healthy",
                "chunk_count": chunk_count,
                "collection_name": self.collection_name,
                "db_path": self.config.vector_db_path
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
