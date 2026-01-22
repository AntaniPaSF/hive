"""
Query Accuracy Testing Suite

Evaluates the quality of RAG responses:
- Answer relevance to questions
- Citation accuracy and validity
- Source attribution correctness
- Answer completeness
"""

import pytest
from typing import List, Dict, Any

from app.rag.pipeline import RAGPipeline, LLMProvider, RAGResponse
from app.query.retriever import Retriever
from app.core.config import AppConfig


# ============================================================================
# Test Data: Question-Answer Pairs with Expected Attributes
# ============================================================================

EVALUATION_QUESTIONS = [
    {
        "question": "What is the vacation policy?",
        "expected_keywords": ["vacation", "days", "time off", "PTO"],
        "expected_doc": "Software_Company_Docupedia_FILLED.pdf",
        "category": "benefits"
    },
    {
        "question": "How many sick days do employees get?",
        "expected_keywords": ["sick", "days", "leave"],
        "expected_doc": "Software_Company_Docupedia_FILLED.pdf",
        "category": "benefits"
    },
    {
        "question": "What is the remote work policy?",
        "expected_keywords": ["remote", "work", "home", "hybrid"],
        "expected_doc": "Software_Company_Docupedia_FILLED.pdf",
        "category": "workplace"
    },
    {
        "question": "What are the employee benefits?",
        "expected_keywords": ["benefits", "insurance", "health", "401k", "retirement"],
        "expected_doc": "Software_Company_Docupedia_FILLED.pdf",
        "category": "benefits"
    },
    {
        "question": "What is the code of conduct?",
        "expected_keywords": ["conduct", "behavior", "ethics", "professional"],
        "expected_doc": "Software_Company_Docupedia_FILLED.pdf",
        "category": "policy"
    },
]


class AccuracyMetrics:
    """Calculate and store accuracy metrics."""
    
    def __init__(self):
        self.total_questions = 0
        self.questions_with_answer = 0
        self.questions_with_sources = 0
        self.questions_with_valid_citations = 0
        self.keyword_match_scores = []
        self.source_relevance_scores = []
    
    def add_result(
        self,
        has_answer: bool,
        has_sources: bool,
        has_valid_citations: bool,
        keyword_score: float,
        source_score: float
    ):
        """Add evaluation result."""
        self.total_questions += 1
        if has_answer:
            self.questions_with_answer += 1
        if has_sources:
            self.questions_with_sources += 1
        if has_valid_citations:
            self.questions_with_valid_citations += 1
        self.keyword_match_scores.append(keyword_score)
        self.source_relevance_scores.append(source_score)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get accuracy summary statistics."""
        return {
            "total_questions": self.total_questions,
            "answer_rate": self.questions_with_answer / self.total_questions if self.total_questions > 0 else 0,
            "citation_rate": self.questions_with_sources / self.total_questions if self.total_questions > 0 else 0,
            "valid_citation_rate": self.questions_with_valid_citations / self.total_questions if self.total_questions > 0 else 0,
            "avg_keyword_score": sum(self.keyword_match_scores) / len(self.keyword_match_scores) if self.keyword_match_scores else 0,
            "avg_source_relevance": sum(self.source_relevance_scores) / len(self.source_relevance_scores) if self.source_relevance_scores else 0,
        }
    
    def __str__(self) -> str:
        summary = self.get_summary()
        return (
            f"Accuracy Metrics:\n"
            f"  Total Questions: {summary['total_questions']}\n"
            f"  Answer Rate: {summary['answer_rate']:.1%}\n"
            f"  Citation Rate: {summary['citation_rate']:.1%}\n"
            f"  Valid Citations: {summary['valid_citation_rate']:.1%}\n"
            f"  Avg Keyword Match: {summary['avg_keyword_score']:.1%}\n"
            f"  Avg Source Relevance: {summary['avg_source_relevance']:.1%}"
        )


@pytest.fixture
def rag_pipeline():
    """Create RAG pipeline for testing."""
    config = AppConfig()
    return RAGPipeline(
        retriever=Retriever(config=config),
        provider=LLMProvider.MOCK,
        config=config
    )


# ============================================================================
# Answer Quality Tests
# ============================================================================

class TestAnswerQuality:
    """Test the quality and relevance of RAG answers."""
    
    def test_all_questions_get_answers(self, rag_pipeline):
        """Verify all questions receive an answer."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            assert response.answer is not None, \
                f"No answer for: {item['question']}"
            assert len(response.answer) > 0, \
                f"Empty answer for: {item['question']}"
            assert len(response.answer) > 20, \
                f"Answer too short for: {item['question']}"
    
    def test_answers_contain_expected_keywords(self, rag_pipeline):
        """Verify answers contain relevant keywords."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            answer_lower = response.answer.lower()
            
            # Check if at least one keyword is present
            keyword_found = any(
                keyword.lower() in answer_lower
                for keyword in item["expected_keywords"]
            )
            
            assert keyword_found, \
                f"No expected keywords in answer for: {item['question']}\n" \
                f"Expected: {item['expected_keywords']}\n" \
                f"Answer: {response.answer[:200]}..."
    
    def test_answers_have_reasonable_length(self, rag_pipeline):
        """Verify answers are neither too short nor too long."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            answer_length = len(response.answer)
            
            # Reasonable range: 20-2000 characters
            assert 20 <= answer_length <= 2000, \
                f"Answer length {answer_length} out of range for: {item['question']}"
    
    def test_keyword_coverage_score(self, rag_pipeline):
        """Calculate keyword coverage score for all questions."""
        scores = []
        
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            answer_lower = response.answer.lower()
            
            # Calculate what percentage of keywords appear in answer
            matches = sum(
                1 for keyword in item["expected_keywords"]
                if keyword.lower() in answer_lower
            )
            score = matches / len(item["expected_keywords"])
            scores.append(score)
            
            print(f"\n{item['question']}")
            print(f"  Keyword score: {score:.1%} ({matches}/{len(item['expected_keywords'])})")
        
        avg_score = sum(scores) / len(scores)
        print(f"\nAverage keyword coverage: {avg_score:.1%}")
        
        # At least 40% keyword coverage on average
        assert avg_score >= 0.4, f"Low keyword coverage: {avg_score:.1%}"


# ============================================================================
# Citation Quality Tests
# ============================================================================

class TestCitationQuality:
    """Test citation accuracy and validity."""
    
    def test_all_answers_have_citations(self, rag_pipeline):
        """Verify all answers include source citations."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            assert len(response.sources) > 0, \
                f"No sources for: {item['question']}"
            
            # Check citation structure
            for citation in response.sources:
                assert citation.document_name is not None
                assert citation.page_number is not None
                assert citation.chunk_id is not None
    
    def test_citations_reference_expected_document(self, rag_pipeline):
        """Verify citations reference the expected document."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            # At least one citation should be from expected document
            expected_doc = item["expected_doc"]
            has_expected_doc = any(
                expected_doc in citation.document_name
                for citation in response.sources
            )
            
            assert has_expected_doc, \
                f"No citations from {expected_doc} for: {item['question']}"
    
    def test_citations_have_valid_page_numbers(self, rag_pipeline):
        """Verify citations have valid page numbers."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            for citation in response.sources:
                # Page numbers should be positive integers
                assert isinstance(citation.page_number, int), \
                    f"Invalid page number type: {type(citation.page_number)}"
                assert citation.page_number > 0, \
                    f"Invalid page number: {citation.page_number}"
    
    def test_citation_relevance_to_question(self, rag_pipeline):
        """Test that citations are relevant to the question."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"], top_k=3)
            
            # Check if citation text contains relevant keywords
            relevance_scores = []
            for citation in response.sources:
                if hasattr(citation, 'text') and citation.text:
                    text_lower = citation.text.lower()
                    matches = sum(
                        1 for keyword in item["expected_keywords"]
                        if keyword.lower() in text_lower
                    )
                    score = matches / len(item["expected_keywords"])
                    relevance_scores.append(score)
            
            if relevance_scores:
                avg_relevance = sum(relevance_scores) / len(relevance_scores)
                print(f"\n{item['question']}")
                print(f"  Citation relevance: {avg_relevance:.1%}")
                
                # At least some relevance expected
                assert avg_relevance > 0, \
                    f"Citations not relevant for: {item['question']}"


# ============================================================================
# Source Attribution Tests
# ============================================================================

class TestSourceAttribution:
    """Test source attribution correctness."""
    
    def test_unique_citations(self, rag_pipeline):
        """Verify citations are unique (no duplicates)."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            # Check for duplicate chunk_ids
            chunk_ids = [c.chunk_id for c in response.sources]
            unique_ids = set(chunk_ids)
            
            # Allow some duplicates but not complete duplication
            duplicate_ratio = 1 - (len(unique_ids) / len(chunk_ids))
            assert duplicate_ratio < 0.5, \
                f"Too many duplicate citations ({duplicate_ratio:.1%}) for: {item['question']}"
    
    def test_citation_count_matches_top_k(self, rag_pipeline):
        """Verify number of citations matches requested top_k."""
        for item in EVALUATION_QUESTIONS:
            for top_k in [3, 5, 10]:
                response = rag_pipeline.ask(item["question"], top_k=top_k)
                
                # Should have at most top_k citations (might be fewer if not enough chunks)
                assert len(response.sources) <= top_k, \
                    f"Too many sources ({len(response.sources)}) for top_k={top_k}"
    
    def test_metadata_completeness(self, rag_pipeline):
        """Verify all citations have complete metadata."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            for i, citation in enumerate(response.sources):
                assert citation.document_name, \
                    f"Missing document_name in citation {i} for: {item['question']}"
                assert citation.page_number is not None, \
                    f"Missing page_number in citation {i} for: {item['question']}"
                assert citation.chunk_id, \
                    f"Missing chunk_id in citation {i} for: {item['question']}"


# ============================================================================
# Comprehensive Accuracy Evaluation
# ============================================================================

class TestComprehensiveAccuracy:
    """Comprehensive accuracy evaluation across all test questions."""
    
    def test_overall_accuracy_metrics(self, rag_pipeline):
        """Calculate overall accuracy metrics."""
        metrics = AccuracyMetrics()
        
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            # Check basic criteria
            has_answer = response.answer is not None and len(response.answer) > 0
            has_sources = len(response.sources) > 0
            has_valid_citations = has_sources and all(
                c.document_name and c.page_number is not None
                for c in response.sources
            )
            
            # Calculate keyword score
            if has_answer:
                answer_lower = response.answer.lower()
                keyword_matches = sum(
                    1 for keyword in item["expected_keywords"]
                    if keyword.lower() in answer_lower
                )
                keyword_score = keyword_matches / len(item["expected_keywords"])
            else:
                keyword_score = 0.0
            
            # Calculate source relevance score
            if has_sources and item["expected_doc"]:
                source_matches = sum(
                    1 for citation in response.sources
                    if item["expected_doc"] in citation.document_name
                )
                source_score = source_matches / len(response.sources)
            else:
                source_score = 0.0
            
            metrics.add_result(
                has_answer=has_answer,
                has_sources=has_sources,
                has_valid_citations=has_valid_citations,
                keyword_score=keyword_score,
                source_score=source_score
            )
        
        # Print summary
        print(f"\n{metrics}")
        
        # Assertions for acceptable accuracy
        summary = metrics.get_summary()
        assert summary["answer_rate"] >= 0.95, \
            f"Low answer rate: {summary['answer_rate']:.1%}"
        assert summary["citation_rate"] >= 0.95, \
            f"Low citation rate: {summary['citation_rate']:.1%}"
        assert summary["valid_citation_rate"] >= 0.90, \
            f"Low valid citation rate: {summary['valid_citation_rate']:.1%}"
        assert summary["avg_keyword_score"] >= 0.30, \
            f"Low keyword match: {summary['avg_keyword_score']:.1%}"
        assert summary["avg_source_relevance"] >= 0.50, \
            f"Low source relevance: {summary['avg_source_relevance']:.1%}"
    
    def test_accuracy_by_category(self, rag_pipeline):
        """Evaluate accuracy by question category."""
        categories = {}
        
        for item in EVALUATION_QUESTIONS:
            category = item["category"]
            if category not in categories:
                categories[category] = AccuracyMetrics()
            
            response = rag_pipeline.ask(item["question"])
            
            # Evaluate response
            has_answer = response.answer is not None and len(response.answer) > 0
            has_sources = len(response.sources) > 0
            has_valid_citations = has_sources and all(
                c.document_name and c.page_number is not None
                for c in response.sources
            )
            
            answer_lower = response.answer.lower() if has_answer else ""
            keyword_matches = sum(
                1 for keyword in item["expected_keywords"]
                if keyword.lower() in answer_lower
            )
            keyword_score = keyword_matches / len(item["expected_keywords"]) if has_answer else 0.0
            
            source_matches = sum(
                1 for citation in response.sources
                if item["expected_doc"] in citation.document_name
            ) if has_sources else 0
            source_score = source_matches / len(response.sources) if has_sources else 0.0
            
            categories[category].add_result(
                has_answer=has_answer,
                has_sources=has_sources,
                has_valid_citations=has_valid_citations,
                keyword_score=keyword_score,
                source_score=source_score
            )
        
        # Print category summaries
        print("\nAccuracy by Category:")
        for category, metrics in categories.items():
            print(f"\n{category.upper()}:")
            summary = metrics.get_summary()
            for key, value in summary.items():
                if isinstance(value, float) and key != "total_questions":
                    print(f"  {key}: {value:.1%}")
                else:
                    print(f"  {key}: {value}")


# ============================================================================
# Answer Completeness Tests
# ============================================================================

class TestAnswerCompleteness:
    """Test whether answers are complete and informative."""
    
    def test_answers_address_question(self, rag_pipeline):
        """Verify answers actually address the question asked."""
        for item in EVALUATION_QUESTIONS:
            response = rag_pipeline.ask(item["question"])
            
            # Answer should contain words from the question
            question_words = set(item["question"].lower().split())
            answer_words = set(response.answer.lower().split())
            
            # Remove common words
            common_words = {'what', 'is', 'the', 'a', 'an', 'how', 'many', 'do', 'does'}
            question_words -= common_words
            
            # At least some overlap expected
            overlap = question_words & answer_words
            overlap_ratio = len(overlap) / len(question_words) if question_words else 0
            
            assert overlap_ratio > 0, \
                f"Answer doesn't address question: {item['question']}\n" \
                f"Answer: {response.answer[:200]}..."
    
    def test_multi_part_questions(self, rag_pipeline):
        """Test handling of multi-part questions."""
        multi_part_questions = [
            "What is the vacation policy and how many days do employees get?",
            "What are the sick leave benefits and who is eligible?",
        ]
        
        for question in multi_part_questions:
            response = rag_pipeline.ask(question)
            
            # Answer should be longer for multi-part questions
            assert len(response.answer) > 50, \
                f"Answer too short for multi-part question: {question}"
            
            # Should have multiple sources
            assert len(response.sources) >= 3, \
                f"Too few sources for multi-part question: {question}"


if __name__ == "__main__":
    # Run with: python -m pytest tests/evaluation/test_accuracy.py -v -s
    pytest.main([__file__, "-v", "-s"])
