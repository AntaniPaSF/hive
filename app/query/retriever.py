"""
Query/Retrieval Module for HR Data Pipeline

Implements text-based search and retrieval from ChromaDB without embeddings.
Supports keyword search, metadata filtering, and result ranking.

Related:
- Phase 2 (P2): Query & Retrieval Interface
- ChromaDB text-based search capabilities
- Metadata filtering for precise retrieval
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from app.core.config import AppConfig
from app.vectordb.client import ChromaDBClient

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Individual search result from a single chunk."""
    chunk_id: str
    text: str
    score: float  # Relevance score (lower is better for ChromaDB distances)
    metadata: Dict
    
    @property
    def page_number(self) -> Optional[int]:
        """Get page number from metadata."""
        return self.metadata.get('page_number')
    
    @property
    def section_title(self) -> Optional[str]:
        """Get section title from metadata."""
        return self.metadata.get('section_title')
    
    @property
    def source_doc(self) -> Optional[str]:
        """Get source document filename."""
        return self.metadata.get('source_doc')
    
    @property
    def document_id(self) -> Optional[str]:
        """Get document ID."""
        return self.metadata.get('document_id')


@dataclass
class RetrievalResult:
    """Complete retrieval result with multiple chunks."""
    query: str
    results: List[SearchResult]
    total_results: int
    retrieved_at: str
    filters_applied: Optional[Dict]
    
    def get_top_k(self, k: int) -> List[SearchResult]:
        """Get top K results."""
        return self.results[:k]
    
    def filter_by_document(self, document_id: str) -> List[SearchResult]:
        """Filter results by document ID."""
        return [r for r in self.results if r.document_id == document_id]
    
    def filter_by_page(self, page_number: int) -> List[SearchResult]:
        """Filter results by page number."""
        return [r for r in self.results if r.page_number == page_number]
    
    def get_context_window(self, result_index: int = 0, window_size: int = 3) -> List[SearchResult]:
        """
        Get context window around a result (neighboring chunks).
        Useful for expanding context beyond a single chunk.
        """
        if not self.results or result_index >= len(self.results):
            return []
        
        target = self.results[result_index]
        
        # Get all results from same document
        same_doc = [r for r in self.results if r.document_id == target.document_id]
        
        # Sort by chunk index if available
        if same_doc and 'chunk_index' in same_doc[0].metadata:
            same_doc.sort(key=lambda r: r.metadata.get('chunk_index', 0))
        
        # Find target in sorted list
        try:
            target_idx = same_doc.index(target)
            start = max(0, target_idx - window_size)
            end = min(len(same_doc), target_idx + window_size + 1)
            return same_doc[start:end]
        except ValueError:
            return [target]


class Retriever:
    """
    Text-based retriever for HR policy documents.
    
    Uses ChromaDB's built-in text search without embeddings.
    Supports keyword matching, metadata filtering, and result ranking.
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the retriever.
        
        Args:
            config: Application configuration. If None, loads from environment.
        """
        self.config = config or AppConfig.validate()
        self.vectordb = ChromaDBClient(config=self.config)
        logger.info("Retriever initialized (text-based search mode)")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        min_score: Optional[float] = None
    ) -> RetrievalResult:
        """
        Search for relevant chunks using text-based search.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default: 5)
            filters: Metadata filters (e.g., {'source_doc': 'policy.pdf', 'page_number': 5})
            min_score: Minimum relevance score threshold (lower is better)
            
        Returns:
            RetrievalResult with search results and metadata
            
        Example:
            >>> retriever = Retriever()
            >>> results = retriever.search("vacation policy", top_k=3)
            >>> for result in results.results:
            >>>     print(f"Page {result.page_number}: {result.text[:100]}")
        """
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return RetrievalResult(
                query=query,
                results=[],
                total_results=0,
                retrieved_at=datetime.utcnow().isoformat(),
                filters_applied=filters
            )
        
        logger.info(f"Searching for: '{query}' (top_k={top_k}, filters={filters})")
        
        try:
            # Query ChromaDB with text search
            raw_results = self.vectordb.query(
                query_texts=[query],
                n_results=top_k,
                where=filters,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Parse results
            results = self._parse_results(raw_results, min_score)
            
            logger.info(f"Found {len(results)} results for query: '{query}'")
            
            return RetrievalResult(
                query=query,
                results=results,
                total_results=len(results),
                retrieved_at=datetime.utcnow().isoformat(),
                filters_applied=filters
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise
    
    def search_by_document(
        self,
        query: str,
        document_id: str,
        top_k: int = 5
    ) -> RetrievalResult:
        """
        Search within a specific document.
        
        Args:
            query: Search query text
            document_id: Document ID to search within
            top_k: Number of results to return
            
        Returns:
            RetrievalResult filtered to the specified document
        """
        filters = {'document_id': document_id}
        return self.search(query, top_k=top_k, filters=filters)
    
    def search_by_page(
        self,
        query: str,
        page_number: int,
        document_id: Optional[str] = None,
        top_k: int = 5
    ) -> RetrievalResult:
        """
        Search within a specific page.
        
        Args:
            query: Search query text
            page_number: Page number to search within
            document_id: Optional document ID filter
            top_k: Number of results to return
            
        Returns:
            RetrievalResult filtered to the specified page
        """
        filters = {'page_number': page_number}
        if document_id:
            filters['document_id'] = document_id
        
        return self.search(query, top_k=top_k, filters=filters)
    
    def search_by_section(
        self,
        query: str,
        section_title: str,
        top_k: int = 5
    ) -> RetrievalResult:
        """
        Search within a specific section.
        
        Args:
            query: Search query text
            section_title: Section title to search within
            top_k: Number of results to return
            
        Returns:
            RetrievalResult filtered to the specified section
        """
        filters = {'section_title': section_title}
        return self.search(query, top_k=top_k, filters=filters)
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[SearchResult]:
        """
        Retrieve a specific chunk by ID.
        
        Args:
            chunk_id: Unique chunk identifier
            
        Returns:
            SearchResult for the chunk, or None if not found
        """
        try:
            raw_results = self.vectordb.get_by_ids([chunk_id])
            
            if not raw_results['documents']:
                logger.warning(f"Chunk not found: {chunk_id}")
                return None
            
            return SearchResult(
                chunk_id=chunk_id,
                text=raw_results['documents'][0],
                score=0.0,  # No relevance score for direct retrieval
                metadata=raw_results['metadatas'][0]
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            return None
    
    def get_document_chunks(
        self,
        document_id: str,
        page_number: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Get all chunks for a document, optionally filtered by page.
        
        Args:
            document_id: Document ID
            page_number: Optional page number filter
            
        Returns:
            List of SearchResult objects for the document
        """
        # Use empty query to get all chunks matching filters
        filters = {'document_id': document_id}
        if page_number is not None:
            filters['page_number'] = page_number
        
        try:
            # Query with empty string gets all matching metadata
            raw_results = self.vectordb.query(
                query_texts=[""],  # Empty query
                n_results=1000,  # Large number to get all chunks
                where=filters,
                include=['documents', 'metadatas']
            )
            
            results = self._parse_results(raw_results, min_score=None)
            
            # Sort by chunk index if available
            if results and 'chunk_index' in results[0].metadata:
                results.sort(key=lambda r: r.metadata.get('chunk_index', 0))
            
            logger.info(f"Retrieved {len(results)} chunks for document {document_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve document chunks: {e}")
            return []
    
    def multi_query_search(
        self,
        queries: List[str],
        top_k: int = 5,
        merge_strategy: str = 'union'
    ) -> RetrievalResult:
        """
        Search with multiple queries and merge results.
        
        Args:
            queries: List of query strings
            top_k: Number of results per query
            merge_strategy: How to merge results ('union' or 'intersection')
            
        Returns:
            Merged RetrievalResult
        """
        all_results = []
        seen_chunk_ids = set()
        
        for query in queries:
            result = self.search(query, top_k=top_k)
            
            if merge_strategy == 'union':
                # Add all unique results
                for r in result.results:
                    if r.chunk_id not in seen_chunk_ids:
                        all_results.append(r)
                        seen_chunk_ids.add(r.chunk_id)
            elif merge_strategy == 'intersection':
                # Only keep results that appear in all queries
                # (Implementation would need result tracking across queries)
                pass
        
        # Sort by score (best first)
        all_results.sort(key=lambda r: r.score)
        
        return RetrievalResult(
            query=' OR '.join(queries),
            results=all_results[:top_k * len(queries)],
            total_results=len(all_results),
            retrieved_at=datetime.utcnow().isoformat(),
            filters_applied=None
        )
    
    def _parse_results(
        self,
        raw_results: Dict,
        min_score: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Parse ChromaDB query results into SearchResult objects.
        
        Args:
            raw_results: Raw results from ChromaDB query
            min_score: Minimum score threshold (lower is better)
            
        Returns:
            List of SearchResult objects
        """
        results = []
        
        # ChromaDB returns results as lists of lists (one list per query)
        # We only send one query at a time, so we take the first list
        ids = raw_results.get('ids', [[]])[0]
        documents = raw_results.get('documents', [[]])[0]
        metadatas = raw_results.get('metadatas', [[]])[0]
        distances = raw_results.get('distances', [[]])[0]
        
        for i, chunk_id in enumerate(ids):
            score = distances[i] if i < len(distances) else 0.0
            
            # Filter by min_score if provided (lower is better)
            if min_score is not None and score > min_score:
                continue
            
            results.append(SearchResult(
                chunk_id=chunk_id,
                text=documents[i] if i < len(documents) else "",
                score=score,
                metadata=metadatas[i] if i < len(metadatas) else {}
            ))
        
        return results
    
    def get_statistics(self) -> Dict:
        """
        Get retrieval statistics.
        
        Returns:
            Dict with statistics about the collection
        """
        try:
            total_chunks = self.vectordb.count()
            
            return {
                'total_chunks': total_chunks,
                'search_mode': 'text-based',
                'collection_name': self.vectordb.collection_name,
                'db_path': self.config.vector_db_path
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
