"""Unit tests for embedding API client."""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout, ConnectionError

from src.core.embedding_client import EmbeddingAPIClient
from src.utils.errors import EmbeddingAPIUnavailable, EmbeddingDimensionMismatch


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("src.core.embedding_client.get_settings") as mock:
        settings = Mock()
        settings.embedding_api_url = "http://localhost:8002/embed"
        settings.embedding_api_timeout = 5
        settings.max_retries = 3
        settings.retry_backoff = 2
        settings.embedding_dimension = 384
        mock.return_value = settings
        yield settings


@pytest.fixture
def embedding_client(mock_settings):
    """Create EmbeddingAPIClient instance for testing."""
    return EmbeddingAPIClient()


@pytest.fixture
def sample_text():
    """Sample query text for embedding."""
    return "What are the vacation policies for full-time employees?"


@pytest.fixture
def sample_embedding():
    """Sample 384-dimensional embedding vector."""
    return [0.1] * 384


class TestEmbeddingAPIClient:
    """Test suite for EmbeddingAPIClient."""

    def test_initialization(self, embedding_client, mock_settings):
        """Test client initialization with default settings."""
        assert embedding_client.api_url == "http://localhost:8002/embed"
        assert embedding_client.timeout == 5
        assert embedding_client.max_retries == 3
        assert embedding_client.retry_backoff == 2
        assert embedding_client.expected_dimension == 384

    def test_custom_initialization(self, mock_settings):
        """Test client initialization with custom parameters."""
        client = EmbeddingAPIClient(
            api_url="http://custom:9000/embed",
            timeout=10,
            max_retries=5,
            retry_backoff=3,
        )
        assert client.api_url == "http://custom:9000/embed"
        assert client.timeout == 10
        assert client.max_retries == 5
        assert client.retry_backoff == 3

    @patch("src.core.embedding_client.requests.post")
    def test_embed_success(
        self, mock_post, embedding_client, sample_text, sample_embedding
    ):
        """Test successful embedding generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": sample_embedding}
        mock_post.return_value = mock_response

        # Generate embedding
        embedding = embedding_client.embed(
            text=sample_text, request_id="test_request_123"
        )

        # Verify result
        assert len(embedding) == 384
        assert embedding == sample_embedding

        # Verify API call
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8002/embed"
        assert call_args[1]["json"]["text"] == sample_text
        assert call_args[1]["timeout"] == 5

    @patch("src.core.embedding_client.requests.post")
    def test_embed_dimension_mismatch(self, mock_post, embedding_client, sample_text):
        """Test embedding with wrong dimension."""
        # Mock API response with wrong dimension
        wrong_embedding = [0.1] * 256  # Wrong dimension
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": wrong_embedding}
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingDimensionMismatch) as exc_info:
            embedding_client.embed(text=sample_text, request_id="test_wrong_dim")

        assert "expected 384" in str(exc_info.value)
        assert "got 256" in str(exc_info.value)

    @patch("src.core.embedding_client.requests.post")
    def test_embed_missing_embedding_field(
        self, mock_post, embedding_client, sample_text
    ):
        """Test API response missing embedding field."""
        # Mock API response without embedding field
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}  # Missing 'embedding'
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingAPIUnavailable) as exc_info:
            embedding_client.embed(text=sample_text, request_id="test_missing_field")

        assert "missing 'embedding' field" in str(exc_info.value).lower()

    @patch("src.core.embedding_client.requests.post")
    def test_embed_timeout(self, mock_post, embedding_client, sample_text):
        """Test embedding timeout with retry."""
        mock_post.side_effect = Timeout("Request timeout")

        with pytest.raises(EmbeddingAPIUnavailable) as exc_info:
            embedding_client.embed(text=sample_text, request_id="test_timeout")

        # Verify retried 3 times
        assert mock_post.call_count == 3
        assert "timeout" in str(exc_info.value).lower()

    @patch("src.core.embedding_client.requests.post")
    @patch("src.core.embedding_client.time.sleep")  # Mock sleep to speed up test
    def test_embed_retry_on_500(
        self, mock_sleep, mock_post, embedding_client, sample_text, sample_embedding
    ):
        """Test retry on 500 server error with eventual success."""
        # First two calls return 500, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"embedding": sample_embedding}

        mock_post.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success,
        ]

        # Should succeed on third attempt
        embedding = embedding_client.embed(
            text=sample_text, request_id="test_retry_500"
        )

        assert len(embedding) == 384
        assert mock_post.call_count == 3
        # Verify exponential backoff sleeps: 2^0=1, 2^1=2
        assert mock_sleep.call_count == 2

    @patch("src.core.embedding_client.requests.post")
    @patch("src.core.embedding_client.time.sleep")
    def test_embed_retry_exhausted(
        self, mock_sleep, mock_post, embedding_client, sample_text
    ):
        """Test all retries exhausted."""
        # All attempts return 500
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingAPIUnavailable) as exc_info:
            embedding_client.embed(text=sample_text, request_id="test_retry_exhausted")

        # Verify retried max_retries times
        assert mock_post.call_count == 3
        assert "server error" in str(exc_info.value).lower()

    @patch("src.core.embedding_client.requests.post")
    def test_embed_404_not_found(self, mock_post, embedding_client, sample_text):
        """Test 404 endpoint not found (no retry)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingAPIUnavailable) as exc_info:
            embedding_client.embed(text=sample_text, request_id="test_404")

        # Should not retry on 404
        assert mock_post.call_count == 1
        assert "not found" in str(exc_info.value).lower()

    @patch("src.core.embedding_client.requests.post")
    @patch("src.core.embedding_client.time.sleep")
    def test_embed_connection_error_retry(
        self, mock_sleep, mock_post, embedding_client, sample_text, sample_embedding
    ):
        """Test retry on connection error with eventual success."""
        # First call fails, second succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"embedding": sample_embedding}

        mock_post.side_effect = [
            ConnectionError("Connection refused"),
            mock_response_success,
        ]

        embedding = embedding_client.embed(
            text=sample_text, request_id="test_conn_retry"
        )

        assert len(embedding) == 384
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1  # One backoff before retry

    @patch("src.core.embedding_client.requests.post")
    def test_embed_connection_error_exhausted(
        self, mock_post, embedding_client, sample_text
    ):
        """Test connection error with all retries exhausted."""
        mock_post.side_effect = ConnectionError("Connection refused")

        with pytest.raises(EmbeddingAPIUnavailable) as exc_info:
            embedding_client.embed(text=sample_text, request_id="test_conn_exhausted")

        assert mock_post.call_count == 3
        assert "connect" in str(exc_info.value).lower()

    @patch("src.core.embedding_client.requests.post")
    @patch("src.core.embedding_client.time.sleep")
    def test_exponential_backoff(
        self, mock_sleep, mock_post, embedding_client, sample_text
    ):
        """Test exponential backoff timing."""
        # All attempts timeout
        mock_post.side_effect = Timeout("Timeout")

        with pytest.raises(EmbeddingAPIUnavailable):
            embedding_client.embed(text=sample_text, request_id="test_backoff")

        # Verify exponential backoff: 2^0=1s, 2^1=2s
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1, 2]  # 2^0, 2^1

    def test_embed_invalid_text_too_short(self, embedding_client):
        """Test embedding with text too short."""
        with pytest.raises(Exception):  # InvalidQuery from validator
            embedding_client.embed(
                text="ab",  # Only 2 chars, need 3+
                request_id="test_short",
            )

    def test_embed_invalid_text_too_long(self, embedding_client):
        """Test embedding with text too long."""
        long_text = "a" * 1001  # Over 1000 char limit

        with pytest.raises(Exception):  # InvalidQuery from validator
            embedding_client.embed(text=long_text, request_id="test_long")

    @patch("src.core.embedding_client.requests.get")
    def test_health_check_healthy(self, mock_get, embedding_client):
        """Test health check when API is accessible."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        health = embedding_client.health_check()

        assert health["status"] == "healthy"
        assert health["accessible"] is True
        assert health["api_url"] == "http://localhost:8002/embed"
        assert health["expected_dimension"] == 384

    @patch("src.core.embedding_client.requests.get")
    def test_health_check_unhealthy(self, mock_get, embedding_client):
        """Test health check when API is unreachable."""
        mock_get.side_effect = ConnectionError("Connection refused")

        health = embedding_client.health_check()

        assert health["status"] == "unhealthy"
        assert health["accessible"] is False
        assert "error" in health


class TestRetryLogic:
    """Test suite for retry logic edge cases."""

    @patch("src.core.embedding_client.get_settings")
    @patch("src.core.embedding_client.requests.post")
    @patch("src.core.embedding_client.time.sleep")
    def test_custom_retry_settings(self, mock_sleep, mock_post, mock_settings):
        """Test retry with custom max_retries and backoff."""
        settings = Mock()
        settings.embedding_api_url = "http://localhost:8002/embed"
        settings.embedding_api_timeout = 5
        settings.max_retries = 5  # Custom: 5 retries
        settings.retry_backoff = 3  # Custom: 3x backoff
        settings.embedding_dimension = 384
        mock_settings.return_value = settings

        client = EmbeddingAPIClient()

        # All attempts fail
        mock_post.side_effect = Timeout("Timeout")

        with pytest.raises(EmbeddingAPIUnavailable):
            client.embed(text="Test query", request_id="test_custom")

        # Verify 5 attempts
        assert mock_post.call_count == 5

        # Verify exponential backoff: 3^0=1, 3^1=3, 3^2=9, 3^3=27
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1, 3, 9, 27]  # 3^0, 3^1, 3^2, 3^3

    @patch("src.core.embedding_client.get_settings")
    @patch("src.core.embedding_client.requests.post")
    def test_no_retry_on_request_exception(self, mock_post, mock_settings):
        """Test that RequestException (non-transient) doesn't retry."""
        settings = Mock()
        settings.embedding_api_url = "http://localhost:8002/embed"
        settings.embedding_api_timeout = 5
        settings.max_retries = 3
        settings.retry_backoff = 2
        settings.embedding_dimension = 384
        mock_settings.return_value = settings

        client = EmbeddingAPIClient()

        from requests.exceptions import RequestException

        mock_post.side_effect = RequestException("Invalid request")

        with pytest.raises(EmbeddingAPIUnavailable):
            client.embed(text="Test query", request_id="test_no_retry")

        # Should not retry on RequestException
        assert mock_post.call_count == 1
