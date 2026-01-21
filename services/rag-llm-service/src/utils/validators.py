"""Input validation functions for RAG LLM Service."""

from typing import Dict, Optional
from .errors import InvalidQuery, EmbeddingDimensionMismatch


def validate_question(question: str) -> str:
    """Validate and sanitize question input.

    Args:
        question: User's question string

    Returns:
        Sanitized question string

    Raises:
        InvalidQuery: If question is invalid

    Validation rules:
        - Must not be empty or whitespace-only
        - Minimum length: 3 characters
        - Maximum length: 1000 characters
        - Strips leading/trailing whitespace
    """
    if not question:
        raise InvalidQuery("Question cannot be empty", field="question")

    # Strip whitespace
    question = question.strip()

    if not question:
        raise InvalidQuery("Question cannot be whitespace-only", field="question")

    if len(question) < 3:
        raise InvalidQuery(
            f"Question too short: {len(question)} chars (minimum 3)", field="question"
        )

    if len(question) > 1000:
        raise InvalidQuery(
            f"Question too long: {len(question)} chars (maximum 1000)", field="question"
        )

    return question


def validate_filters(filters: Optional[Dict]) -> Optional[Dict]:
    """Validate query filters.

    Args:
        filters: Optional filter dictionary

    Returns:
        Validated filters or None

    Raises:
        InvalidQuery: If filters are invalid

    Supported filters:
        - source (str): Filter by document name
        - max_results (int): Maximum chunks to retrieve (1-10)
    """
    if filters is None:
        return None

    if not isinstance(filters, dict):
        raise InvalidQuery("Filters must be a dictionary", field="filters")

    # Validate max_results if present
    if "max_results" in filters:
        max_results = filters["max_results"]

        if not isinstance(max_results, int):
            raise InvalidQuery(
                "max_results must be an integer", field="filters.max_results"
            )

        if max_results < 1:
            raise InvalidQuery(
                f"max_results must be at least 1, got {max_results}",
                field="filters.max_results",
            )

        if max_results > 10:
            raise InvalidQuery(
                f"max_results cannot exceed 10, got {max_results}",
                field="filters.max_results",
            )

    # Validate source if present
    if "source" in filters:
        source = filters["source"]

        if not isinstance(source, str):
            raise InvalidQuery("source must be a string", field="filters.source")

        if not source.strip():
            raise InvalidQuery("source cannot be empty", field="filters.source")

    return filters


def validate_confidence(confidence: float, threshold: float) -> bool:
    """Validate if confidence meets threshold.

    Args:
        confidence: Calculated confidence score (0.0-1.0)
        threshold: Minimum acceptable confidence

    Returns:
        True if confidence >= threshold, False otherwise

    Raises:
        InvalidQuery: If confidence is out of range
    """
    if not 0.0 <= confidence <= 1.0:
        raise InvalidQuery(
            f"Confidence must be between 0.0 and 1.0, got {confidence}",
            field="confidence",
        )

    if not 0.0 <= threshold <= 1.0:
        raise InvalidQuery(
            f"Threshold must be between 0.0 and 1.0, got {threshold}", field="threshold"
        )

    return confidence >= threshold


def validate_embedding_dimension(embedding: list, expected_dim: int = 384) -> bool:
    """Validate embedding dimension matches expected value.

    Args:
        embedding: Embedding vector (list of floats)
        expected_dim: Expected dimension (default: 384 for all-MiniLM-L6-v2)

    Returns:
        True if dimension matches

    Raises:
        EmbeddingDimensionMismatch: If dimension doesn't match
    """
    actual_dim = len(embedding)

    if actual_dim != expected_dim:
        raise EmbeddingDimensionMismatch(expected=expected_dim, actual=actual_dim)

    return True


def sanitize_excerpt(excerpt: str, max_length: int = 200) -> str:
    """Sanitize and truncate excerpt text.

    Args:
        excerpt: Source excerpt text
        max_length: Maximum length (default: 200)

    Returns:
        Sanitized and truncated excerpt
    """
    # Strip whitespace
    excerpt = excerpt.strip()

    # Truncate if too long
    if len(excerpt) > max_length:
        excerpt = excerpt[: max_length - 3] + "..."

    return excerpt
