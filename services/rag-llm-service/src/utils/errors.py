"""Custom exception classes for RAG LLM Service."""


class RAGServiceError(Exception):
    """Base exception for RAG service errors."""

    pass


class VectorStoreUnavailable(RAGServiceError):
    """Raised when ChromaDB vector store is unavailable.

    This can occur due to:
    - Connection timeout
    - Network errors
    - Vector store service not running
    - Invalid URL configuration
    """

    def __init__(
        self, message: str = "Vector store is unavailable", details: str = None
    ):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class OllamaUnavailable(RAGServiceError):
    """Raised when Ollama LLM service is unavailable.

    This can occur due to:
    - Ollama service not running
    - Model not loaded
    - Connection timeout
    - Network errors
    """

    def __init__(
        self, message: str = "Ollama service is unavailable", details: str = None
    ):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class EmbeddingAPIUnavailable(RAGServiceError):
    """Raised when HR Data Pipeline embedding API is unavailable.

    This can occur due to:
    - Embedding service not running
    - Connection timeout
    - Network errors
    - Invalid API URL configuration
    """

    def __init__(
        self, message: str = "Embedding API is unavailable", details: str = None
    ):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class NoCitationsFound(RAGServiceError):
    """Raised when LLM generates an answer without citations.

    According to the constitution (Principle II: Transparency),
    all answers must include source citations. If the LLM fails
    to cite sources, the answer is rejected.
    """

    def __init__(self, message: str = "No citations found in generated answer"):
        super().__init__(message)


class InvalidQuery(RAGServiceError):
    """Raised when query input validation fails.

    This can occur due to:
    - Empty or whitespace-only question
    - Question too short (< 3 chars) or too long (> 1000 chars)
    - Invalid filter structure
    - Invalid max_results value
    """

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)

    def __str__(self):
        if self.field:
            return f"Invalid query field '{self.field}': {self.message}"
        return f"Invalid query: {self.message}"


class GenerationTimeout(RAGServiceError):
    """Raised when LLM generation exceeds timeout threshold.

    This can occur when:
    - LLM takes too long to generate response
    - Network latency is high
    - Model is overloaded
    """

    def __init__(
        self, message: str = "LLM generation timed out", timeout_seconds: int = None
    ):
        self.message = message
        self.timeout_seconds = timeout_seconds
        super().__init__(self.message)

    def __str__(self):
        if self.timeout_seconds:
            return f"{self.message} (timeout: {self.timeout_seconds}s)"
        return self.message


class EmbeddingDimensionMismatch(RAGServiceError):
    """Raised when embedding dimension doesn't match expected value.

    The all-MiniLM-L6-v2 model produces 384-dimensional embeddings.
    If the API returns a different dimension, this error is raised.
    """

    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        message = f"Embedding dimension mismatch: expected {expected}, got {actual}"
        super().__init__(message)


class LowConfidenceAnswer(RAGServiceError):
    """Raised when answer confidence is below threshold.

    When the average similarity score of retrieved chunks is below
    MIN_CONFIDENCE_THRESHOLD, the service returns "I don't know"
    instead of an uncertain answer.
    """

    def __init__(self, confidence: float, threshold: float):
        self.confidence = confidence
        self.threshold = threshold
        message = f"Answer confidence {confidence:.2f} below threshold {threshold:.2f}"
        super().__init__(message)
