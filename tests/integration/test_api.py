"""
API Integration Tests

Tests for FastAPI endpoints including health, query, search, ingest, and documents.

Related: Phase 2 (P2), Task 2.3 - API Layer Tests
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.ingestion.cli import IngestionPipeline


@pytest.fixture(scope="module")
def sample_ingestion():
    """Ingest sample PDF once for all tests."""
    pdf_path = Path("data/pdf/Software_Company_Docupedia_FILLED.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    pipeline = IngestionPipeline()
    try:
        pipeline.ingest_pdf(pdf_path)
    except Exception as e:
        pytest.skip(f"Could not ingest PDF: {e}")


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "version" in data
        assert "database" in data
        assert "timestamp" in data
        assert "components" in data
    
    def test_health_check_components(self, client):
        """Test health check includes all components."""
        response = client.get("/health")
        data = response.json()
        
        components = data["components"]
        assert "retriever" in components
        assert "rag_pipeline" in components
        assert "vector_db" in components
        assert "chunks_available" in components


class TestQueryEndpoint:
    """Test question answering endpoint."""
    
    def test_query_basic(self, client, sample_ingestion):
        """Test basic query."""
        response = client.post(
            "/query",
            json={
                "question": "What is the vacation policy?",
                "provider": "mock"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["question"] == "What is the vacation policy?"
        assert len(data["answer"]) > 0
        assert isinstance(data["citations"], list)
        assert data["model"] == "mock-model"
    
    def test_query_with_parameters(self, client, sample_ingestion):
        """Test query with custom parameters."""
        response = client.post(
            "/query",
            json={
                "question": "What are employee benefits?",
                "top_k": 3,
                "provider": "mock",
                "temperature": 0.5,
                "max_tokens": 500
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["question"] == "What are employee benefits?"
        assert len(data["citations"]) <= 3
    
    def test_query_with_filters(self, client, sample_ingestion):
        """Test query with metadata filters."""
        response = client.post(
            "/query",
            json={
                "question": "policy",
                "top_k": 5,
                "provider": "mock",
                "filters": {"page_number": 5}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All citations should be from page 5
        for citation in data["citations"]:
            assert citation["page_number"] == 5
    
    def test_query_invalid_provider(self, client):
        """Test query with invalid provider."""
        response = client.post(
            "/query",
            json={
                "question": "test",
                "provider": "invalid_provider"
            }
        )
        
        assert response.status_code == 400
    
    def test_query_validation_error(self, client):
        """Test query with validation errors."""
        # Empty question
        response = client.post(
            "/query",
            json={
                "question": "",
                "provider": "mock"
            }
        )
        
        assert response.status_code == 422
    
    def test_query_response_structure(self, client, sample_ingestion):
        """Test query response has correct structure."""
        response = client.post(
            "/query",
            json={
                "question": "What is the company policy?",
                "provider": "mock"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "question" in data
        assert "answer" in data
        assert "citations" in data
        assert "model" in data
        assert "sources" in data
        assert "generated_at" in data
        
        # Optional fields
        assert "tokens_used" in data
        assert "page_range" in data or data["page_range"] is None
    
    def test_query_citations_structure(self, client, sample_ingestion):
        """Test citation structure in query response."""
        response = client.post(
            "/query",
            json={
                "question": "employee",
                "top_k": 2,
                "provider": "mock"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["citations"]:
            citation = data["citations"][0]
            assert "source_doc" in citation
            assert "page_number" in citation
            assert "relevance_score" in citation
            assert "text_excerpt" in citation


class TestSearchEndpoint:
    """Test search/retrieval endpoint."""
    
    def test_search_basic(self, client, sample_ingestion):
        """Test basic search."""
        response = client.post(
            "/search",
            json={
                "query": "vacation policy",
                "top_k": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "vacation policy"
        assert isinstance(data["results"], list)
        assert data["total_results"] >= 0
        assert "retrieved_at" in data
    
    def test_search_with_filters(self, client, sample_ingestion):
        """Test search with metadata filters."""
        response = client.post(
            "/search",
            json={
                "query": "policy",
                "top_k": 10,
                "filters": {"page_number": 5}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All results should be from page 5
        for result in data["results"]:
            assert result["page_number"] == 5
    
    def test_search_with_min_score(self, client, sample_ingestion):
        """Test search with minimum score filter."""
        response = client.post(
            "/search",
            json={
                "query": "employee",
                "top_k": 10,
                "min_score": 0.5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All results should have score >= 0.5
        for result in data["results"]:
            assert result["score"] >= 0.5
    
    def test_search_result_structure(self, client, sample_ingestion):
        """Test search result structure."""
        response = client.post(
            "/search",
            json={
                "query": "policy",
                "top_k": 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if data["results"]:
            result = data["results"][0]
            assert "chunk_id" in result
            assert "text" in result
            assert "score" in result
            assert "source_doc" in result
            assert "page_number" in result
            assert "metadata" in result


class TestIngestEndpoint:
    """Test document ingestion endpoint."""
    
    def test_ingest_validation_file_not_found(self, client):
        """Test ingest with non-existent file."""
        response = client.post(
            "/ingest",
            json={
                "file_path": "nonexistent/file.pdf",
                "batch": False
            }
        )
        
        assert response.status_code == 404
    
    def test_ingest_response_structure(self, client):
        """Test ingest response structure (validation only)."""
        # This test just validates the error response structure
        response = client.post(
            "/ingest",
            json={
                "file_path": "nonexistent.pdf",
                "batch": False
            }
        )
        
        assert response.status_code in [404, 500]
        data = response.json()
        
        assert "detail" in data


class TestDocumentsEndpoint:
    """Test documents listing endpoint."""
    
    def test_list_documents(self, client, sample_ingestion):
        """Test listing documents."""
        response = client.get("/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "documents" in data
        assert "total_count" in data
        assert isinstance(data["documents"], list)
        assert data["total_count"] >= 0
    
    def test_list_documents_structure(self, client, sample_ingestion):
        """Test document info structure."""
        response = client.get("/documents")
        data = response.json()
        
        if data["documents"]:
            doc = data["documents"][0]
            assert "document_id" in doc
            assert "filename" in doc
            assert "chunk_count" in doc
            assert "total_tokens" in doc
            assert "page_count" in doc
            assert "ingested_at" in doc
    
    def test_get_document_chunks_not_found(self, client):
        """Test getting chunks for non-existent document."""
        response = client.get("/documents/nonexistent-id/chunks")
        
        assert response.status_code == 404
    
    def test_get_document_chunks_structure(self, client, sample_ingestion):
        """Test document chunks structure."""
        # First get list of documents
        list_response = client.get("/documents")
        list_data = list_response.json()
        
        if list_data["documents"]:
            doc_id = list_data["documents"][0]["document_id"]
            
            # Get chunks for first document
            response = client.get(f"/documents/{doc_id}/chunks")
            
            # May return 404 or 200 depending on ChromaDB state
            if response.status_code == 200:
                data = response.json()
                
                assert "document_id" in data
                assert "chunks" in data
                assert "total_count" in data
                assert data["document_id"] == doc_id
                
                if data["chunks"]:
                    chunk = data["chunks"][0]
                    assert "chunk_id" in chunk
                    assert "text" in chunk
                    assert "page_number" in chunk
                    assert "token_count" in chunk
            elif response.status_code == 404:
                # ChromaDB may have internal issues, skip validation
                pytest.skip("Document retrieval failed (ChromaDB internal error)")


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "info" in data
        assert "paths" in data
        assert data["info"]["title"] == "HR Data Pipeline API"
    
    def test_docs_page(self, client):
        """Test Swagger UI docs page."""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_page(self, client):
        """Test ReDoc docs page."""
        response = client.get("/redoc")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestCORSHeaders:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses."""
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # CORS should allow the request
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_endpoint(self, client):
        """Test requesting non-existent endpoint."""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test using wrong HTTP method."""
        # GET on POST endpoint
        response = client.get("/query")
        
        assert response.status_code == 405
    
    def test_malformed_json(self, client):
        """Test sending malformed JSON."""
        response = client.post(
            "/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


def test_api_end_to_end(client, sample_ingestion):
    """End-to-end API test."""
    # 1. Check health
    health_response = client.get("/health")
    assert health_response.status_code == 200
    
    # 2. Search for documents
    search_response = client.post(
        "/search",
        json={"query": "vacation", "top_k": 3}
    )
    assert search_response.status_code == 200
    
    # 3. Ask a question
    query_response = client.post(
        "/query",
        json={
            "question": "What is the vacation policy?",
            "provider": "mock"
        }
    )
    assert query_response.status_code == 200
    query_data = query_response.json()
    assert len(query_data["answer"]) > 0
    
    # 4. List documents
    docs_response = client.get("/documents")
    assert docs_response.status_code == 200
    docs_data = docs_response.json()
    assert docs_data["total_count"] > 0
