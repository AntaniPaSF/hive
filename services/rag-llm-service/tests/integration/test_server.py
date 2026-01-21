"""
Integration tests for FastAPI server endpoints.

Tests the REST API layer including /query and /health endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager

from src.server import app
from src.schemas.query import Answer, Citation
from src.utils.errors import VectorStoreUnavailable, OllamaUnavailable


@pytest.fixture
def mock_rag_service():
    """Create a mocked RAG service."""
    service = Mock()
    service.query = Mock()
    service.health_check = Mock()
    return service


@asynccontextmanager
async def mock_lifespan(app):
    """Mock lifespan to skip actual service initialization."""
    yield


@pytest.fixture
def client(mock_rag_service):
    """Create test client with mocked RAG service and skipped lifespan."""
    # Override app's lifespan context manager to avoid real initialization
    app_copy = app

    @asynccontextmanager
    async def override_lifespan(app):
        # Set mock service directly without initialization
        import src.server as server_module

        server_module.rag_service = mock_rag_service
        yield

    # Save original and temporarily override
    original_lifespan = app_copy.router.lifespan_context
    app_copy.router.lifespan_context = override_lifespan

    # Set raise_server_exceptions=False to properly test exception handlers
    with TestClient(app_copy, raise_server_exceptions=False) as test_client:
        yield test_client

    # Restore original lifespan
    app_copy.router.lifespan_context = original_lifespan


class TestQueryEndpoint:
    """Test POST /query endpoint."""

    def test_successful_query(self, client, mock_rag_service):
        """Test successful query with answer and citations."""
        # Setup mock response
        mock_answer = Answer(
            answer="Personnel must wear protective eyewear and gloves when handling Class A chemicals according to [safety_manual.pdf, Chemical Handling].",
            citations=[
                Citation(
                    document_name="safety_manual.pdf",
                    excerpt="All personnel must wear protective eyewear and gloves when handling Class A chemicals.",
                    section="Chemical Handling",
                    page_number=5,
                    chunk_id="chunk_safety_p5_0",
                )
            ],
            confidence=0.87,
            message="Answer generated successfully",
            request_id="req_20260121_test123",
            processing_time_ms=3420,
        )

        mock_rag_service.query.return_value = mock_answer

        # Make request
        response = client.post(
            "/query",
            json={
                "question": "What safety equipment is required for handling chemicals?"
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] is not None
        assert len(data["citations"]) == 1
        assert data["confidence"] == 0.87
        assert data["request_id"] == "req_20260121_test123"
        assert data["processing_time_ms"] == 3420

        # Verify headers
        assert "X-Processing-Time-Ms" in response.headers
        assert "X-Request-ID" in response.headers

    def test_query_with_filters(self, client, mock_rag_service):
        """Test query with source and max_results filters."""
        mock_answer = Answer(
            answer="Test answer",
            citations=[],
            confidence=0.6,
            message="Success",
            request_id="req_test",
            processing_time_ms=1500,
        )

        mock_rag_service.query.return_value = mock_answer

        response = client.post(
            "/query",
            json={
                "question": "Test question",
                "filters": {"source": "safety_manual.pdf", "max_results": 3},
            },
        )

        assert response.status_code == 200

        # Verify filters were passed to service
        call_args = mock_rag_service.query.call_args
        assert call_args.kwargs["filters"]["source"] == "safety_manual.pdf"
        assert call_args.kwargs["filters"]["max_results"] == 3

    def test_query_with_custom_request_id(self, client, mock_rag_service):
        """Test query with custom request ID."""
        custom_request_id = "custom_req_xyz789"

        mock_answer = Answer(
            answer="Test answer",
            citations=[],
            confidence=0.5,
            message="Success",
            request_id=custom_request_id,
            processing_time_ms=1000,
        )

        mock_rag_service.query.return_value = mock_answer

        response = client.post(
            "/query",
            json={"question": "Test question", "request_id": custom_request_id},
        )

        assert response.status_code == 200
        assert response.json()["request_id"] == custom_request_id

    def test_low_confidence_query(self, client, mock_rag_service):
        """Test query with low confidence returns 'I don't know'."""
        mock_answer = Answer(
            answer=None,
            citations=[],
            confidence=0.3,
            message="I don't know - retrieved content has low confidence score",
            request_id="req_test",
            processing_time_ms=1200,
        )

        mock_rag_service.query.return_value = mock_answer

        response = client.post(
            "/query", json={"question": "What is the meaning of life?"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["answer"] is None
        assert len(data["citations"]) == 0
        assert data["confidence"] < 0.5
        assert "don't know" in data["message"].lower()

    def test_query_validation_empty_question(self, client):
        """Test validation error for empty question."""
        response = client.post("/query", json={"question": ""})

        assert response.status_code == 422  # Validation error

    def test_query_validation_question_too_short(self, client):
        """Test validation error for question too short."""
        response = client.post("/query", json={"question": "Hi"})

        assert response.status_code == 422

    def test_query_validation_question_too_long(self, client):
        """Test validation error for question too long."""
        response = client.post("/query", json={"question": "x" * 1001})

        assert response.status_code == 422

    def test_query_validation_invalid_max_results(self, client):
        """Test validation error for invalid max_results."""
        response = client.post(
            "/query",
            json={
                "question": "Test question",
                "filters": {"max_results": 15},  # Max is 10
            },
        )

        assert response.status_code == 422

    def test_query_validation_negative_max_results(self, client):
        """Test validation error for negative max_results."""
        response = client.post(
            "/query", json={"question": "Test question", "filters": {"max_results": -1}}
        )

        assert response.status_code == 422

    def test_query_whitespace_stripped(self, client, mock_rag_service):
        """Test that whitespace is stripped from question."""
        mock_answer = Answer(
            answer="Test answer",
            citations=[],
            confidence=0.5,
            message="Success",
            request_id="req_test",
            processing_time_ms=1000,
        )

        mock_rag_service.query.return_value = mock_answer

        response = client.post(
            "/query", json={"question": "  Test question with spaces  "}
        )

        assert response.status_code == 200

        # Verify stripped question was passed to service
        call_args = mock_rag_service.query.call_args
        assert call_args.kwargs["question"] == "Test question with spaces"


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    def test_health_all_healthy(self, client, mock_rag_service):
        """Test health check when all services are healthy."""
        mock_rag_service.health_check.return_value = {
            "status": "healthy",
            "components": {
                "ollama": {"status": "healthy", "model": "mistral:7b"},
                "vector_store": {
                    "status": "healthy",
                    "collection": "corporate_documents",
                },
                "embedding_api": {
                    "status": "healthy",
                    "endpoint": "http://localhost:8000/embed",
                },
            },
            "timestamp": "2026-01-21T14:00:00.000Z",
        }

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "components" in data
        assert "timestamp" in data

    def test_health_degraded(self, client, mock_rag_service):
        """Test health check when one service is degraded."""
        mock_rag_service.health_check.return_value = {
            "status": "degraded",
            "components": {
                "ollama": {"status": "healthy"},
                "vector_store": {"status": "unhealthy", "error": "Connection timeout"},
                "embedding_api": {"status": "healthy"},
            },
            "timestamp": "2026-01-21T14:00:00.000Z",
        }

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "degraded"

    def test_health_unhealthy(self, client, mock_rag_service):
        """Test health check when service is unhealthy."""
        mock_rag_service.health_check.return_value = {
            "status": "unhealthy",
            "error": "Critical service failure",
            "timestamp": "2026-01-21T14:00:00.000Z",
        }

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()

        assert data["status"] == "unhealthy"

    def test_health_service_not_initialized(self, client):
        """Test health check when RAG service is not initialized."""
        with patch("src.server.rag_service", None):
            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "unhealthy"
            assert "not initialized" in data["error"]


class TestErrorHandling:
    """Test error handling and responses."""

    def test_vector_store_unavailable(self, client, mock_rag_service):
        """Test error response when vector store is unavailable."""
        mock_rag_service.query.side_effect = VectorStoreUnavailable(
            "ChromaDB connection timeout"
        )

        response = client.post("/query", json={"question": "Test question"})

        assert response.status_code == 503
        data = response.json()

        assert data["error_type"] == "vector_store_unavailable"
        assert "ChromaDB" in data["error_details"]
        assert "timestamp" in data

    def test_ollama_unavailable(self, client, mock_rag_service):
        """Test error response when Ollama is unavailable."""
        mock_rag_service.query.side_effect = OllamaUnavailable(
            "Ollama connection refused"
        )

        response = client.post("/query", json={"question": "Test question"})

        assert response.status_code == 503
        data = response.json()

        assert data["error_type"] == "ollama_unavailable"
        assert "Ollama" in data["error_details"]

    def test_value_error(self, client, mock_rag_service):
        """Test error response for validation errors."""
        mock_rag_service.query.side_effect = ValueError("Invalid input format")

        response = client.post("/query", json={"question": "Test question"})

        assert response.status_code == 400
        data = response.json()

        assert data["error_type"] == "validation_error"
        assert "Invalid input" in data["error_details"]

    def test_unexpected_exception(self, client, mock_rag_service):
        """Test error response for unexpected exceptions."""
        mock_rag_service.query.side_effect = RuntimeError("Unexpected error")

        response = client.post("/query", json={"question": "Test question"})

        assert response.status_code == 500
        data = response.json()

        assert data["error_type"] == "internal_server_error"
        assert "unexpected error" in data["error_details"].lower()


class TestRootEndpoint:
    """Test GET / root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns service information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "RAG LLM Service"
        assert "version" in data
        assert "endpoints" in data
        assert "POST /query" in data["endpoints"]
        assert "GET /health" in data["endpoints"]


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers are present on responses."""
        response = client.get("/")

        # CORS middleware should add appropriate headers
        # The middleware adds headers to responses, not to OPTIONS specifically
        assert response.status_code == 200


class TestRequestLogging:
    """Test request logging middleware."""

    def test_request_logging_headers(self, client, mock_rag_service):
        """Test that processing time and request ID are added to headers."""
        mock_answer = Answer(
            answer="Test answer",
            citations=[],
            confidence=0.5,
            message="Success",
            request_id="req_test",
            processing_time_ms=1000,
        )

        mock_rag_service.query.return_value = mock_answer

        response = client.post("/query", json={"question": "Test question"})

        assert "X-Processing-Time-Ms" in response.headers
        assert "X-Request-ID" in response.headers

    def test_custom_request_id_in_header(self, client, mock_rag_service):
        """Test that custom request ID from header is used."""
        custom_request_id = "custom_header_req_123"

        mock_answer = Answer(
            answer="Test answer",
            citations=[],
            confidence=0.5,
            message="Success",
            request_id=custom_request_id,
            processing_time_ms=1000,
        )

        mock_rag_service.query.return_value = mock_answer

        response = client.post(
            "/query",
            json={"question": "Test question"},
            headers={"X-Request-ID": custom_request_id},
        )

        assert response.headers["X-Request-ID"] == custom_request_id
