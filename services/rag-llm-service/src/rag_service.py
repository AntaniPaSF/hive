"""
RAG Service - Main orchestrator for retrieval-augmented generation pipeline.

This module provides the RAGService class that coordinates:
- Query embedding generation
- Vector store retrieval
- LLM answer generation
- Citation extraction and validation
"""

import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from .core.embedding_client import EmbeddingAPIClient
from .core.retrieval import VectorStoreClient
from .core.ollama_client import OllamaClient
from .prompts.qa_prompt import build_qa_prompt
from .prompts.citation_parser import extract_citations
from .schemas.query import Query, Answer, Citation
from .utils.logger import get_logger
from .utils.errors import (
    VectorStoreUnavailable,
    OllamaUnavailable,
    EmbeddingAPIUnavailable,
    NoCitationsFound,
    InvalidQuery,
)
from .config import get_settings

logger = get_logger(__name__)


class RAGService:
    """
    Main RAG service orchestrator.

    Coordinates the complete RAG pipeline:
    1. Query embedding generation
    2. Vector store retrieval
    3. LLM answer generation
    4. Citation extraction and validation

    Handles confidence thresholds and "I don't know" responses.
    """

    def __init__(
        self,
        embedding_client: Optional[EmbeddingAPIClient] = None,
        vector_store_client: Optional[VectorStoreClient] = None,
        ollama_client: Optional[OllamaClient] = None,
        min_confidence: float = 0.5,
    ):
        """
        Initialize RAG service.

        Args:
            embedding_client: Embedding API client (created if None)
            vector_store_client: Vector store client (created if None)
            ollama_client: Ollama LLM client (created if None)
            min_confidence: Minimum confidence threshold for answers
        """
        settings = get_settings()

        self.embedding_client = embedding_client or EmbeddingAPIClient()
        self.vector_store_client = vector_store_client or VectorStoreClient()
        self.ollama_client = ollama_client or OllamaClient()
        self.min_confidence = min_confidence

        logger.info(
            "RAGService initialized",
            extra={
                "component": "rag_service",
                "event": "initialization",
                "data": {
                    "min_confidence": self.min_confidence,
                    "embedding_api": self.embedding_client.base_url,
                    "vector_store": self.vector_store_client.vector_store_url,
                    "ollama_host": self.ollama_client.host,
                },
            },
        )

    def query(
        self,
        question: str,
        filters: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Answer:
        """
        Process a query through the RAG pipeline.

        Args:
            question: User's natural language question
            filters: Optional filters for retrieval (source, max_results)
            request_id: Optional request ID (generated if None)

        Returns:
            Answer object with answer text, citations, and confidence

        Raises:
            InvalidQuery: If question is invalid
            VectorStoreUnavailable: If vector store is unreachable
            OllamaUnavailable: If Ollama is unreachable
            EmbeddingAPIUnavailable: If embedding API is unreachable
        """
        # Generate request ID if not provided
        if request_id is None:
            request_id = (
                f"req_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
            )

        start_time = time.time()

        logger.info(
            "Processing query",
            extra={
                "component": "rag_service",
                "event": "query_start",
                "request_id": request_id,
                "data": {"question": question, "filters": filters},
            },
        )

        try:
            # Step 1: Generate query embedding
            embedding_start = time.time()
            query_embedding = self.embedding_client.embed(
                text=question, request_id=request_id
            )
            embedding_time = (time.time() - embedding_start) * 1000

            logger.info(
                "Query embedding generated",
                extra={
                    "component": "rag_service",
                    "event": "embedding_complete",
                    "request_id": request_id,
                    "data": {
                        "embedding_time_ms": round(embedding_time, 2),
                        "embedding_dimension": len(query_embedding),
                    },
                },
            )

            # Step 2: Retrieve relevant chunks from vector store
            retrieval_start = time.time()
            max_results = filters.get("max_results", 5) if filters else 5
            source_filter = filters.get("source") if filters else None

            retrieved_chunks = self.vector_store_client.query(
                query_embedding=query_embedding,
                max_results=max_results,
                source_filter=source_filter,
                request_id=request_id,
            )
            retrieval_time = (time.time() - retrieval_start) * 1000

            # Calculate confidence from retrieved chunks
            confidence = self._calculate_confidence(retrieved_chunks)

            logger.info(
                "Retrieval complete",
                extra={
                    "component": "rag_service",
                    "event": "retrieval_complete",
                    "request_id": request_id,
                    "data": {
                        "retrieval_time_ms": round(retrieval_time, 2),
                        "chunks_retrieved": len(retrieved_chunks),
                        "confidence": round(confidence, 3),
                    },
                },
            )

            # Step 3: Check confidence threshold
            if confidence < self.min_confidence:
                logger.warning(
                    "Low confidence, returning 'I don't know' response",
                    extra={
                        "component": "rag_service",
                        "event": "low_confidence",
                        "request_id": request_id,
                        "data": {
                            "confidence": round(confidence, 3),
                            "threshold": self.min_confidence,
                        },
                    },
                )

                processing_time = round((time.time() - start_time) * 1000)
                return Answer(
                    answer=None,
                    citations=[],
                    confidence=confidence,
                    message="I don't know - the information is not available in the knowledge base or the confidence is too low.",
                    request_id=request_id,
                    processing_time_ms=processing_time,
                )

            # Step 4: Generate answer using LLM
            generation_start = time.time()

            # Build prompt with retrieved context
            prompt = build_qa_prompt(
                question=question,
                retrieved_chunks=self._format_chunks_for_prompt(retrieved_chunks),
                include_system_instructions=True,
            )

            generated_answer = self.ollama_client.generate(
                prompt=prompt,
                request_id=request_id,
                temperature=0.1,  # Low temperature for factual answers
            )
            generation_time = (time.time() - generation_start) * 1000

            logger.info(
                "Answer generation complete",
                extra={
                    "component": "rag_service",
                    "event": "generation_complete",
                    "request_id": request_id,
                    "data": {
                        "generation_time_ms": round(generation_time, 2),
                        "answer_length": len(generated_answer),
                    },
                },
            )

            # Step 5: Extract and validate citations
            citations_list, all_valid = extract_citations(
                answer_text=generated_answer,
                retrieved_chunks=self._format_chunks_for_citation(retrieved_chunks),
                request_id=request_id,
            )

            # Convert to Citation objects
            citations = [
                Citation(
                    document_name=cit["document_name"],
                    excerpt=cit.get("excerpt", "")[:200],
                    page_number=cit.get("page_number"),
                    section=cit.get("section"),
                    chunk_id=cit.get("chunk_id"),
                )
                for cit in citations_list
                if cit.get("excerpt")  # Only include citations with excerpts
            ]

            # Validate citations exist
            if not citations:
                logger.warning(
                    "No valid citations found in generated answer",
                    extra={
                        "component": "rag_service",
                        "event": "no_citations",
                        "request_id": request_id,
                        "data": {"answer_length": len(generated_answer)},
                    },
                )

                # Return "I don't know" if no citations (prevent hallucination)
                processing_time = round((time.time() - start_time) * 1000)
                return Answer(
                    answer=None,
                    citations=[],
                    confidence=0.0,
                    message="I don't know - unable to verify answer with source citations.",
                    request_id=request_id,
                    processing_time_ms=processing_time,
                )

            # Step 6: Return successful answer
            processing_time = round((time.time() - start_time) * 1000)

            logger.info(
                "Query processing complete",
                extra={
                    "component": "rag_service",
                    "event": "query_complete",
                    "request_id": request_id,
                    "data": {
                        "total_time_ms": processing_time,
                        "embedding_time_ms": round(embedding_time, 2),
                        "retrieval_time_ms": round(retrieval_time, 2),
                        "generation_time_ms": round(generation_time, 2),
                        "citations_count": len(citations),
                        "confidence": round(confidence, 3),
                    },
                },
            )

            return Answer(
                answer=generated_answer,
                citations=citations,
                confidence=confidence,
                message=None,
                request_id=request_id,
                processing_time_ms=processing_time,
            )

        except (
            VectorStoreUnavailable,
            OllamaUnavailable,
            EmbeddingAPIUnavailable,
        ) as e:
            # Service unavailable - return error response
            processing_time = round((time.time() - start_time) * 1000)

            logger.error(
                "Service unavailable during query processing",
                extra={
                    "component": "rag_service",
                    "event": "service_unavailable",
                    "request_id": request_id,
                    "error": {"type": type(e).__name__, "message": str(e)},
                },
            )

            return Answer(
                answer=None,
                citations=[],
                confidence=0.0,
                message=f"Service temporarily unavailable: {str(e)}",
                request_id=request_id,
                processing_time_ms=processing_time,
            )

    def health_check(self) -> Dict[str, Any]:
        """
        Check health status of all services.

        Returns:
            Dictionary with health status of each component
        """
        logger.info(
            "Running health check",
            extra={"component": "rag_service", "event": "health_check_start"},
        )

        # Check each service
        ollama_health = self.ollama_client.health_check()
        vector_store_health = self.vector_store_client.health_check()
        embedding_health = self.embedding_client.health_check()

        # Determine overall status
        all_healthy = (
            ollama_health.get("status") == "healthy"
            and vector_store_health.get("status") == "healthy"
            and embedding_health.get("status") == "healthy"
        )

        overall_status = "healthy" if all_healthy else "degraded"

        result = {
            "status": overall_status,
            "components": {
                "ollama": ollama_health,
                "vector_store": vector_store_health,
                "embedding_api": embedding_health,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(
            "Health check complete",
            extra={
                "component": "rag_service",
                "event": "health_check_complete",
                "data": {"status": overall_status},
            },
        )

        return result

    def _calculate_confidence(self, retrieved_chunks: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score from retrieved chunks.

        Uses average similarity score from top retrieved chunks.

        Args:
            retrieved_chunks: List of retrieved chunk dictionaries

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not retrieved_chunks:
            return 0.0

        # Average similarity scores
        similarities = [
            chunk.get("similarity_score", 0.0) for chunk in retrieved_chunks
        ]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        return round(avg_similarity, 3)

    def _format_chunks_for_prompt(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format retrieved chunks for prompt building.

        Args:
            chunks: Raw chunks from vector store

        Returns:
            Formatted chunks for prompt template
        """
        formatted = []
        for chunk in chunks:
            formatted.append(
                {
                    "content": chunk.get("content", ""),
                    "metadata": {
                        "document_name": chunk.get("metadata", {}).get(
                            "source_doc", ""
                        ),
                        "section": chunk.get("metadata", {}).get("section_title", ""),
                        "page_number": chunk.get("metadata", {}).get("page_number"),
                    },
                }
            )
        return formatted

    def _format_chunks_for_citation(
        self, chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format retrieved chunks for citation extraction.

        Args:
            chunks: Raw chunks from vector store

        Returns:
            Formatted chunks for citation parser
        """
        formatted = []
        for chunk in chunks:
            formatted.append(
                {
                    "chunk_id": chunk.get("chunk_id", ""),
                    "content": chunk.get("content", ""),
                    "metadata": {
                        "document_name": chunk.get("metadata", {}).get(
                            "source_doc", ""
                        ),
                        "section": chunk.get("metadata", {}).get("section_title", ""),
                        "page_number": chunk.get("metadata", {}).get("page_number"),
                    },
                }
            )
        return formatted
