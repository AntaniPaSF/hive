"""
Unit tests for Pydantic schema models.

Tests data validation for Query, Answer, and Citation models.
"""

import pytest
from pydantic import ValidationError

from src.schemas.query import Query, Answer, Citation


class TestQueryModel:
    """Test Query model validation."""

    def test_valid_query(self):
        """Test creating a valid Query."""
        query = Query(question="What is the vacation policy?")
        assert query.question == "What is the vacation policy?"
        assert query.filters is None

    def test_query_with_filters(self):
        """Test Query with filters."""
        query = Query(
            question="What is the vacation policy?",
            filters={"source": "hr_policy.pdf", "max_results": 5},
        )
        assert query.filters["source"] == "hr_policy.pdf"
        assert query.filters["max_results"] == 5

    def test_question_too_short(self):
        """Test validation fails for question too short."""
        with pytest.raises(ValidationError) as exc_info:
            Query(question="Hi")

        assert "String should have at least 3 characters" in str(exc_info.value)

    def test_question_too_long(self):
        """Test validation fails for question too long."""
        long_question = "x" * 1001
        with pytest.raises(ValidationError) as exc_info:
            Query(question=long_question)

        assert "String should have at most 1000 characters" in str(exc_info.value)

    def test_question_empty_string(self):
        """Test validation fails for empty question."""
        with pytest.raises(ValidationError):
            Query(question="")

    def test_question_whitespace_only(self):
        """Test validation fails for whitespace-only question."""
        with pytest.raises(ValidationError):
            Query(question="   ")


class TestCitationModel:
    """Test Citation model validation."""

    def test_valid_citation_with_all_fields(self):
        """Test creating a valid Citation with all fields."""
        citation = Citation(
            document_name="safety_manual.pdf",
            excerpt="All personnel must wear protective equipment.",
            section="Safety Protocols",
            page_number=5,
            chunk_id="chunk_123",
        )
        assert citation.document_name == "safety_manual.pdf"
        assert citation.excerpt == "All personnel must wear protective equipment."
        assert citation.section == "Safety Protocols"
        assert citation.page_number == 5
        assert citation.chunk_id == "chunk_123"

    def test_valid_citation_minimal(self):
        """Test creating a Citation with only required fields."""
        citation = Citation(
            document_name="policy.pdf", excerpt="This is the relevant excerpt."
        )
        assert citation.document_name == "policy.pdf"
        assert citation.excerpt == "This is the relevant excerpt."
        assert citation.section is None
        assert citation.page_number is None
        assert citation.chunk_id is None

    def test_excerpt_too_long(self):
        """Test validation fails for excerpt too long."""
        long_excerpt = "x" * 201
        with pytest.raises(ValidationError) as exc_info:
            Citation(document_name="doc.pdf", excerpt=long_excerpt)

        assert "String should have at most 200 characters" in str(exc_info.value)

    def test_excerpt_empty_fails(self):
        """Test validation fails for empty excerpt."""
        with pytest.raises(ValidationError):
            Citation(document_name="doc.pdf", excerpt="")

    def test_missing_required_fields(self):
        """Test validation fails when required fields missing."""
        with pytest.raises(ValidationError):
            Citation(document_name="doc.pdf")  # Missing excerpt


class TestAnswerModel:
    """Test Answer model validation."""

    def test_valid_answer_with_citations(self, sample_citations):
        """Test creating a valid Answer with citations."""
        answer = Answer(
            answer="The vacation policy allows 20 days per year.",
            citations=sample_citations,
            confidence=0.87,
            message="Answer generated successfully",
            request_id="req_123",
            processing_time_ms=3420,
        )
        assert answer.answer == "The vacation policy allows 20 days per year."
        assert len(answer.citations) == 2
        assert answer.confidence == 0.87
        assert answer.processing_time_ms == 3420

    def test_valid_i_dont_know_answer(self):
        """Test creating a valid 'I don't know' answer."""
        answer = Answer(
            answer=None,
            citations=[],
            confidence=0.3,
            message="I don't know - low confidence",
            request_id="req_456",
            processing_time_ms=1250,
        )
        assert answer.answer is None
        assert len(answer.citations) == 0
        assert answer.confidence == 0.3
        assert "don't know" in answer.message.lower()

    def test_confidence_must_be_between_0_and_1(self):
        """Test confidence validation."""
        # Valid confidence values
        Answer(
            answer="Test",
            citations=[],
            confidence=0.0,
            message="",
            request_id="",
            processing_time_ms=100,
        )
        Answer(
            answer="Test",
            citations=[],
            confidence=0.5,
            message="",
            request_id="",
            processing_time_ms=100,
        )
        Answer(
            answer="Test",
            citations=[],
            confidence=1.0,
            message="",
            request_id="",
            processing_time_ms=100,
        )

        # Invalid confidence values
        with pytest.raises(ValidationError):
            Answer(
                answer="Test",
                citations=[],
                confidence=-0.1,
                message="",
                request_id="",
                processing_time_ms=100,
            )

        with pytest.raises(ValidationError):
            Answer(
                answer="Test",
                citations=[],
                confidence=1.5,
                message="",
                request_id="",
                processing_time_ms=100,
            )

    def test_processing_time_must_be_positive(self):
        """Test processing time must be positive."""
        # Valid
        Answer(
            answer="Test",
            citations=[],
            confidence=0.5,
            message="",
            request_id="",
            processing_time_ms=1,
        )

        # Invalid
        with pytest.raises(ValidationError):
            Answer(
                answer="Test",
                citations=[],
                confidence=0.5,
                message="",
                request_id="",
                processing_time_ms=-1,
            )

    def test_empty_citations_list(self):
        """Test Answer can have empty citations list."""
        answer = Answer(
            answer="Test answer",
            citations=[],
            confidence=0.6,
            message="Success",
            request_id="req_789",
            processing_time_ms=2000,
        )
        assert answer.citations == []


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_query_to_dict(self):
        """Test Query serialization to dict."""
        query = Query(question="Test question", filters={"max_results": 3})
        data = query.model_dump()

        assert data["question"] == "Test question"
        assert data["filters"]["max_results"] == 3

    def test_citation_to_dict(self, sample_citation):
        """Test Citation serialization to dict."""
        data = sample_citation.model_dump()

        assert data["document_name"] == "safety_manual.pdf"
        assert data["excerpt"] is not None
        assert data["section"] == "Chemical Handling"
        assert data["page_number"] == 5

    def test_answer_to_dict(self, sample_answer):
        """Test Answer serialization to dict."""
        data = sample_answer.model_dump()

        assert data["answer"] is not None
        assert len(data["citations"]) == 2
        assert data["confidence"] == 0.87
        assert data["request_id"] == "req_20260121_test123"

    def test_query_from_dict(self):
        """Test Query deserialization from dict."""
        data = {"question": "Test question", "filters": {"source": "doc.pdf"}}
        query = Query(**data)

        assert query.question == "Test question"
        assert query.filters["source"] == "doc.pdf"

    def test_citation_from_dict(self):
        """Test Citation deserialization from dict."""
        data = {
            "document_name": "policy.pdf",
            "excerpt": "Test excerpt",
            "section": "Section 1",
            "page_number": 10,
        }
        citation = Citation(**data)

        assert citation.document_name == "policy.pdf"
        assert citation.section == "Section 1"
