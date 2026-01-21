"""
Unit tests for input validation functions.

Tests validation logic for questions, filters, and other inputs.
"""

import pytest

from src.utils.validators import (
    validate_question,
    validate_filters,
    validate_confidence,
    validate_embedding_dimension,
    sanitize_excerpt,
)
from src.utils.errors import InvalidQuery, EmbeddingDimensionMismatch


class TestQuestionValidation:
    """Test question validation."""

    def test_valid_question(self):
        """Test validation passes for valid question."""
        question = "What is the vacation policy?"
        result = validate_question(question)
        assert result == question

    def test_question_minimum_length(self):
        """Test question must be at least 3 characters."""
        result = validate_question("Why")
        assert result == "Why"

        with pytest.raises(InvalidQuery) as exc_info:
            validate_question("Hi")
        assert "too short" in str(exc_info.value).lower()

    def test_question_maximum_length(self):
        """Test question cannot exceed 1000 characters."""
        valid_long_question = "x" * 1000
        result = validate_question(valid_long_question)
        assert len(result) == 1000

        invalid_long_question = "x" * 1001
        with pytest.raises(InvalidQuery) as exc_info:
            validate_question(invalid_long_question)
        assert "too long" in str(exc_info.value).lower()

    def test_empty_question_fails(self):
        """Test empty question fails validation."""
        with pytest.raises(InvalidQuery) as exc_info:
            validate_question("")
        assert "cannot be empty" in str(exc_info.value).lower()

    def test_whitespace_only_question_fails(self):
        """Test whitespace-only question fails validation."""
        with pytest.raises(InvalidQuery):
            validate_question("   ")

    def test_none_question_fails(self):
        """Test None question fails validation."""
        with pytest.raises(InvalidQuery):
            validate_question(None)


class TestQuestionSanitization:
    """Test question sanitization (integrated in validate_question)."""

    def test_strip_whitespace(self):
        """Test whitespace is stripped during validation."""
        result = validate_question("  Test question  ")
        assert result == "Test question"

    def test_leading_trailing_whitespace(self):
        """Test leading/trailing whitespace removed."""
        result = validate_question("\n\t  Test question  \n\t")
        assert result == "Test question"


class TestConfidenceValidation:
    """Test confidence score validation."""

    def test_valid_confidence_above_threshold(self):
        """Test confidence above threshold returns True."""
        assert validate_confidence(0.8, 0.5) is True

    def test_valid_confidence_equals_threshold(self):
        """Test confidence equal to threshold returns True."""
        assert validate_confidence(0.5, 0.5) is True

    def test_confidence_below_threshold(self):
        """Test confidence below threshold returns False."""
        assert validate_confidence(0.3, 0.5) is False

    def test_invalid_confidence_out_of_range(self):
        """Test invalid confidence score raises error."""
        with pytest.raises(InvalidQuery):
            validate_confidence(1.5, 0.5)

        with pytest.raises(InvalidQuery):
            validate_confidence(-0.1, 0.5)


class TestFilterValidation:
    """Test filter validation."""

    def test_valid_filters(self):
        """Test validation passes for valid filters."""
        filters = {"source": "policy.pdf", "max_results": 5}
        result = validate_filters(filters)
        assert result == filters

    def test_none_filters_allowed(self):
        """Test None filters returns None."""
        assert validate_filters(None) is None

    def test_max_results_range(self):
        """Test max_results must be between 1 and 10."""
        # Valid values
        assert validate_filters({"max_results": 1}) == {"max_results": 1}
        assert validate_filters({"max_results": 5}) == {"max_results": 5}
        assert validate_filters({"max_results": 10}) == {"max_results": 10}

        # Invalid values
        with pytest.raises(InvalidQuery) as exc_info:
            validate_filters({"max_results": 0})
        assert "at least 1" in str(exc_info.value)

        with pytest.raises(InvalidQuery):
            validate_filters({"max_results": 11})

    def test_source_filter_type(self):
        """Test source filter must be string."""
        result = validate_filters({"source": "doc.pdf"})
        assert result == {"source": "doc.pdf"}

        with pytest.raises(InvalidQuery) as exc_info:
            validate_filters({"source": 123})
        assert "must be a string" in str(exc_info.value)

    def test_empty_filters(self):
        """Test empty filters dict is valid."""
        assert validate_filters({}) == {}

    def test_none_filters(self):
        """Test None filters returns None."""
        assert validate_filters(None) is None


class TestExcerptSanitization:
    """Test excerpt text sanitization."""

    def test_sanitize_excerpt_basic(self):
        """Test basic excerpt sanitization."""
        result = sanitize_excerpt("  This is an excerpt  ")
        assert result == "This is an excerpt"

    def test_sanitize_excerpt_truncate(self):
        """Test long excerpt is truncated to max_length."""
        long_text = "a" * 250
        result = sanitize_excerpt(long_text, max_length=200)
        assert len(result) == 200
        assert result.endswith("...")

    def test_sanitize_excerpt_short(self):
        """Test short excerpt is not truncated."""
        short_text = "Short excerpt"
        result = sanitize_excerpt(short_text, max_length=200)
        assert result == short_text


class TestEmbeddingDimensionValidation:
    """Test embedding dimension validation."""

    def test_valid_dimension(self):
        """Test validation passes for 384 dimensions."""
        embedding = [0.1] * 384
        assert validate_embedding_dimension(embedding) is True

    def test_invalid_dimension(self):
        """Test validation fails for wrong dimensions."""
        embedding_128 = [0.1] * 128
        with pytest.raises(EmbeddingDimensionMismatch) as exc_info:
            validate_embedding_dimension(embedding_128)
        assert "384" in str(exc_info.value)

        embedding_768 = [0.1] * 768
        with pytest.raises(EmbeddingDimensionMismatch):
            validate_embedding_dimension(embedding_768)

    def test_empty_embedding(self):
        """Test validation fails for empty embedding."""
        with pytest.raises(EmbeddingDimensionMismatch):
            validate_embedding_dimension([])

    def test_custom_dimension(self):
        """Test validation with custom expected dimension."""
        embedding_512 = [0.1] * 512
        assert validate_embedding_dimension(embedding_512, expected_dim=512) is True

        with pytest.raises(EmbeddingDimensionMismatch):
            validate_embedding_dimension(embedding_512, expected_dim=384)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_question_with_newlines(self):
        """Test question with newlines is handled."""
        question = "What is\nthe policy?"
        result = validate_question(question)
        # Whitespace is stripped, but newlines may remain
        assert len(result) >= 3

    def test_question_with_special_unicode(self):
        """Test question with unicode characters."""
        question = "What is the vacation policy for café employees?"
        result = validate_question(question)
        assert "café" in result

    def test_filters_with_extra_keys(self):
        """Test filters with unknown keys are passed through."""
        filters = {"source": "doc.pdf", "extra_key": "value"}
        # Unknown keys are allowed and returned
        result = validate_filters(filters)
        assert result == filters
