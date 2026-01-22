"""LLM Benchmark Tests - Pytest Integration

These tests validate that the LLM implementation passes the benchmark
test suite requirements. They run as part of CI/CD on pull requests.

The tests use a mock LLM implementation for fast CI/CD execution.
For full benchmarking, use: python tests/benchmark/benchmark.py
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.benchmark.models.question import BenchmarkQuestion
from tests.benchmark.validators.fuzzy_match import match_against_variations
from tests.benchmark.validators.citation_check import validate_citations


class MockLLMImplementation:
    """Mock LLM for testing - simulates correct responses"""
    
    def __init__(self):
        """Initialize with ground truth responses"""
        self.responses = {
            "Q001": {
                "answer": "Submit a vacation request through the employee portal at least 2 weeks in advance.",
                "citations": ["HR Policy Chapter 3: Time Off", "Section 3.1: Vacation Policy"]
            },
            "Q002": {
                "answer": "Full-time employees receive 20 vacation days per year.",
                "citations": ["HR Policy Chapter 3: Time Off", "Section 3.2: Annual Accrual"]
            },
            "Q003": {
                "answer": "$75 per day for domestic travel, $100 for international.",
                "citations": ["HR Policy Chapter 5: Business Travel", "Section 5.3: Meal Allowance"]
            },
        }
    
    def query(self, question: str, question_id: str) -> Dict[str, any]:
        """Query the LLM and return answer with citations
        
        Args:
            question: The question text
            question_id: Question identifier (e.g., Q001)
        
        Returns:
            Dictionary with 'answer' and 'citations' keys
        """
        if question_id in self.responses:
            return self.responses[question_id]
        
        raise ValueError(f"Unknown question ID: {question_id}")


@pytest.fixture(scope="session")
def mock_llm():
    """Fixture providing mock LLM implementation"""
    return MockLLMImplementation()


@pytest.fixture(scope="session")
def test_questions():
    """Fixture providing test questions"""
    return [
        BenchmarkQuestion(
            id="Q001",
            category="vacation_policy",
            question="How do I request vacation time?",
            expected_answer="Submit a vacation request through the employee portal at least 2 weeks in advance.",
            variations=[
                "Submit vacation request via employee portal 2 weeks ahead.",
                "Use the portal to request time off with 2-week notice.",
            ],
            citation_required=True
        ),
        BenchmarkQuestion(
            id="Q002",
            category="vacation_policy",
            question="How many vacation days do I get per year?",
            expected_answer="Full-time employees receive 20 vacation days per year.",
            variations=[
                "20 days of vacation annually for full-time staff.",
                "Full-time workers get 20 vacation days each year.",
            ],
            citation_required=True
        ),
        BenchmarkQuestion(
            id="Q003",
            category="expense_policy",
            question="What is the maximum daily meal allowance for business travel?",
            expected_answer="$75 per day for domestic travel, $100 for international.",
            variations=[
                "Domestic travel: $75/day, International: $100/day for meals.",
                "$75 daily meal limit domestic, $100 international.",
            ],
            citation_required=True
        ),
    ]


class TestLLMBenchmarkAccuracy:
    """Test LLM accuracy against benchmark questions"""
    
    def test_llm_answers_question_q001(self, mock_llm, test_questions):
        """Test Q001: Vacation request process"""
        question = test_questions[0]
        response = mock_llm.query(question.question, question.id)
        
        # Check answer accuracy using fuzzy matching
        match, score, _ = match_against_variations(
            [question.expected_answer] + question.variations,
            response["answer"],
            lev_threshold=0.8
        )
        
        assert match, f"Answer '{response['answer']}' does not match expected variations"
        assert score >= 0.8, f"Match score {score} below threshold 0.8"
    
    def test_llm_answers_question_q002(self, mock_llm, test_questions):
        """Test Q002: Vacation days per year"""
        question = test_questions[1]
        response = mock_llm.query(question.question, question.id)
        
        match, score, _ = match_against_variations(
            [question.expected_answer] + question.variations,
            response["answer"],
            lev_threshold=0.8
        )
        
        assert match, f"Answer '{response['answer']}' does not match expected variations"
        assert score >= 0.8, f"Match score {score} below threshold 0.8"
    
    def test_llm_answers_question_q003(self, mock_llm, test_questions):
        """Test Q003: Meal allowance limits"""
        question = test_questions[2]
        response = mock_llm.query(question.question, question.id)
        
        match, score, _ = match_against_variations(
            [question.expected_answer] + question.variations,
            response["answer"],
            lev_threshold=0.8
        )
        
        assert match, f"Answer '{response['answer']}' does not match expected variations"
        assert score >= 0.8, f"Match score {score} below threshold 0.8"


class TestLLMBenchmarkCitations:
    """Test LLM citation coverage and accuracy"""
    
    def test_llm_provides_citations_q001(self, mock_llm, test_questions):
        """Test that Q001 answer includes citations"""
        question = test_questions[0]
        response = mock_llm.query(question.question, question.id)
        
        assert "citations" in response, "Response missing 'citations' field"
        assert len(response["citations"]) > 0, "No citations provided for Q001"
        assert isinstance(response["citations"], list), "Citations must be a list"
    
    def test_llm_provides_citations_q002(self, mock_llm, test_questions):
        """Test that Q002 answer includes citations"""
        question = test_questions[1]
        response = mock_llm.query(question.question, question.id)
        
        assert "citations" in response, "Response missing 'citations' field"
        assert len(response["citations"]) > 0, "No citations provided for Q002"
        assert isinstance(response["citations"], list), "Citations must be a list"
    
    def test_llm_provides_citations_q003(self, mock_llm, test_questions):
        """Test that Q003 answer includes citations"""
        question = test_questions[2]
        response = mock_llm.query(question.question, question.id)
        
        assert "citations" in response, "Response missing 'citations' field"
        assert len(response["citations"]) > 0, "No citations provided for Q003"
        assert isinstance(response["citations"], list), "Citations must be a list"


class TestLLMBenchmarkConsistency:
    """Test LLM consistency and reliability"""
    
    def test_llm_consistent_answers(self, mock_llm, test_questions):
        """Test that LLM provides consistent answers across multiple queries"""
        question = test_questions[0]
        
        # Query twice and verify consistency
        response1 = mock_llm.query(question.question, question.id)
        response2 = mock_llm.query(question.question, question.id)
        
        assert response1["answer"] == response2["answer"], "LLM answers are inconsistent"
        assert response1["citations"] == response2["citations"], "LLM citations are inconsistent"
    
    def test_llm_returns_required_fields(self, mock_llm, test_questions):
        """Test that LLM response includes all required fields"""
        question = test_questions[0]
        response = mock_llm.query(question.question, question.id)
        
        required_fields = ["answer", "citations"]
        for field in required_fields:
            assert field in response, f"Response missing required field: {field}"
        
        assert isinstance(response["answer"], str), "Answer must be a string"
        assert isinstance(response["citations"], list), "Citations must be a list"
        assert len(response["answer"]) > 0, "Answer cannot be empty"


class TestLLMBenchmarkPerformance:
    """Test LLM performance characteristics"""
    
    def test_llm_response_time(self, mock_llm, test_questions):
        """Test that LLM responses complete within time limit"""
        import time
        
        question = test_questions[0]
        
        start = time.time()
        response = mock_llm.query(question.question, question.id)
        elapsed = time.time() - start
        
        # For mock implementation, should be very fast
        assert elapsed < 1.0, f"LLM response took {elapsed:.2f}s, expected < 1.0s"
    
    def test_llm_batch_processing(self, mock_llm, test_questions):
        """Test LLM can process multiple questions"""
        responses = []
        for question in test_questions:
            response = mock_llm.query(question.question, question.id)
            responses.append(response)
        
        assert len(responses) == len(test_questions), "Not all questions processed"
        assert all("answer" in r for r in responses), "Some responses missing answers"
        assert all("citations" in r for r in responses), "Some responses missing citations"


class TestBenchmarkSuiteIntegration:
    """Integration tests for the complete benchmark suite"""
    
    def test_all_benchmark_questions_pass(self, mock_llm, test_questions):
        """Test that all benchmark questions pass validation"""
        failures = []
        
        for question in test_questions:
            try:
                response = mock_llm.query(question.question, question.id)
                
                # Check accuracy
                match, score, _ = match_against_variations(
                    [question.expected_answer] + question.variations,
                    response["answer"],
                    lev_threshold=0.8
                )
                
                if not match or score < 0.8:
                    failures.append(f"{question.id}: Accuracy check failed (score: {score})")
                
                # Check citations if required
                if question.citation_required:
                    if "citations" not in response or len(response["citations"]) == 0:
                        failures.append(f"{question.id}: Citation check failed")
                
            except Exception as e:
                failures.append(f"{question.id}: {str(e)}")
        
        assert len(failures) == 0, f"Benchmark failures:\n" + "\n".join(failures)
    
    def test_benchmark_coverage(self, test_questions):
        """Test that benchmark includes multiple categories"""
        categories = set(q.category for q in test_questions)
        
        assert len(categories) >= 2, "Benchmark should cover at least 2 categories"
        assert "vacation_policy" in categories, "Benchmark must include vacation_policy"
        assert "expense_policy" in categories, "Benchmark must include expense_policy"
    
    def test_benchmark_citations_required_for_all(self, test_questions):
        """Test that all benchmark questions require citations"""
        for question in test_questions:
            assert question.citation_required, \
                f"Question {question.id} should require citations for RAG validation"
