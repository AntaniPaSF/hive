"""Unit tests for vector store retrieval client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, ConnectionError

from src.core.retrieval import VectorStoreClient
from src.schemas.query import RetrievedChunk
from src.utils.errors import VectorStoreUnavailable, EmbeddingDimensionMismatch


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("src.core.retrieval.get_settings") as mock:
        settings = Mock()
        settings.vector_store_url = "http://localhost:8001"
        settings.vector_store_collection = "corporate_documents"
        settings.vector_store_timeout = 10
        settings.max_retrieved_chunks = 5
        settings.min_confidence_threshold = 0.5
        mock.return_value = settings
        yield settings


@pytest.fixture
def vector_store_client(mock_settings):
    """Create VectorStoreClient instance for testing."""
    return VectorStoreClient()


@pytest.fixture
def sample_query_embedding():
    """Sample 384-dimensional embedding vector."""
    return [0.1] * 384


@pytest.fixture
def mock_chromadb_response():
    """Sample ChromaDB API response."""
    return {
        "ids": [["chunk_pdf_hash1_0", "chunk_pdf_hash2_1", "chunk_kaggle_hash3_2"]],
        "documents": [
            [
                "All personnel must wear protective eyewear when handling chemicals.",
                "Annual leave is granted at 20 days per year for full-time employees.",
                "Remote work requires manager approval and secure VPN connection.",
            ]
        ],
        "metadatas": [
            [
                {
                    "source_doc": "safety_manual.pdf",
                    "source_type": "pdf",
                    "page_number": 5,
                    "section_title": "Chemical Handling",
                    "chunk_index": 0,
                    "embedding_model": "all-MiniLM-L6-v2",
                },
                {
                    "source_doc": "hr_policy.pdf",
                    "source_type": "pdf",
                    "page_number": 12,
                    "section_title": "Leave Policy",
                    "chunk_index": 1,
                    "embedding_model": "all-MiniLM-L6-v2",
                },
                {
                    "source_doc": "remote_work_guide.txt",
                    "source_type": "kaggle",
                    "section_title": "Remote Work Guidelines",
                    "chunk_index": 2,
                    "embedding_model": "all-MiniLM-L6-v2",
                },
            ]
        ],
        "distances": [[0.15, 0.25, 0.35]],  # Cosine distances
    }


class TestVectorStoreClient:
    """Test suite for VectorStoreClient."""

    def test_initialization(self, vector_store_client, mock_settings):
        """Test client initialization with default settings."""
        assert vector_store_client.vector_store_url == "http://localhost:8001"
        assert vector_store_client.collection_name == "corporate_documents"
        assert vector_store_client.timeout == 10
        assert vector_store_client.max_retrieved_chunks == 5

    def test_custom_initialization(self, mock_settings):
        """Test client initialization with custom parameters."""
        client = VectorStoreClient(
            vector_store_url="http://custom:9000",
            collection_name="custom_collection",
            timeout=30,
        )
        assert client.vector_store_url == "http://custom:9000"
        assert client.collection_name == "custom_collection"
        assert client.timeout == 30

    @patch("src.core.retrieval.requests.post")
    def test_query_success(
        self,
        mock_post,
        vector_store_client,
        sample_query_embedding,
        mock_chromadb_response,
    ):
        """Test successful query with proper chunk ordering."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_chromadb_response
        mock_post.return_value = mock_response

        # Execute query
        chunks = vector_store_client.query(
            query_embedding=sample_query_embedding, request_id="test_request_123"
        )

        # Verify chunks returned
        assert len(chunks) == 3
        assert all(isinstance(chunk, RetrievedChunk) for chunk in chunks)

        # Verify ordering by similarity (highest first)
        # distances [0.15, 0.25, 0.35] -> similarities [0.85, 0.75, 0.65]
        assert chunks[0].similarity_score == 0.85
        assert chunks[1].similarity_score == 0.75
        assert chunks[2].similarity_score == 0.65

        # Verify first chunk metadata
        assert chunks[0].chunk_id == "chunk_pdf_hash1_0"
        assert chunks[0].metadata["document_name"] == "safety_manual.pdf"
        assert chunks[0].metadata["page_number"] == 5
        assert chunks[0].metadata["section"] == "Chemical Handling"
        assert chunks[0].metadata["chunk_index"] == 0

    @patch("src.core.retrieval.requests.post")
    def test_query_with_filters(
        self,
        mock_post,
        vector_store_client,
        sample_query_embedding,
        mock_chromadb_response,
    ):
        """Test query with source filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_chromadb_response
        mock_post.return_value = mock_response

        # Execute query with filter
        chunks = vector_store_client.query(
            query_embedding=sample_query_embedding,
            max_results=3,
            source_filter="safety_manual.pdf",
            request_id="test_request_456",
        )

        # Verify API call included filters
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["n_results"] == 3
        assert payload["where"]["source_doc"] == "safety_manual.pdf"

    @patch("src.core.retrieval.requests.post")
    def test_query_embedding_dimension_mismatch(self, mock_post, vector_store_client):
        """Test query with invalid embedding dimension."""
        # Invalid embedding (not 384 dimensions)
        invalid_embedding = [0.1] * 256

        with pytest.raises(EmbeddingDimensionMismatch) as exc_info:
            vector_store_client.query(
                query_embedding=invalid_embedding, request_id="test_invalid_dim"
            )

        assert "expected 384" in str(exc_info.value)
        assert "got 256" in str(exc_info.value)

    @patch("src.core.retrieval.requests.post")
    def test_query_timeout(
        self, mock_post, vector_store_client, sample_query_embedding
    ):
        """Test query timeout handling."""
        mock_post.side_effect = Timeout("Connection timeout")

        with pytest.raises(VectorStoreUnavailable) as exc_info:
            vector_store_client.query(
                query_embedding=sample_query_embedding, request_id="test_timeout"
            )

        assert "timeout" in str(exc_info.value).lower()

    @patch("src.core.retrieval.requests.post")
    def test_query_connection_error(
        self, mock_post, vector_store_client, sample_query_embedding
    ):
        """Test connection error handling."""
        mock_post.side_effect = ConnectionError("Failed to connect")

        with pytest.raises(VectorStoreUnavailable) as exc_info:
            vector_store_client.query(
                query_embedding=sample_query_embedding, request_id="test_conn_error"
            )

        assert "connect" in str(exc_info.value).lower()

    @patch("src.core.retrieval.requests.post")
    def test_query_404_collection_not_found(
        self, mock_post, vector_store_client, sample_query_embedding
    ):
        """Test 404 error when collection not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        with pytest.raises(VectorStoreUnavailable) as exc_info:
            vector_store_client.query(
                query_embedding=sample_query_embedding, request_id="test_404"
            )

        assert "not found" in str(exc_info.value).lower()

    @patch("src.core.retrieval.requests.post")
    def test_query_500_server_error(
        self, mock_post, vector_store_client, sample_query_embedding
    ):
        """Test 500 server error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with pytest.raises(VectorStoreUnavailable) as exc_info:
            vector_store_client.query(
                query_embedding=sample_query_embedding, request_id="test_500"
            )

        assert "server error" in str(exc_info.value).lower()

    @patch("src.core.retrieval.requests.post")
    def test_metadata_extraction_missing_fields(
        self, mock_post, vector_store_client, sample_query_embedding
    ):
        """Test metadata extraction with missing optional fields."""
        # Response with minimal metadata
        minimal_response = {
            "ids": [["chunk_minimal_1"]],
            "documents": [["Sample content without full metadata"]],
            "metadatas": [
                [
                    {
                        "source_doc": "minimal.pdf",
                        "chunk_index": 0,
                        # Missing: page_number, section_title, source_type
                    }
                ]
            ],
            "distances": [[0.2]],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = minimal_response
        mock_post.return_value = mock_response

        chunks = vector_store_client.query(
            query_embedding=sample_query_embedding, request_id="test_minimal_metadata"
        )

        assert len(chunks) == 1
        assert chunks[0].metadata["document_name"] == "minimal.pdf"
        assert chunks[0].metadata["chunk_index"] == 0
        assert "page_number" not in chunks[0].metadata
        assert "section" not in chunks[0].metadata

    @patch("src.core.retrieval.requests.post")
    def test_confidence_calculation(
        self,
        mock_post,
        vector_store_client,
        sample_query_embedding,
        mock_chromadb_response,
    ):
        """Test confidence score calculation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_chromadb_response
        mock_post.return_value = mock_response

        chunks = vector_store_client.query(
            query_embedding=sample_query_embedding, request_id="test_confidence"
        )

        # Calculate expected confidence
        # similarities: [0.85, 0.75, 0.65]
        # average: (0.85 + 0.75 + 0.65) / 3 = 0.75
        confidence = vector_store_client._calculate_confidence(chunks)
        assert abs(confidence - 0.75) < 0.01

    @patch("src.core.retrieval.requests.post")
    def test_confidence_calculation_empty_chunks(
        self, mock_post, vector_store_client, sample_query_embedding
    ):
        """Test confidence calculation with zero chunks."""
        # Empty response
        empty_response = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_response
        mock_post.return_value = mock_response

        chunks = vector_store_client.query(
            query_embedding=sample_query_embedding, request_id="test_empty"
        )

        assert len(chunks) == 0
        confidence = vector_store_client._calculate_confidence(chunks)
        assert confidence == 0.0

    @patch("src.core.retrieval.requests.post")
    def test_embedding_model_mismatch_warning(
        self, mock_post, vector_store_client, sample_query_embedding, caplog
    ):
        """Test warning when chunk has mismatched embedding model."""
        # Response with wrong embedding model
        mismatched_response = {
            "ids": [["chunk_wrong_model"]],
            "documents": [["Content with wrong model"]],
            "metadatas": [
                [
                    {
                        "source_doc": "test.pdf",
                        "chunk_index": 0,
                        "embedding_model": "text-embedding-ada-002",  # Wrong model
                    }
                ]
            ],
            "distances": [[0.2]],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mismatched_response
        mock_post.return_value = mock_response

        with patch("src.core.retrieval.logger") as mock_logger:
            chunks = vector_store_client.query(
                query_embedding=sample_query_embedding, request_id="test_model_mismatch"
            )

            # Verify warning was logged
            assert mock_logger.warning.called
            warning_args = mock_logger.warning.call_args
            assert "mismatch" in str(warning_args).lower()

    @patch("src.core.retrieval.requests.get")
    def test_health_check_healthy(self, mock_get, vector_store_client):
        """Test health check when vector store is accessible."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        health = vector_store_client.health_check()

        assert health["status"] == "healthy"
        assert health["accessible"] is True
        assert health["vector_store_url"] == "http://localhost:8001"

    @patch("src.core.retrieval.requests.get")
    def test_health_check_unhealthy(self, mock_get, vector_store_client):
        """Test health check when vector store is unreachable."""
        mock_get.side_effect = ConnectionError("Connection refused")

        health = vector_store_client.health_check()

        assert health["status"] == "unhealthy"
        assert health["accessible"] is False
        assert "error" in health


class TestMetadataExtraction:
    """Test suite for metadata extraction logic."""

    @patch("src.core.retrieval.get_settings")
    def test_extract_metadata_complete(self, mock_settings):
        """Test extraction with all metadata fields present."""
        mock_settings.return_value = Mock()
        client = VectorStoreClient()

        chromadb_metadata = {
            "source_doc": "complete.pdf",
            "source_type": "pdf",
            "page_number": 10,
            "section_title": "Section A",
            "chunk_index": 5,
            "embedding_model": "all-MiniLM-L6-v2",
        }

        metadata = client._extract_metadata(
            chromadb_metadata, chunk_id="chunk_test_1", request_id="test_extract"
        )

        assert metadata["document_name"] == "complete.pdf"
        assert metadata["source_type"] == "pdf"
        assert metadata["page_number"] == 10
        assert metadata["section"] == "Section A"
        assert metadata["chunk_index"] == 5

    @patch("src.core.retrieval.get_settings")
    def test_extract_metadata_minimal(self, mock_settings):
        """Test extraction with only required fields."""
        mock_settings.return_value = Mock()
        client = VectorStoreClient()

        chromadb_metadata = {"source_doc": "minimal.txt", "chunk_index": 0}

        metadata = client._extract_metadata(
            chromadb_metadata, chunk_id="chunk_minimal", request_id="test_minimal"
        )

        assert metadata["document_name"] == "minimal.txt"
        assert metadata["chunk_index"] == 0
        assert "page_number" not in metadata
        assert "section" not in metadata

    @patch("src.core.retrieval.get_settings")
    def test_extract_metadata_missing_required(self, mock_settings):
        """Test extraction with missing required fields (uses defaults)."""
        mock_settings.return_value = Mock()
        client = VectorStoreClient()

        chromadb_metadata = {}

        metadata = client._extract_metadata(
            chromadb_metadata, chunk_id="chunk_empty", request_id="test_empty"
        )

        # Verify defaults applied
        assert metadata["document_name"] == "Unknown"
        assert metadata["chunk_index"] == 0
        assert metadata["source_type"] == "unknown"
