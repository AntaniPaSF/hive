"""
Ollama LLM Client for RAG answer generation.

This module provides the OllamaClient class for interacting with the Ollama API
to generate answers based on retrieved context chunks.
"""

import requests
from requests.exceptions import Timeout, ConnectionError, RequestException
from typing import Optional, Dict, Any, List
import time

from ..utils.logger import get_logger
from ..utils.errors import OllamaUnavailable, GenerationTimeout, InvalidQuery

logger = get_logger(__name__)


class OllamaClient:
    """
    Client for Ollama LLM API.

    Handles connection to Ollama, answer generation with retry logic,
    and error handling for timeouts and connection issues.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "mistral:7b",
        timeout: int = 30,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ):
        """
        Initialize Ollama client.

        Args:
            host: Ollama API host URL
            model: Model name to use (e.g., "mistral:7b", "llama3")
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Base delay between retries (seconds)
        """
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.generate_endpoint = f"{self.host}/api/generate"

        logger.info(
            "Initialized OllamaClient",
            extra={
                "component": "ollama_client",
                "event": "initialization",
                "data": {
                    "host": self.host,
                    "model": self.model,
                    "timeout": self.timeout,
                },
            },
        )

    def generate(
        self,
        prompt: str,
        request_id: str,
        stream: bool = False,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate answer from Ollama LLM.

        Args:
            prompt: Complete prompt including system instructions and context
            request_id: Unique request identifier for logging
            stream: Whether to stream the response (default: False)
            temperature: Sampling temperature (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum tokens to generate (None = model default)

        Returns:
            Generated text from the LLM

        Raises:
            OllamaUnavailable: If Ollama service is unreachable or returns error
            GenerationTimeout: If generation exceeds timeout
            InvalidQuery: If prompt is empty or invalid
        """
        if not prompt or not prompt.strip():
            raise InvalidQuery("Prompt cannot be empty")

        # Prepare request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {"temperature": temperature},
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        logger.info(
            "Generating answer with Ollama",
            extra={
                "component": "ollama_client",
                "event": "generate_start",
                "request_id": request_id,
                "data": {
                    "model": self.model,
                    "temperature": temperature,
                    "prompt_length": len(prompt),
                },
            },
        )

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self.generate_endpoint, json=payload, timeout=self.timeout
                )

                # Handle HTTP errors
                if response.status_code == 404:
                    error_msg = f"Model '{self.model}' not found in Ollama"
                    logger.error(
                        error_msg,
                        extra={
                            "component": "ollama_client",
                            "event": "model_not_found",
                            "request_id": request_id,
                            "error": {"status_code": 404, "model": self.model},
                        },
                    )
                    raise OllamaUnavailable(error_msg)

                if response.status_code >= 500:
                    error_msg = f"Ollama server error: {response.status_code}"
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2**attempt)
                        logger.warning(
                            f"Ollama server error, retrying in {delay}s",
                            extra={
                                "component": "ollama_client",
                                "event": "retry",
                                "request_id": request_id,
                                "data": {
                                    "attempt": attempt + 1,
                                    "status_code": response.status_code,
                                    "retry_delay": delay,
                                },
                            },
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise OllamaUnavailable(error_msg)

                response.raise_for_status()

                # Parse response
                result = response.json()
                generated_text = result.get("response", "")

                if not generated_text:
                    raise OllamaUnavailable("Empty response from Ollama")

                logger.info(
                    "Successfully generated answer",
                    extra={
                        "component": "ollama_client",
                        "event": "generate_success",
                        "request_id": request_id,
                        "data": {
                            "response_length": len(generated_text),
                            "attempt": attempt + 1,
                        },
                    },
                )

                return generated_text

            except Timeout as e:
                error_msg = f"Ollama request timeout after {self.timeout}s"
                logger.error(
                    error_msg,
                    extra={
                        "component": "ollama_client",
                        "event": "timeout",
                        "request_id": request_id,
                        "error": {"timeout": self.timeout, "attempt": attempt + 1},
                    },
                )
                raise GenerationTimeout(error_msg) from e

            except ConnectionError as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Connection error, retrying in {delay}s",
                        extra={
                            "component": "ollama_client",
                            "event": "retry",
                            "request_id": request_id,
                            "data": {"attempt": attempt + 1, "retry_delay": delay},
                        },
                    )
                    time.sleep(delay)
                    last_exception = e
                    continue
                else:
                    error_msg = f"Failed to connect to Ollama at {self.host}"
                    logger.error(
                        error_msg,
                        extra={
                            "component": "ollama_client",
                            "event": "connection_error",
                            "request_id": request_id,
                            "error": {"host": self.host, "attempts": attempt + 1},
                        },
                    )
                    raise OllamaUnavailable(error_msg) from e

            except RequestException as e:
                error_msg = f"Ollama request failed: {str(e)}"
                logger.error(
                    error_msg,
                    extra={
                        "component": "ollama_client",
                        "event": "request_error",
                        "request_id": request_id,
                        "error": {"message": str(e)},
                    },
                )
                raise OllamaUnavailable(error_msg) from e

        # Should not reach here, but handle retry exhaustion
        if last_exception:
            raise OllamaUnavailable(
                f"Failed after {self.max_retries + 1} attempts"
            ) from last_exception

    def health_check(self) -> Dict[str, Any]:
        """
        Check if Ollama service is healthy and model is available.

        Returns:
            Dictionary with health status information
        """
        try:
            # Try to list models to verify connectivity
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            response.raise_for_status()

            models_data = response.json()
            available_models = [m["name"] for m in models_data.get("models", [])]
            model_available = self.model in available_models

            return {
                "status": "healthy" if model_available else "degraded",
                "host": self.host,
                "model": self.model,
                "model_available": model_available,
                "available_models": available_models,
            }

        except (Timeout, ConnectionError, RequestException) as e:
            logger.error(
                "Ollama health check failed",
                extra={
                    "component": "ollama_client",
                    "event": "health_check_failed",
                    "error": {"message": str(e)},
                },
            )
            return {
                "status": "unhealthy",
                "host": self.host,
                "model": self.model,
                "error": str(e),
            }
