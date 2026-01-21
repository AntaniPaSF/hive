"""
Integration tests for RAG service end-to-end query flow.

Tests the complete pipeline: embedding → retrieval → generation → citation extraction
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.rag_service import RAGService
from src.schemas.query import Query, Answer, Citation
from src.utils.errors import VectorStoreUnavailable, OllamaUnavailable


@pytest.fixture
def sample_query_embedding():
    """Sample 384-dim embedding vector."""
    return [0.1] * 384


@pytest.fixture
def sample_retrieved_chunks():
    """Sample chunks from vector store."""
    return [
        {
            "chunk_id": "chunk_safety_p5_0",
            "content": "All personnel must wear protective eyewear and gloves when handling Class A chemicals.",
            "metadata": {
                "source_doc": "safety_manual.pdf",
                "page_number": 5,
                "section_title": "Chemical Handling",
                "chunk_index": 0,
                "source_type": "pdf",
            },
            "similarity_score": 0.87,
        },
        {
            "chunk_id": "chunk_safety_p6_0",
            "content": "Chemical storage areas must maintain ventilation and temperature control according to specifications.",
            "metadata": {
                "source_doc": "safety_manual.pdf",
                "page_number": 6,
                "section_title": "Chemical Storage",
                "chunk_index": 0,
                "source_type": "pdf",
            },
            "similarity_score": 0.72,
        },
    ]


@pytest.fixture
def sample_llm_answer():
    """Sample answer from LLM with citations."""
    return "Personnel handling Class A chemicals must wear protective eyewear and gloves according to [safety_manual.pdf, Chemical Handling]. Storage areas must maintain proper ventilation [safety_manual.pdf, Chemical Storage]."


@pytest.fixture
def rag_service():
    """Create RAG service with mocked clients."""
    # Create mocked clients
    embedding_client = Mock()
    vector_store_client = Mock()
    ollama_client = Mock()

    # Create service
    service = RAGService(
        embedding_client=embedding_client,
        vector_store_client=vector_store_client,
        ollama_client=ollama_client,
        min_confidence=0.5,
    )

    return service


class TestRAGServiceQuery:
    """Test RAGService query method."""

    def test_successful_query_flow(
        self,
        rag_service,
        sample_query_embedding,
        sample_retrieved_chunks,
        sample_llm_answer,
    ):
        """Test complete successful query flow."""
        # Setup mocks
        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = sample_retrieved_chunks
        rag_service.ollama_client.generate.return_value = sample_llm_answer

        # Execute query
        result = rag_service.query(
            question="What safety equipment is required for handling chemicals?",
            filters={"max_results": 5},
        )

        # Verify result
        assert isinstance(result, Answer)
        assert result.answer == sample_llm_answer
        assert len(result.citations) == 2
        assert result.confidence > 0.5
        assert result.request_id is not None
        assert result.processing_time_ms > 0

        # Verify all clients were called
        rag_service.embedding_client.embed.assert_called_once()
        rag_service.vector_store_client.query.assert_called_once()
        rag_service.ollama_client.generate.assert_called_once()

    def test_query_with_request_id(
        self,
        rag_service,
        sample_query_embedding,
        sample_retrieved_chunks,
        sample_llm_answer,
    ):
        """Test query with provided request ID."""
        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = sample_retrieved_chunks
        rag_service.ollama_client.generate.return_value = sample_llm_answer

        custom_request_id = "custom_req_12345"
        result = rag_service.query(
            question="Test question", request_id=custom_request_id
        )

        assert result.request_id == custom_request_id

    def test_low_confidence_returns_i_dont_know(
        self, rag_service, sample_query_embedding
    ):
        """Test low confidence results in 'I don't know' response."""
        # Return chunks with low similarity scores
        low_confidence_chunks = [
            {
                "chunk_id": "chunk_1",
                "content": "Some content",
                "metadata": {"source_doc": "doc.pdf", "section_title": "Section"},
                "similarity_score": 0.3,
            }
        ]

        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = low_confidence_chunks

        result = rag_service.query(question="Test question")

        # Should return "I don't know" without calling LLM
        assert result.answer is None
        assert len(result.citations) == 0
        assert result.confidence < 0.5
        assert "don't know" in result.message.lower()

        # Verify LLM was NOT called due to low confidence
        rag_service.ollama_client.generate.assert_not_called()

    def test_no_citations_returns_i_dont_know(
        self, rag_service, sample_query_embedding, sample_retrieved_chunks
    ):
        """Test answer without citations returns 'I don't know'."""
        # Answer without citation markers
        answer_without_citations = (
            "Personnel must wear protective equipment when handling chemicals."
        )

        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = sample_retrieved_chunks
        rag_service.ollama_client.generate.return_value = answer_without_citations

        result = rag_service.query(question="Test question")

        # Should return "I don't know" due to missing citations
        assert result.answer is None
        assert len(result.citations) == 0
        assert result.confidence == 0.0
        assert "citations" in result.message.lower()

    def test_vector_store_unavailable(self, rag_service, sample_query_embedding):
        """Test handling of vector store unavailability."""
        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.side_effect = VectorStoreUnavailable(
            "Connection timeout"
        )

        result = rag_service.query(question="Test question")

        # Should return error response
        assert result.answer is None
        assert len(result.citations) == 0
        assert result.confidence == 0.0
        assert "unavailable" in result.message.lower()

    def test_ollama_unavailable(
        self, rag_service, sample_query_embedding, sample_retrieved_chunks
    ):
        """Test handling of Ollama unavailability."""
        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = sample_retrieved_chunks
        rag_service.ollama_client.generate.side_effect = OllamaUnavailable(
            "Connection refused"
        )

        result = rag_service.query(question="Test question")

        # Should return error response
        assert result.answer is None
        assert "unavailable" in result.message.lower()

    def test_query_with_source_filter(
        self,
        rag_service,
        sample_query_embedding,
        sample_retrieved_chunks,
        sample_llm_answer,
    ):
        """Test query with source document filter."""
        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = sample_retrieved_chunks
        rag_service.ollama_client.generate.return_value = sample_llm_answer

        result = rag_service.query(
            question="Test question",
            filters={"source": "safety_manual.pdf", "max_results": 3},
        )

        # Verify filter was passed to vector store
        call_args = rag_service.vector_store_client.query.call_args
        assert call_args.kwargs["source_filter"] == "safety_manual.pdf"
        assert call_args.kwargs["max_results"] == 3

    def test_confidence_calculation(self, rag_service, sample_query_embedding):
        """Test confidence score calculation."""
        chunks_with_varied_scores = [
            {
                "chunk_id": "1",
                "content": "Content 1",
                "metadata": {"source_doc": "doc.pdf", "section_title": "Section"},
                "similarity_score": 0.9,
            },
            {
                "chunk_id": "2",
                "content": "Content 2",
                "metadata": {"source_doc": "doc.pdf", "section_title": "Section"},
                "similarity_score": 0.7,
            },
            {
                "chunk_id": "3",
                "content": "Content 3",
                "metadata": {"source_doc": "doc.pdf", "section_title": "Section"},
                "similarity_score": 0.6,
            },
        ]

        # Expected average: (0.9 + 0.7 + 0.6) / 3 = 0.733...
        confidence = rag_service._calculate_confidence(chunks_with_varied_scores)

        assert 0.73 <= confidence <= 0.74

    def test_empty_chunks_zero_confidence(self, rag_service):
        """Test zero confidence for empty chunks."""
        confidence = rag_service._calculate_confidence([])
        assert confidence == 0.0


class TestRAGServiceHealthCheck:
    """Test RAGService health check."""

    def test_health_check_all_healthy(self, rag_service):
        """Test health check when all services are healthy."""
        # Setup mocks
        rag_service.ollama_client.health_check.return_value = {
            "status": "healthy",
            "model": "mistral:7b",
            "model_available": True,
        }
        rag_service.vector_store_client.health_check.return_value = {
            "status": "healthy",
            "collection": "corporate_documents",
        }
        rag_service.embedding_client.health_check.return_value = {
            "status": "healthy",
            "endpoint": "http://localhost:8000/embed",
        }

        result = rag_service.health_check()

        assert result["status"] == "healthy"
        assert "ollama" in result["components"]
        assert "vector_store" in result["components"]
        assert "embedding_api" in result["components"]
        assert "timestamp" in result

    def test_health_check_degraded(self, rag_service):
        """Test health check when one service is degraded."""
        rag_service.ollama_client.health_check.return_value = {"status": "healthy"}
        rag_service.vector_store_client.health_check.return_value = {
            "status": "unhealthy",
            "error": "Connection timeout",
        }
        rag_service.embedding_client.health_check.return_value = {"status": "healthy"}

        result = rag_service.health_check()

        assert result["status"] == "degraded"
        assert result["components"]["vector_store"]["status"] == "unhealthy"


class TestRAGServiceFormatting:
    """Test internal formatting methods."""

    def test_format_chunks_for_prompt(self, rag_service, sample_retrieved_chunks):
        """Test chunk formatting for prompt building."""
        formatted = rag_service._format_chunks_for_prompt(sample_retrieved_chunks)

        assert len(formatted) == 2
        assert "content" in formatted[0]
        assert "metadata" in formatted[0]
        assert formatted[0]["metadata"]["document_name"] == "safety_manual.pdf"
        assert formatted[0]["metadata"]["section"] == "Chemical Handling"

    def test_format_chunks_for_citation(self, rag_service, sample_retrieved_chunks):
        """Test chunk formatting for citation extraction."""
        formatted = rag_service._format_chunks_for_citation(sample_retrieved_chunks)

        assert len(formatted) == 2
        assert "chunk_id" in formatted[0]
        assert "content" in formatted[0]
        assert "metadata" in formatted[0]
        assert formatted[0]["chunk_id"] == "chunk_safety_p5_0"


class TestRAGServiceIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_complex_multi_source_query(self, rag_service, sample_query_embedding):
        """Test query retrieving from multiple source documents."""
        multi_source_chunks = [
            {
                "chunk_id": "chunk_hr_1",
                "content": "Employees receive 20 days of paid vacation.",
                "metadata": {
                    "source_doc": "hr_policy.pdf",
                    "page_number": 12,
                    "section_title": "Time Off",
                    "chunk_index": 0,
                },
                "similarity_score": 0.85,
            },
            {
                "chunk_id": "chunk_benefits_1",
                "content": "Health insurance coverage begins on the first day of employment.",
                "metadata": {
                    "source_doc": "benefits_guide.pdf",
                    "page_number": 3,
                    "section_title": "Health Benefits",
                    "chunk_index": 0,
                },
                "similarity_score": 0.78,
            },
        ]

        llm_answer = "Employees receive 20 days of paid vacation [hr_policy.pdf, Time Off] and health insurance starts immediately [benefits_guide.pdf, Health Benefits]."

        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = multi_source_chunks
        rag_service.ollama_client.generate.return_value = llm_answer

        result = rag_service.query(question="What are the employee benefits?")

        assert result.answer is not None
        assert len(result.citations) == 2
        assert any(c.document_name == "hr_policy.pdf" for c in result.citations)
        assert any(c.document_name == "benefits_guide.pdf" for c in result.citations)

    def test_borderline_confidence_threshold(self, rag_service, sample_query_embedding):
        """Test behavior at confidence threshold boundary."""
        # Exactly at threshold (0.5)
        threshold_chunks = [
            {
                "chunk_id": "1",
                "content": "Content",
                "metadata": {"source_doc": "doc.pdf", "section_title": "Section"},
                "similarity_score": 0.5,
            }
        ]

        llm_answer = "According to the document [doc.pdf, Section], this is the answer."

        rag_service.embedding_client.embed.return_value = sample_query_embedding
        rag_service.vector_store_client.query.return_value = threshold_chunks
        rag_service.ollama_client.generate.return_value = llm_answer

        result = rag_service.query(question="Test question")

        # At exactly 0.5, should proceed with generation
        assert result.answer is not None
        assert result.confidence == 0.5
