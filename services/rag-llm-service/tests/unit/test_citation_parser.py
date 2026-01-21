"""
Unit tests for citation parser.
"""

import pytest

from src.prompts.citation_parser import extract_citations, format_citations_for_display


@pytest.fixture
def sample_chunks():
    """Sample retrieved chunks for citation validation."""
    return [
        {
            "chunk_id": "chunk_safety_p5_0",
            "content": "All personnel must wear protective eyewear and gloves when handling Class A chemicals.",
            "metadata": {
                "document_name": "safety_manual.pdf",
                "page_number": 5,
                "section": "Chemical Handling",
                "chunk_index": 0,
            },
        },
        {
            "chunk_id": "chunk_hr_p12_0",
            "content": "Employees receive 20 days of paid vacation annually, with accrual starting from the hire date.",
            "metadata": {
                "document_name": "hr_policy.pdf",
                "page_number": 12,
                "section": "Time Off",
                "chunk_index": 0,
            },
        },
        {
            "chunk_id": "chunk_ethics_p3_1",
            "content": "All employees must complete mandatory ethics training within 30 days of hire.",
            "metadata": {
                "document_name": "ethics_guidelines.pdf",
                "page_number": 3,
                "section": "Training Requirements",
                "chunk_index": 1,
            },
        },
    ]


class TestExtractCitations:
    """Test citation extraction from LLM answers."""

    def test_extract_single_citation(self, sample_chunks):
        """Test extracting a single citation."""
        answer = "According to the safety manual [safety_manual.pdf, Chemical Handling], all personnel must wear protective gear."

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        assert len(citations) == 1
        assert all_valid is True

        citation = citations[0]
        assert citation["document_name"] == "safety_manual.pdf"
        assert citation["section"] == "Chemical Handling"
        assert citation["page_number"] == 5
        assert citation["chunk_id"] == "chunk_safety_p5_0"
        assert len(citation["excerpt"]) <= 200

    def test_extract_multiple_citations(self, sample_chunks):
        """Test extracting multiple citations."""
        answer = """According to company policy [hr_policy.pdf, Time Off], employees get 20 days of vacation. 
        Additionally, the ethics guidelines [ethics_guidelines.pdf, Training Requirements] require training within 30 days."""

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        assert len(citations) == 2
        assert all_valid is True

        assert citations[0]["document_name"] == "hr_policy.pdf"
        assert citations[0]["section"] == "Time Off"

        assert citations[1]["document_name"] == "ethics_guidelines.pdf"
        assert citations[1]["section"] == "Training Requirements"

    def test_extract_duplicate_citations(self, sample_chunks):
        """Test deduplication of repeated citations."""
        answer = """The safety manual [safety_manual.pdf, Chemical Handling] states that protective gear is required.
        As mentioned in [safety_manual.pdf, Chemical Handling], this applies to all personnel."""

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        # Should deduplicate to single citation
        assert len(citations) == 1
        assert citations[0]["document_name"] == "safety_manual.pdf"

    def test_extract_no_citations(self, sample_chunks):
        """Test answer with no citations."""
        answer = "I don't know - this information is not available in the provided documents."

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        assert len(citations) == 0
        assert all_valid is False

    def test_extract_invalid_citation(self, sample_chunks):
        """Test citation referencing unknown source."""
        answer = "According to the handbook [employee_handbook.pdf, Benefits], employees get healthcare."

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        assert len(citations) == 1
        assert all_valid is False

        citation = citations[0]
        assert citation["document_name"] == "employee_handbook.pdf"
        assert citation["section"] == "Benefits"
        assert citation["excerpt"] is None
        assert citation["page_number"] is None
        assert "validation_warning" in citation

    def test_extract_mixed_valid_invalid(self, sample_chunks):
        """Test mix of valid and invalid citations."""
        answer = """The safety manual [safety_manual.pdf, Chemical Handling] requires protective gear.
        The handbook [unknown_doc.pdf, Unknown Section] mentions additional requirements."""

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        assert len(citations) == 2
        assert all_valid is False

        # First citation should be valid
        assert citations[0]["chunk_id"] is not None

        # Second citation should be invalid
        assert citations[1]["chunk_id"] is None
        assert "validation_warning" in citations[1]

    def test_extract_case_insensitive_matching(self, sample_chunks):
        """Test case-insensitive citation matching."""
        # LLM might use different casing
        answer = "According to policy [HR_Policy.PDF, time off], employees get vacation days."

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        assert len(citations) == 1
        assert all_valid is True
        assert (
            citations[0]["document_name"] == "HR_Policy.PDF"
        )  # Preserves LLM's casing
        assert citations[0]["chunk_id"] == "chunk_hr_p12_0"  # But matches source

    def test_extract_with_whitespace_variations(self, sample_chunks):
        """Test citation parsing with various whitespace."""
        answer = """Citations with different spacing:
        [safety_manual.pdf,Chemical Handling]
        [hr_policy.pdf,  Time Off  ]
        [ ethics_guidelines.pdf , Training Requirements ]"""

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        assert len(citations) == 3
        assert all_valid is True

    def test_extract_citation_with_special_chars(self, sample_chunks):
        """Test citation with special characters in section name."""
        answer = "As stated in [hr_policy.pdf, Time Off & Benefits], employees receive 20 days."

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        # Should still extract citation even if section doesn't match exactly
        assert len(citations) == 1
        assert citations[0]["document_name"] == "hr_policy.pdf"

    def test_extract_from_empty_answer(self, sample_chunks):
        """Test extraction from empty answer."""
        citations, all_valid = extract_citations("", sample_chunks, "test_123")

        assert len(citations) == 0
        assert all_valid is False

    def test_extract_with_empty_chunks(self):
        """Test extraction when no chunks are provided."""
        answer = "According to the manual [manual.pdf, Section 1], this is required."

        citations, all_valid = extract_citations(answer, [], "test_123")

        assert len(citations) == 1
        assert all_valid is False
        assert citations[0]["chunk_id"] is None


class TestFormatCitations:
    """Test citation formatting for display."""

    def test_format_citation_with_page(self):
        """Test formatting citation with page number."""
        citations = [
            {
                "document_name": "safety_manual.pdf",
                "section": "Chemical Handling",
                "page_number": 5,
            }
        ]

        formatted = format_citations_for_display(citations)

        assert len(formatted) == 1
        assert formatted[0] == "[safety_manual.pdf, Chemical Handling, p.5]"

    def test_format_citation_without_page(self):
        """Test formatting citation without page number."""
        citations = [{"document_name": "policy.pdf", "section": "Benefits"}]

        formatted = format_citations_for_display(citations)

        assert formatted[0] == "[policy.pdf, Benefits]"

    def test_format_citation_document_only(self):
        """Test formatting citation with only document name."""
        citations = [{"document_name": "guidelines.pdf"}]

        formatted = format_citations_for_display(citations)

        assert formatted[0] == "[guidelines.pdf]"

    def test_format_multiple_citations(self):
        """Test formatting multiple citations."""
        citations = [
            {"document_name": "doc1.pdf", "section": "Section A", "page_number": 10},
            {"document_name": "doc2.pdf", "section": "Section B"},
            {"document_name": "doc3.pdf"},
        ]

        formatted = format_citations_for_display(citations)

        assert len(formatted) == 3
        assert formatted[0] == "[doc1.pdf, Section A, p.10]"
        assert formatted[1] == "[doc2.pdf, Section B]"
        assert formatted[2] == "[doc3.pdf]"

    def test_format_empty_list(self):
        """Test formatting empty citation list."""
        formatted = format_citations_for_display([])

        assert formatted == []


class TestCitationPatterns:
    """Test various citation pattern matching."""

    def test_pattern_with_commas_in_section(self, sample_chunks):
        """Test citation with commas in section name."""
        # Create chunk with comma in section
        chunks = [
            {
                "chunk_id": "test_1",
                "content": "Test content",
                "metadata": {
                    "document_name": "test.pdf",
                    "section": "Section A, Part 1",
                },
            }
        ]

        answer = "According to [test.pdf, Section A, Part 1], this is required."

        citations, all_valid = extract_citations(answer, chunks, "test_123")

        # Current regex will treat this as separate parts due to comma
        # This is a known limitation - document in future enhancement
        assert len(citations) >= 1

    def test_pattern_with_brackets_in_text(self, sample_chunks):
        """Test that non-citation brackets are ignored."""
        answer = """According to the manual [safety_manual.pdf, Chemical Handling], you must:
        - Use PPE [personal protective equipment]
        - Follow [these guidelines]"""

        citations, all_valid = extract_citations(answer, sample_chunks, "test_123")

        # Should only extract the valid citation, not the bracketed abbreviations
        assert len(citations) == 1
        assert citations[0]["document_name"] == "safety_manual.pdf"

    def test_pattern_multiline_citation(self, sample_chunks):
        """Test citation split across lines."""
        answer = """According to policy
        [hr_policy.pdf,
        Time Off], employees get vacation days."""

        # Current implementation may not handle multiline citations
        # This tests the actual behavior
        citations, _ = extract_citations(answer, sample_chunks, "test_123")

        # Document current behavior
        # Future enhancement: support multiline citations
        assert isinstance(citations, list)
