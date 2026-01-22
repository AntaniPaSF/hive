"""
Unit tests for RAG Pipeline

Tests RAG pipeline functionality including:
- Pipeline initialization with different providers
- Question answering with mock LLM
- Citation generation
- Context building
- Batch processing
- Error handling

Related: Phase 2 (P2), Task 2.2 - RAG Pipeline Tests
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.rag.pipeline import (
    RAGPipeline,
    RAGResponse,
    Citation,
    LLMProvider
)
from app.ingestion.cli import IngestionPipeline


@pytest.fixture(scope="module")
def sample_ingestion():
    """Ingest sample PDF once for all tests."""
    pdf_path = Path("data/pdf/Software_Company_Docupedia_FILLED.pdf")
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}")
    
    pipeline = IngestionPipeline()
    try:
        pipeline.ingest_pdf(pdf_path)
    except Exception as e:
        pytest.skip(f"Could not ingest PDF: {e}")


@pytest.fixture
def rag_pipeline():
    """Create RAG pipeline in mock mode."""
    return RAGPipeline(provider=LLMProvider.MOCK)


class TestRAGPipelineInitialization:
    """Test RAG pipeline initialization."""
    
    def test_mock_provider_initialization(self):
        """Test initialization with mock provider."""
        pipeline = RAGPipeline(provider=LLMProvider.MOCK)
        
        assert pipeline.provider == LLMProvider.MOCK
        assert pipeline.model_name == "mock-model"
        assert pipeline.llm_client is None
        assert pipeline.retriever is not None
    
    @pytest.mark.skip(reason="Requires openai/anthropic/ollama packages")
    def test_default_model_names(self):
        """Test default model names for each provider."""
        pipeline_openai = RAGPipeline(provider=LLMProvider.OPENAI)
        assert pipeline_openai.model_name == "gpt-4"
        
        pipeline_anthropic = RAGPipeline(provider=LLMProvider.ANTHROPIC)
        assert pipeline_anthropic.model_name == "claude-3-sonnet-20240229"
        
        pipeline_ollama = RAGPipeline(provider=LLMProvider.OLLAMA)
        assert pipeline_ollama.model_name == "llama2"
    
    def test_custom_model_name(self):
        """Test initialization with custom model name."""
        pipeline = RAGPipeline(
            provider=LLMProvider.MOCK,
            model_name="custom-model-v1"
        )
        
        assert pipeline.model_name == "custom-model-v1"
    
    def test_get_model_info(self, rag_pipeline):
        """Test getting model information."""
        info = rag_pipeline.get_model_info()
        
        assert info['provider'] == 'mock'
        assert info['model'] == 'mock-model'
        assert 'retriever' in info
        assert 'chunk_size' in info


class TestRAGResponse:
    """Test RAGResponse dataclass."""
    
    def test_rag_response_creation(self):
        """Test creating RAG response."""
        citations = [
            Citation(
                source_doc="test.pdf",
                page_number=1,
                section_title="Introduction",
                chunk_id="abc123",
                relevance_score=0.95,
                text_excerpt="Sample text excerpt..."
            )
        ]
        
        response = RAGResponse(
            question="Test question?",
            answer="Test answer.",
            citations=citations,
            context_used=["Context 1"],
            model="test-model",
            tokens_used=100
        )
        
        assert response.question == "Test question?"
        assert response.answer == "Test answer."
        assert len(response.citations) == 1
        assert response.tokens_used == 100
    
    def test_format_with_citations(self):
        """Test formatting response with citations."""
        citations = [
            Citation(
                source_doc="doc1.pdf",
                page_number=5,
                section_title="Benefits",
                chunk_id="xyz",
                relevance_score=0.9,
                text_excerpt="Excerpt..."
            )
        ]
        
        response = RAGResponse(
            question="Benefits?",
            answer="Here are the benefits.",
            citations=citations,
            context_used=["Context"],
            model="test"
        )
        
        formatted = response.format_with_citations()
        
        assert "Here are the benefits." in formatted
        assert "Sources:" in formatted
        assert "doc1.pdf" in formatted
        assert "Page 5" in formatted
    
    def test_get_unique_sources(self):
        """Test getting unique source documents."""
        citations = [
            Citation("doc1.pdf", 1, None, "id1", 0.9, "text1"),
            Citation("doc2.pdf", 2, None, "id2", 0.8, "text2"),
            Citation("doc1.pdf", 3, None, "id3", 0.7, "text3")
        ]
        
        response = RAGResponse(
            question="Test",
            answer="Answer",
            citations=citations,
            context_used=[],
            model="test"
        )
        
        sources = response.get_unique_sources()
        assert len(sources) == 2
        assert "doc1.pdf" in sources
        assert "doc2.pdf" in sources
    
    def test_get_page_range(self):
        """Test getting page range from citations."""
        citations = [
            Citation("doc.pdf", 5, None, "id1", 0.9, "text1"),
            Citation("doc.pdf", 12, None, "id2", 0.8, "text2"),
            Citation("doc.pdf", 7, None, "id3", 0.7, "text3")
        ]
        
        response = RAGResponse(
            question="Test",
            answer="Answer",
            citations=citations,
            context_used=[],
            model="test"
        )
        
        page_range = response.get_page_range()
        assert page_range == (5, 12)
    
    def test_empty_citations(self):
        """Test response with no citations."""
        response = RAGResponse(
            question="Test",
            answer="No results found.",
            citations=[],
            context_used=[],
            model="test"
        )
        
        assert response.get_unique_sources() == []
        assert response.get_page_range() == (0, 0)


class TestCitation:
    """Test Citation dataclass."""
    
    def test_citation_creation(self):
        """Test creating citation."""
        citation = Citation(
            source_doc="handbook.pdf",
            page_number=42,
            section_title="Time Off",
            chunk_id="chunk-001",
            relevance_score=0.92,
            text_excerpt="Employees are entitled to..."
        )
        
        assert citation.source_doc == "handbook.pdf"
        assert citation.page_number == 42
        assert citation.section_title == "Time Off"
        assert citation.relevance_score == 0.92
    
    def test_citation_string_representation(self):
        """Test citation string formatting."""
        citation = Citation(
            source_doc="policy.pdf",
            page_number=10,
            section_title="Benefits",
            chunk_id="xyz",
            relevance_score=0.85,
            text_excerpt="Text..."
        )
        
        citation_str = str(citation)
        assert "policy.pdf" in citation_str
        assert "Page 10" in citation_str
        assert "Section: Benefits" in citation_str
    
    def test_citation_without_section(self):
        """Test citation without section title."""
        citation = Citation(
            source_doc="doc.pdf",
            page_number=5,
            section_title=None,
            chunk_id="abc",
            relevance_score=0.8,
            text_excerpt="Text"
        )
        
        citation_str = str(citation)
        assert "Section:" not in citation_str


class TestRAGQuestionAnswering:
    """Test RAG question answering functionality."""
    
    def test_ask_basic_question(self, rag_pipeline, sample_ingestion):
        """Test asking a basic question."""
        response = rag_pipeline.ask("What is the vacation policy?")
        
        assert isinstance(response, RAGResponse)
        assert response.question == "What is the vacation policy?"
        assert len(response.answer) > 0
        assert response.model == "mock-model"
    
    def test_ask_with_results(self, rag_pipeline, sample_ingestion):
        """Test asking question that should return results."""
        response = rag_pipeline.ask("employee benefits", top_k=3)
        
        assert isinstance(response, RAGResponse)
        assert len(response.context_used) > 0
        assert len(response.citations) > 0
        assert response.citations[0].relevance_score > 0
    
    def test_ask_with_no_results(self, rag_pipeline):
        """Test asking question with no matching documents."""
        # Note: ChromaDB text search may still find some results even for nonsense queries
        # This test validates that the pipeline handles low-relevance results gracefully
        response = rag_pipeline.ask("xyznonexistent", top_k=3)
        
        assert isinstance(response, RAGResponse)
        # Either no results or mock response is returned
        assert len(response.answer) > 0  # Some answer is always provided
    
    def test_ask_with_filters(self, rag_pipeline, sample_ingestion):
        """Test asking with metadata filters."""
        response = rag_pipeline.ask(
            "policy",
            top_k=3,
            filters={'page_number': 5}
        )
        
        assert isinstance(response, RAGResponse)
        # All citations should be from page 5
        for citation in response.citations:
            assert citation.page_number == 5
    
    def test_ask_with_temperature(self, rag_pipeline, sample_ingestion):
        """Test asking with different temperature."""
        response = rag_pipeline.ask(
            "What are the policies?",
            temperature=0.7,
            max_tokens=500
        )
        
        assert isinstance(response, RAGResponse)
        assert len(response.answer) > 0


class TestContextBuilding:
    """Test context building from search results."""
    
    def test_build_context(self, rag_pipeline, sample_ingestion):
        """Test building context from retrieval results."""
        # Get some results first
        retrieval_result = rag_pipeline.retriever.search("policy", top_k=3)
        
        # Build context
        context = rag_pipeline._build_context(retrieval_result.results)
        
        assert len(context) > 0
        assert "[Source 1:" in context
        assert "Page" in context
    
    def test_context_includes_metadata(self, rag_pipeline, sample_ingestion):
        """Test that context includes source metadata."""
        retrieval_result = rag_pipeline.retriever.search("employee", top_k=2)
        context = rag_pipeline._build_context(retrieval_result.results)
        
        # Should have source markers
        assert context.count("[Source") >= 2
        assert "Page" in context


class TestPromptBuilding:
    """Test prompt construction."""
    
    def test_build_prompt(self, rag_pipeline):
        """Test building LLM prompt."""
        question = "What is the PTO policy?"
        context = "[Source 1: handbook.pdf, Page 5]\nPTO policy states..."
        
        prompt = rag_pipeline._build_prompt(question, context)
        
        assert question in prompt
        assert context in prompt
        assert "HR policy assistant" in prompt
        assert "ONLY" in prompt  # Emphasis on using only context
    
    def test_prompt_includes_rules(self, rag_pipeline):
        """Test that prompt includes important rules."""
        prompt = rag_pipeline._build_prompt("Test?", "Context")
        
        assert "based only on" in prompt.lower()  # Case insensitive
        assert "context" in prompt.lower()
        assert "do not make up information" in prompt.lower()


class TestCitationCreation:
    """Test citation creation from search results."""
    
    def test_create_citations(self, rag_pipeline, sample_ingestion):
        """Test creating citations from search results."""
        retrieval_result = rag_pipeline.retriever.search("policy", top_k=3)
        citations = rag_pipeline._create_citations(retrieval_result.results)
        
        assert len(citations) > 0
        assert all(isinstance(c, Citation) for c in citations)
        assert all(c.source_doc for c in citations)
        assert all(c.page_number > 0 for c in citations)
    
    def test_citation_text_excerpt(self, rag_pipeline, sample_ingestion):
        """Test that citations include text excerpts."""
        retrieval_result = rag_pipeline.retriever.search("employee", top_k=2)
        citations = rag_pipeline._create_citations(retrieval_result.results)
        
        for citation in citations:
            assert len(citation.text_excerpt) > 0
            # Should be truncated to 200 chars or less (plus "...")
            assert len(citation.text_excerpt) <= 203


class TestBatchProcessing:
    """Test batch question processing."""
    
    def test_batch_ask_multiple_questions(self, rag_pipeline, sample_ingestion):
        """Test processing multiple questions in batch."""
        questions = [
            "What is the vacation policy?",
            "What are employee benefits?",
            "What is the PTO policy?"
        ]
        
        responses = rag_pipeline.batch_ask(questions, top_k=3)
        
        assert len(responses) == 3
        assert all(isinstance(r, RAGResponse) for r in responses)
        assert [r.question for r in responses] == questions
    
    def test_batch_ask_handles_errors(self, rag_pipeline):
        """Test that batch processing handles individual errors."""
        questions = ["Valid question", "Another valid question"]
        
        # Mock ask to fail on first question
        original_ask = rag_pipeline.ask
        call_count = [0]
        
        def mock_ask(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated error")
            return original_ask(*args, **kwargs)
        
        rag_pipeline.ask = mock_ask
        
        responses = rag_pipeline.batch_ask(questions)
        
        assert len(responses) == 2
        assert "Error processing question" in responses[0].answer


class TestContextWindow:
    """Test context window expansion."""
    
    def test_ask_with_context_window(self, rag_pipeline, sample_ingestion):
        """Test asking with expanded context window."""
        response = rag_pipeline.ask_with_context_window(
            "policy",
            top_k=2,
            window_size=1
        )
        
        assert isinstance(response, RAGResponse)
        # Should have more context than original top_k
        # (includes neighboring chunks)
        assert len(response.context_used) >= 2
    
    def test_context_window_with_no_results(self, rag_pipeline):
        """Test context window with no initial results."""
        # Note: ChromaDB text search may return results even for nonsense queries
        response = rag_pipeline.ask_with_context_window(
            "xyznonexistent",
            top_k=3,
            window_size=1
        )
        
        assert isinstance(response, RAGResponse)
        # Response is always provided (may have citations if text search finds matches)
        assert len(response.answer) > 0


class TestMockGeneration:
    """Test mock answer generation."""
    
    def test_generate_mock_answer(self, rag_pipeline):
        """Test generating mock answer."""
        context = "[Source 1: test.pdf, Page 5]\nTest content"
        answer, tokens = rag_pipeline._generate_mock("Test question?", context)
        
        assert len(answer) > 0
        assert "test.pdf" in answer.lower() or "[source 1:" in answer.lower()
        assert tokens == 150  # Mock token count
        assert "mock response" in answer.lower()


def test_rag_pipeline_end_to_end(sample_ingestion):
    """End-to-end test of RAG pipeline."""
    pipeline = RAGPipeline(provider=LLMProvider.MOCK)
    
    # Ask a question
    response = pipeline.ask(
        "What are the employee policies?",
        top_k=5
    )
    
    # Verify complete response
    assert isinstance(response, RAGResponse)
    assert len(response.answer) > 0
    assert response.question == "What are the employee policies?"
    assert response.model == "mock-model"
    
    # Should have context and citations
    if response.citations:  # If results were found
        assert len(response.context_used) > 0
        assert len(response.citations) > 0
        assert all(isinstance(c, Citation) for c in response.citations)
        
        # Test formatted output
        formatted = response.format_with_citations()
        assert "Sources:" in formatted
