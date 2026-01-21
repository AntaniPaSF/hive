"""
Unit tests for OllamaClient.
"""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout, ConnectionError, RequestException

from src.core.ollama_client import OllamaClient
from src.utils.errors import OllamaUnavailable, GenerationTimeout, InvalidQuery


@pytest.fixture
def ollama_client():
    """Create OllamaClient instance for testing."""
    return OllamaClient(
        host="http://localhost:11434",
        model="mistral:7b",
        timeout=30,
        max_retries=2,
        retry_delay=0.1,  # Short delay for tests
    )


@pytest.fixture
def sample_prompt():
    """Sample prompt for testing."""
    return """Answer the following question based on the context:
    
Context: Employees receive 20 days of vacation annually.

Question: How many vacation days do employees get?

Answer:"""


class TestOllamaClient:
    """Test OllamaClient functionality."""

    def test_initialization(self, ollama_client):
        """Test client initialization."""
        assert ollama_client.host == "http://localhost:11434"
        assert ollama_client.model == "mistral:7b"
        assert ollama_client.timeout == 30
        assert ollama_client.max_retries == 2
        assert ollama_client.generate_endpoint == "http://localhost:11434/api/generate"

    def test_custom_initialization(self):
        """Test client with custom parameters."""
        client = OllamaClient(
            host="http://custom-host:8080/",  # Test trailing slash removal
            model="llama3",
            timeout=60,
        )
        assert client.host == "http://custom-host:8080"
        assert client.model == "llama3"
        assert client.timeout == 60

    @patch("src.core.ollama_client.requests.post")
    def test_generate_success(self, mock_post, ollama_client, sample_prompt):
        """Test successful answer generation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "mistral:7b",
            "response": "Employees receive 20 days of vacation annually.",
            "done": True,
        }
        mock_post.return_value = mock_response

        result = ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert result == "Employees receive 20 days of vacation annually."
        mock_post.assert_called_once()

        # Verify request payload
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["model"] == "mistral:7b"
        assert payload["prompt"] == sample_prompt
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.1

    @patch("src.core.ollama_client.requests.post")
    def test_generate_with_custom_params(self, mock_post, ollama_client, sample_prompt):
        """Test generation with custom parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test answer"}
        mock_post.return_value = mock_response

        ollama_client.generate(
            prompt=sample_prompt, request_id="test_123", temperature=0.7, max_tokens=500
        )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["options"]["temperature"] == 0.7
        assert payload["options"]["num_predict"] == 500

    def test_generate_empty_prompt(self, ollama_client):
        """Test error on empty prompt."""
        with pytest.raises(InvalidQuery) as exc_info:
            ollama_client.generate(prompt="", request_id="test_123")

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_generate_whitespace_prompt(self, ollama_client):
        """Test error on whitespace-only prompt."""
        with pytest.raises(InvalidQuery):
            ollama_client.generate(prompt="   \n  ", request_id="test_123")

    @patch("src.core.ollama_client.requests.post")
    def test_generate_model_not_found(self, mock_post, ollama_client, sample_prompt):
        """Test handling of 404 model not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        with pytest.raises(OllamaUnavailable) as exc_info:
            ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert "not found" in str(exc_info.value).lower()
        assert "mistral:7b" in str(exc_info.value)

    @patch("src.core.ollama_client.requests.post")
    @patch("src.core.ollama_client.time.sleep")  # Mock sleep to speed up tests
    def test_generate_retry_on_500(
        self, mock_sleep, mock_post, ollama_client, sample_prompt
    ):
        """Test retry logic on 500 server error."""
        # First two calls return 500, third succeeds
        mock_response_error = Mock()
        mock_response_error.status_code = 500

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"response": "Success after retry"}

        mock_post.side_effect = [
            mock_response_error,
            mock_response_error,
            mock_response_success,
        ]

        result = ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert result == "Success after retry"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2  # Two retries

    @patch("src.core.ollama_client.requests.post")
    @patch("src.core.ollama_client.time.sleep")
    def test_generate_retry_exhausted(
        self, mock_sleep, mock_post, ollama_client, sample_prompt
    ):
        """Test failure after retry exhaustion."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        with pytest.raises(OllamaUnavailable) as exc_info:
            ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert "server error" in str(exc_info.value).lower()
        assert mock_post.call_count == 3  # Initial + 2 retries

    @patch("src.core.ollama_client.requests.post")
    def test_generate_timeout(self, mock_post, ollama_client, sample_prompt):
        """Test timeout handling."""
        mock_post.side_effect = Timeout("Connection timeout")

        with pytest.raises(GenerationTimeout) as exc_info:
            ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert "timeout" in str(exc_info.value).lower()
        assert "30s" in str(exc_info.value)

    @patch("src.core.ollama_client.requests.post")
    @patch("src.core.ollama_client.time.sleep")
    def test_generate_connection_error_retry(
        self, mock_sleep, mock_post, ollama_client, sample_prompt
    ):
        """Test retry on connection error."""
        # First call fails, second succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"response": "Success"}

        mock_post.side_effect = [
            ConnectionError("Connection refused"),
            mock_response_success,
        ]

        result = ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert result == "Success"
        assert mock_post.call_count == 2

    @patch("src.core.ollama_client.requests.post")
    @patch("src.core.ollama_client.time.sleep")
    def test_generate_connection_error_exhausted(
        self, mock_sleep, mock_post, ollama_client, sample_prompt
    ):
        """Test connection error after retry exhaustion."""
        mock_post.side_effect = ConnectionError("Connection refused")

        with pytest.raises(OllamaUnavailable) as exc_info:
            ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert "failed to connect" in str(exc_info.value).lower()
        assert mock_post.call_count == 3  # Initial + 2 retries

    @patch("src.core.ollama_client.requests.post")
    def test_generate_empty_response(self, mock_post, ollama_client, sample_prompt):
        """Test handling of empty response from Ollama."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": ""}
        mock_post.return_value = mock_response

        with pytest.raises(OllamaUnavailable) as exc_info:
            ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert "empty response" in str(exc_info.value).lower()

    @patch("src.core.ollama_client.requests.post")
    def test_generate_request_exception(self, mock_post, ollama_client, sample_prompt):
        """Test handling of generic request exception."""
        mock_post.side_effect = RequestException("Unknown error")

        with pytest.raises(OllamaUnavailable) as exc_info:
            ollama_client.generate(prompt=sample_prompt, request_id="test_123")

        assert "request failed" in str(exc_info.value).lower()

    @patch("src.core.ollama_client.requests.get")
    def test_health_check_healthy(self, mock_get, ollama_client):
        """Test health check when service is healthy."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "mistral:7b"}, {"name": "llama3"}]
        }
        mock_get.return_value = mock_response

        result = ollama_client.health_check()

        assert result["status"] == "healthy"
        assert result["model"] == "mistral:7b"
        assert result["model_available"] is True
        assert "mistral:7b" in result["available_models"]

    @patch("src.core.ollama_client.requests.get")
    def test_health_check_model_not_available(self, mock_get, ollama_client):
        """Test health check when model is not available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3"}  # mistral:7b not in list
            ]
        }
        mock_get.return_value = mock_response

        result = ollama_client.health_check()

        assert result["status"] == "degraded"
        assert result["model_available"] is False

    @patch("src.core.ollama_client.requests.get")
    def test_health_check_connection_error(self, mock_get, ollama_client):
        """Test health check on connection error."""
        mock_get.side_effect = ConnectionError("Connection refused")

        result = ollama_client.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "connection refused" in result["error"].lower()

    @patch("src.core.ollama_client.requests.get")
    def test_health_check_timeout(self, mock_get, ollama_client):
        """Test health check on timeout."""
        mock_get.side_effect = Timeout("Request timeout")

        result = ollama_client.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestExponentialBackoff:
    """Test exponential backoff behavior."""

    @patch("src.core.ollama_client.requests.post")
    @patch("src.core.ollama_client.time.sleep")
    def test_backoff_timing(self, mock_sleep, mock_post, sample_prompt):
        """Test exponential backoff delay calculation."""
        client = OllamaClient(
            host="http://localhost:11434", max_retries=3, retry_delay=1.0
        )

        mock_post.side_effect = ConnectionError("Connection refused")

        with pytest.raises(OllamaUnavailable):
            client.generate(prompt=sample_prompt, request_id="test_123")

        # Verify exponential backoff: 1s, 2s, 4s
        assert mock_sleep.call_count == 3
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1.0, 2.0, 4.0]
