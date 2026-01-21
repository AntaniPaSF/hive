"""Vector store retrieval client for ChromaDB integration."""

import time
from typing import Optional
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from ..schemas.query import RetrievedChunk
from ..utils.errors import (
    VectorStoreUnavailable,
    EmbeddingDimensionMismatch,
    LowConfidenceAnswer,
)
from ..utils.validators import (
    validate_filters,
    validate_embedding_dimension,
    validate_confidence,
)
from ..utils.logger import get_logger
from ..config import get_settings


logger = get_logger(__name__)


class VectorStoreClient:
    """Client for querying ChromaDB vector store.

    Handles connection management, query execution, metadata extraction,
    and confidence calculation for retrieved chunks.
    """

    def __init__(
        self,
        vector_store_url: Optional[str] = None,
        collection_name: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize vector store client.

        Args:
            vector_store_url: ChromaDB API endpoint (defaults to config)
            collection_name: ChromaDB collection name (defaults to config)
            timeout: Query timeout in seconds (defaults to config)
        """
        settings = get_settings()
        self.vector_store_url = vector_store_url or settings.vector_store_url
        self.collection_name = collection_name or settings.vector_store_collection
        self.timeout = timeout or settings.vector_store_timeout
        self.max_retrieved_chunks = settings.max_retrieved_chunks

        logger.info(
            "VectorStoreClient initialized",
            extra={
                "component": "retrieval",
                "event": "client_init",
                "data": {
                    "vector_store_url": self.vector_store_url,
                    "collection": self.collection_name,
                    "timeout": self.timeout,
                },
            },
        )

    def query(
        self,
        query_embedding: list[float],
        max_results: Optional[int] = None,
        source_filter: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """Query vector store for relevant chunks.

        Args:
            query_embedding: 384-dimensional embedding vector for query
            max_results: Maximum number of chunks to retrieve (default from config)
            source_filter: Optional source document name filter
            request_id: Request ID for logging/tracing

        Returns:
            List of RetrievedChunk objects ordered by similarity (highest first)

        Raises:
            VectorStoreUnavailable: ChromaDB connection failed or timeout
            EmbeddingDimensionMismatch: Query embedding not 384-dim
        """
        start_time = time.time()

        # Validate embedding dimension
        validate_embedding_dimension(query_embedding)

        # Build filters
        filters = {}
        if max_results is not None:
            validate_filters({"max_results": max_results})
            max_results = max_results
        else:
            max_results = self.max_retrieved_chunks

        if source_filter:
            validate_filters({"source": source_filter})
            filters["source_doc"] = source_filter

        # Build ChromaDB query request
        query_payload = {
            "query_embeddings": [query_embedding],
            "n_results": max_results,
            "include": ["documents", "metadatas", "distances"],
        }

        if filters:
            query_payload["where"] = filters

        logger.info(
            "Querying vector store",
            extra={
                "component": "retrieval",
                "event": "vector_store_query",
                "request_id": request_id,
                "data": {
                    "collection": self.collection_name,
                    "max_results": max_results,
                    "filters": filters,
                    "embedding_dim": len(query_embedding),
                },
            },
        )

        try:
            # Query ChromaDB API
            response = requests.post(
                f"{self.vector_store_url}/api/v1/collections/{self.collection_name}/query",
                json=query_payload,
                timeout=self.timeout,
            )

            # Handle HTTP errors
            if response.status_code == 404:
                error_msg = f"Collection '{self.collection_name}' not found"
                logger.error(
                    error_msg,
                    extra={
                        "component": "retrieval",
                        "event": "vector_store_error",
                        "request_id": request_id,
                        "error": {"type": "NotFound", "status_code": 404},
                    },
                )
                raise VectorStoreUnavailable(
                    message=error_msg,
                    details={"collection": self.collection_name, "status_code": 404},
                )

            if response.status_code >= 500:
                error_msg = f"Vector store server error: {response.status_code}"
                logger.error(
                    error_msg,
                    extra={
                        "component": "retrieval",
                        "event": "vector_store_error",
                        "request_id": request_id,
                        "error": {
                            "type": "ServerError",
                            "status_code": response.status_code,
                        },
                    },
                )
                raise VectorStoreUnavailable(
                    message=error_msg, details={"status_code": response.status_code}
                )

            response.raise_for_status()
            result = response.json()

        except Timeout:
            error_msg = f"Vector store query timeout after {self.timeout}s"
            logger.error(
                error_msg,
                extra={
                    "component": "retrieval",
                    "event": "vector_store_timeout",
                    "request_id": request_id,
                    "error": {"type": "Timeout", "timeout": self.timeout},
                },
            )
            raise VectorStoreUnavailable(
                message=error_msg, details={"timeout": self.timeout}
            )

        except ConnectionError as e:
            error_msg = f"Failed to connect to vector store: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "component": "retrieval",
                    "event": "vector_store_connection_error",
                    "request_id": request_id,
                    "error": {"type": "ConnectionError", "details": str(e)},
                },
            )
            raise VectorStoreUnavailable(
                message=error_msg, details={"url": self.vector_store_url}
            )

        except RequestException as e:
            error_msg = f"Vector store request failed: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "component": "retrieval",
                    "event": "vector_store_request_error",
                    "request_id": request_id,
                    "error": {"type": "RequestError", "details": str(e)},
                },
            )
            raise VectorStoreUnavailable(message=error_msg, details={"error": str(e)})

        # Parse response and extract chunks
        chunks = self._parse_chromadb_response(result, request_id)

        # Calculate confidence
        confidence = self._calculate_confidence(chunks, request_id)

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Vector store query complete",
            extra={
                "component": "retrieval",
                "event": "query_complete",
                "request_id": request_id,
                "data": {
                    "chunks_retrieved": len(chunks),
                    "confidence": confidence,
                    "elapsed_ms": elapsed_ms,
                },
            },
        )

        return chunks

    def _parse_chromadb_response(
        self, response: dict, request_id: Optional[str] = None
    ) -> list[RetrievedChunk]:
        """Parse ChromaDB response into RetrievedChunk objects.

        Args:
            response: ChromaDB API response JSON
            request_id: Request ID for logging

        Returns:
            List of RetrievedChunk objects with extracted metadata
        """
        chunks = []

        # ChromaDB returns nested arrays: [[chunk1, chunk2, ...]]
        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids):
            content = documents[i] if i < len(documents) else ""
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0

            # Convert distance to similarity score (cosine distance -> similarity)
            # ChromaDB returns cosine distance (lower = more similar)
            # Similarity = 1 - distance
            similarity_score = 1.0 - distance

            # Extract metadata with fallback values
            extracted_metadata = self._extract_metadata(metadata, chunk_id, request_id)

            chunk = RetrievedChunk(
                chunk_id=chunk_id,
                content=content,
                metadata=extracted_metadata,
                similarity_score=similarity_score,
            )
            chunks.append(chunk)

        # Sort by similarity (highest first)
        chunks.sort(key=lambda c: c.similarity_score, reverse=True)

        return chunks

    def _extract_metadata(
        self, chromadb_metadata: dict, chunk_id: str, request_id: Optional[str] = None
    ) -> dict:
        """Extract and validate required metadata fields.

        Args:
            chromadb_metadata: Raw metadata from ChromaDB
            chunk_id: Chunk identifier for logging
            request_id: Request ID for logging

        Returns:
            Dictionary with required metadata fields
        """
        # Required fields from data contract
        document_name = chromadb_metadata.get("source_doc", "Unknown")
        chunk_index = chromadb_metadata.get("chunk_index", 0)

        # Optional fields
        page_number = chromadb_metadata.get("page_number")
        section = chromadb_metadata.get("section_title")
        source_type = chromadb_metadata.get("source_type", "unknown")

        # Validate embedding model (warn if mismatch)
        embedding_model = chromadb_metadata.get("embedding_model")
        if embedding_model != "all-MiniLM-L6-v2":
            logger.warning(
                "Embedding model mismatch in chunk metadata",
                extra={
                    "component": "retrieval",
                    "event": "embedding_model_mismatch",
                    "request_id": request_id,
                    "data": {
                        "chunk_id": chunk_id,
                        "expected": "all-MiniLM-L6-v2",
                        "actual": embedding_model,
                    },
                },
            )

        metadata = {
            "document_name": document_name,
            "chunk_index": chunk_index,
            "source_type": source_type,
        }

        # Add optional fields if present
        if page_number is not None:
            metadata["page_number"] = page_number
        if section:
            metadata["section"] = section

        return metadata

    def _calculate_confidence(
        self, chunks: list[RetrievedChunk], request_id: Optional[str] = None
    ) -> float:
        """Calculate confidence score from retrieved chunks.

        Confidence is the average similarity score across all retrieved chunks.

        Args:
            chunks: List of retrieved chunks
            request_id: Request ID for logging

        Returns:
            Average similarity score (0.0 to 1.0)
        """
        if not chunks:
            logger.warning(
                "No chunks retrieved for confidence calculation",
                extra={
                    "component": "retrieval",
                    "event": "zero_chunks",
                    "request_id": request_id,
                },
            )
            return 0.0

        # Calculate average similarity
        total_similarity = sum(chunk.similarity_score for chunk in chunks)
        confidence = total_similarity / len(chunks)

        # Validate confidence range
        try:
            validate_confidence(confidence, get_settings().min_confidence_threshold)
        except Exception as e:
            # Log but don't fail - let caller decide how to handle low confidence
            logger.warning(
                "Low confidence score",
                extra={
                    "component": "retrieval",
                    "event": "low_confidence",
                    "request_id": request_id,
                    "data": {
                        "confidence": confidence,
                        "threshold": get_settings().min_confidence_threshold,
                        "chunks": len(chunks),
                    },
                },
            )

        return confidence

    def health_check(self) -> dict:
        """Check vector store connectivity and collection status.

        Returns:
            Health status dictionary with connection details
        """
        try:
            response = requests.get(
                f"{self.vector_store_url}/api/v1/heartbeat", timeout=5
            )
            response.raise_for_status()

            return {
                "status": "healthy",
                "vector_store_url": self.vector_store_url,
                "collection": self.collection_name,
                "accessible": True,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "vector_store_url": self.vector_store_url,
                "collection": self.collection_name,
                "accessible": False,
                "error": str(e),
            }
