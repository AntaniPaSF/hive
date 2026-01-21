"""Embedding API client for HR Data Pipeline integration."""

import time
from typing import Optional
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from ..utils.errors import EmbeddingAPIUnavailable, EmbeddingDimensionMismatch
from ..utils.validators import validate_embedding_dimension, validate_question
from ..utils.logger import get_logger
from ..config import get_settings


logger = get_logger(__name__)


class EmbeddingAPIClient:
    """Client for HR Data Pipeline embedding API.

    Generates 384-dimensional query embeddings using the same all-MiniLM-L6-v2
    model as the HR Data Pipeline to ensure embedding compatibility.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_backoff: Optional[int] = None,
    ):
        """Initialize embedding API client.

        Args:
            api_url: Embedding API endpoint URL (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
            max_retries: Maximum retry attempts (defaults to config)
            retry_backoff: Retry backoff multiplier (defaults to config)
        """
        settings = get_settings()
        self.api_url = api_url or settings.embedding_api_url
        self.timeout = timeout or settings.embedding_api_timeout
        self.max_retries = max_retries or settings.max_retries
        self.retry_backoff = retry_backoff or settings.retry_backoff
        self.expected_dimension = settings.embedding_dimension

        logger.info(
            "EmbeddingAPIClient initialized",
            extra={
                "component": "embedding",
                "event": "client_init",
                "data": {
                    "api_url": self.api_url,
                    "timeout": self.timeout,
                    "max_retries": self.max_retries,
                    "expected_dimension": self.expected_dimension,
                },
            },
        )

    def embed(self, text: str, request_id: Optional[str] = None) -> list[float]:
        """Generate 384-dimensional embedding for query text.

        Calls HR Data Pipeline embedding API to ensure model consistency.
        Implements exponential backoff retry on transient failures.

        Args:
            text: Query text to embed (3-1000 chars)
            request_id: Request ID for logging/tracing

        Returns:
            384-dimensional embedding vector as list of floats

        Raises:
            EmbeddingAPIUnavailable: API connection failed or timeout
            EmbeddingDimensionMismatch: API returned non-384-dim vector
        """
        start_time = time.time()

        # Validate input text
        validate_question(text)

        logger.info(
            "Generating embedding",
            extra={
                "component": "embedding",
                "event": "embed_request",
                "request_id": request_id,
                "data": {"text_length": len(text), "api_url": self.api_url},
            },
        )

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Call embedding API
                response = requests.post(
                    self.api_url,
                    json={"text": text},
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )

                # Handle HTTP errors
                if response.status_code == 404:
                    error_msg = f"Embedding API endpoint not found: {self.api_url}"
                    logger.error(
                        error_msg,
                        extra={
                            "component": "embedding",
                            "event": "api_not_found",
                            "request_id": request_id,
                            "error": {"type": "NotFound", "status_code": 404},
                        },
                    )
                    raise EmbeddingAPIUnavailable(
                        message=error_msg,
                        details={"api_url": self.api_url, "status_code": 404},
                    )

                if response.status_code >= 500:
                    error_msg = f"Embedding API server error: {response.status_code}"
                    logger.warning(
                        f"{error_msg} (attempt {attempt + 1}/{self.max_retries})",
                        extra={
                            "component": "embedding",
                            "event": "api_server_error",
                            "request_id": request_id,
                            "error": {
                                "type": "ServerError",
                                "status_code": response.status_code,
                                "attempt": attempt + 1,
                            },
                        },
                    )
                    last_error = EmbeddingAPIUnavailable(
                        message=error_msg,
                        details={
                            "status_code": response.status_code,
                            "attempt": attempt + 1,
                        },
                    )

                    # Retry on 5xx errors
                    if attempt < self.max_retries - 1:
                        backoff_seconds = self.retry_backoff**attempt
                        logger.info(
                            f"Retrying in {backoff_seconds}s...",
                            extra={
                                "component": "embedding",
                                "event": "retry_backoff",
                                "request_id": request_id,
                                "data": {"backoff_seconds": backoff_seconds},
                            },
                        )
                        time.sleep(backoff_seconds)
                        continue
                    else:
                        raise last_error

                response.raise_for_status()
                result = response.json()

                # Extract embedding vector
                embedding = result.get("embedding")
                if not embedding:
                    error_msg = "Embedding API response missing 'embedding' field"
                    logger.error(
                        error_msg,
                        extra={
                            "component": "embedding",
                            "event": "invalid_response",
                            "request_id": request_id,
                            "error": {"type": "InvalidResponse", "response": result},
                        },
                    )
                    raise EmbeddingAPIUnavailable(
                        message=error_msg, details={"response": result}
                    )

                # Validate dimension
                try:
                    validate_embedding_dimension(embedding)
                except EmbeddingDimensionMismatch as e:
                    logger.error(
                        "Embedding dimension mismatch from API",
                        extra={
                            "component": "embedding",
                            "event": "dimension_mismatch",
                            "request_id": request_id,
                            "error": {
                                "type": "DimensionMismatch",
                                "expected": self.expected_dimension,
                                "actual": len(embedding),
                            },
                        },
                    )
                    raise e

                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    "Embedding generated successfully",
                    extra={
                        "component": "embedding",
                        "event": "embed_success",
                        "request_id": request_id,
                        "data": {
                            "dimension": len(embedding),
                            "elapsed_ms": elapsed_ms,
                            "attempts": attempt + 1,
                        },
                    },
                )

                return embedding

            except Timeout:
                error_msg = f"Embedding API timeout after {self.timeout}s"
                logger.warning(
                    f"{error_msg} (attempt {attempt + 1}/{self.max_retries})",
                    extra={
                        "component": "embedding",
                        "event": "api_timeout",
                        "request_id": request_id,
                        "error": {
                            "type": "Timeout",
                            "timeout": self.timeout,
                            "attempt": attempt + 1,
                        },
                    },
                )
                last_error = EmbeddingAPIUnavailable(
                    message=error_msg,
                    details={"timeout": self.timeout, "attempt": attempt + 1},
                )

                # Retry on timeout
                if attempt < self.max_retries - 1:
                    backoff_seconds = self.retry_backoff**attempt
                    logger.info(
                        f"Retrying in {backoff_seconds}s...",
                        extra={
                            "component": "embedding",
                            "event": "retry_backoff",
                            "request_id": request_id,
                            "data": {"backoff_seconds": backoff_seconds},
                        },
                    )
                    time.sleep(backoff_seconds)
                    continue
                else:
                    raise last_error

            except ConnectionError as e:
                error_msg = f"Failed to connect to embedding API: {str(e)}"
                logger.warning(
                    f"{error_msg} (attempt {attempt + 1}/{self.max_retries})",
                    extra={
                        "component": "embedding",
                        "event": "connection_error",
                        "request_id": request_id,
                        "error": {
                            "type": "ConnectionError",
                            "details": str(e),
                            "attempt": attempt + 1,
                        },
                    },
                )
                last_error = EmbeddingAPIUnavailable(
                    message=error_msg,
                    details={"api_url": self.api_url, "attempt": attempt + 1},
                )

                # Retry on connection errors
                if attempt < self.max_retries - 1:
                    backoff_seconds = self.retry_backoff**attempt
                    logger.info(
                        f"Retrying in {backoff_seconds}s...",
                        extra={
                            "component": "embedding",
                            "event": "retry_backoff",
                            "request_id": request_id,
                            "data": {"backoff_seconds": backoff_seconds},
                        },
                    )
                    time.sleep(backoff_seconds)
                    continue
                else:
                    raise last_error

            except RequestException as e:
                error_msg = f"Embedding API request failed: {str(e)}"
                logger.error(
                    error_msg,
                    extra={
                        "component": "embedding",
                        "event": "request_error",
                        "request_id": request_id,
                        "error": {
                            "type": "RequestError",
                            "details": str(e),
                            "attempt": attempt + 1,
                        },
                    },
                )
                raise EmbeddingAPIUnavailable(
                    message=error_msg, details={"error": str(e)}
                )

        # Should not reach here, but raise last error if retries exhausted
        if last_error:
            raise last_error

        raise EmbeddingAPIUnavailable(
            message="Embedding API failed after all retry attempts",
            details={"max_retries": self.max_retries},
        )

    def health_check(self) -> dict:
        """Check embedding API connectivity and status.

        Returns:
            Health status dictionary with connection details
        """
        try:
            # Try a simple health check or minimal request
            response = requests.get(
                f"{self.api_url.rsplit('/', 1)[0]}/health", timeout=5
            )
            response.raise_for_status()

            return {
                "status": "healthy",
                "api_url": self.api_url,
                "accessible": True,
                "expected_dimension": self.expected_dimension,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "api_url": self.api_url,
                "accessible": False,
                "expected_dimension": self.expected_dimension,
                "error": str(e),
            }
