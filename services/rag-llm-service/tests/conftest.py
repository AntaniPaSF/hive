"""
Shared pytest fixtures for RAG LLM Service tests.

Provides common test data, mock objects, and utilities across all test modules.
"""

import pytest
from unittest.mock import Mock
from typing import List, Dict, Any

from src.schemas.query import Query, Answer, Citation


# Sample test data fixtures
@pytest.fixture
def sample_question() -> str:
    """Sample question for testing."""
    return "What are the safety protocols for handling chemicals?"


@pytest.fixture
def sample_query() -> Query:
    """Sample Query object for testing."""
    return Query(
        question="What are the safety protocols for handling chemicals?",
        filters={"source": "safety_manual.pdf", "max_results": 5},
    )


@pytest.fixture
def sample_citation() -> Citation:
    """Sample Citation object for testing."""
    return Citation(
        document_name="safety_manual.pdf",
        excerpt="All personnel must wear protective eyewear and gloves when handling Class A chemicals.",
        section="Chemical Handling",
        page_number=5,
        chunk_id="chunk_safety_p5_0",
    )


@pytest.fixture
def sample_citations() -> List[Citation]:
    """Sample list of citations for testing."""
    return [
        Citation(
            document_name="safety_manual.pdf",
            excerpt="All personnel must wear protective eyewear and gloves when handling Class A chemicals.",
            section="Chemical Handling",
            page_number=5,
            chunk_id="chunk_safety_p5_0",
        ),
        Citation(
            document_name="safety_manual.pdf",
            excerpt="Chemical storage areas must maintain ventilation and temperature control according to specifications.",
            section="Chemical Storage",
            page_number=6,
            chunk_id="chunk_safety_p6_0",
        ),
    ]


@pytest.fixture
def sample_answer(sample_citations) -> Answer:
    """Sample Answer object for testing."""
    return Answer(
        answer="Personnel handling Class A chemicals must wear protective eyewear and gloves according to [safety_manual.pdf, Chemical Handling]. Storage areas must maintain proper ventilation [safety_manual.pdf, Chemical Storage].",
        citations=sample_citations,
        confidence=0.87,
        message="Answer generated successfully",
        request_id="req_20260121_test123",
        processing_time_ms=3420,
    )


@pytest.fixture
def sample_low_confidence_answer() -> Answer:
    """Sample low confidence 'I don't know' answer for testing."""
    return Answer(
        answer=None,
        citations=[],
        confidence=0.3,
        message="I don't know - retrieved content has low confidence score",
        request_id="req_20260121_test456",
        processing_time_ms=1250,
    )


@pytest.fixture
def sample_retrieved_chunks() -> List[Dict[str, Any]]:
    """Sample retrieved chunks from vector store."""
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
def sample_embedding() -> List[float]:
    """Sample 384-dimensional embedding vector."""
    return [0.1] * 384


# Mock client fixtures
@pytest.fixture
def mock_chromadb_client():
    """Mock ChromaDB client."""
    client = Mock()
    client.query = Mock()
    client.health_check = Mock(return_value={"status": "healthy"})
    return client


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client."""
    client = Mock()
    client.generate = Mock()
    client.health_check = Mock(
        return_value={"status": "healthy", "model": "mistral:7b"}
    )
    return client


@pytest.fixture
def mock_embedding_client():
    """Mock Embedding API client."""
    client = Mock()
    client.embed = Mock()
    client.health_check = Mock(return_value={"status": "healthy"})
    return client


@pytest.fixture
def mock_rag_service(mock_chromadb_client, mock_ollama_client, mock_embedding_client):
    """Mock complete RAG service."""
    service = Mock()
    service.vector_store_client = mock_chromadb_client
    service.ollama_client = mock_ollama_client
    service.embedding_client = mock_embedding_client
    service.query = Mock()
    service.health_check = Mock()
    return service


# Test data generators
@pytest.fixture
def make_query():
    """Factory fixture for creating Query objects."""

    def _make_query(question: str, filters: Dict[str, Any] = None) -> Query:
        return Query(question=question, filters=filters)

    return _make_query


@pytest.fixture
def make_citation():
    """Factory fixture for creating Citation objects."""

    def _make_citation(
        document_name: str,
        excerpt: str,
        section: str = None,
        page_number: int = None,
        chunk_id: str = None,
    ) -> Citation:
        return Citation(
            document_name=document_name,
            excerpt=excerpt,
            section=section,
            page_number=page_number,
            chunk_id=chunk_id,
        )

    return _make_citation


@pytest.fixture
def make_answer():
    """Factory fixture for creating Answer objects."""

    def _make_answer(
        answer: str = None,
        citations: List[Citation] = None,
        confidence: float = 0.5,
        message: str = "Success",
        request_id: str = "req_test",
        processing_time_ms: int = 1000,
    ) -> Answer:
        return Answer(
            answer=answer,
            citations=citations or [],
            confidence=confidence,
            message=message,
            request_id=request_id,
            processing_time_ms=processing_time_ms,
        )

    return _make_answer
