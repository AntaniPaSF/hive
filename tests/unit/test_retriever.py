"""
Unit tests for Retriever

Tests text-based search, metadata filtering, and result ranking.
"""

import pytest
from pathlib import Path
from app.query.retriever import Retriever, RetrievalResult, SearchResult
from app.core.config import AppConfig


@pytest.fixture
def retriever():
    """Create a retriever instance."""
    return Retriever()


@pytest.fixture
def sample_ingestion():
    """
    Ingest sample document for testing.
    Run once before tests to ensure data is available.
    """
    from app.ingestion.cli import IngestionPipeline
    
    # Check if sample PDF exists
    pdf_path = Path("data/pdf/Software_Company_Docupedia_FILLED.pdf")
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF not found: {pdf_path}")
    
    # Ingest the document
    pipeline = IngestionPipeline()
    result = pipeline.ingest_pdf(pdf_path, rebuild=False)
    
    return result


def test_retriever_initialization(retriever):
    """Test that retriever initializes correctly."""
    assert retriever is not None
    assert retriever.vectordb is not None
    assert retriever.config is not None


def test_empty_query(retriever):
    """Test that empty query returns empty results."""
    result = retriever.search("")
    
    assert isinstance(result, RetrievalResult)
    assert result.total_results == 0
    assert len(result.results) == 0
    assert result.query == ""


def test_basic_search(retriever, sample_ingestion):
    """Test basic text search functionality."""
    result = retriever.search("vacation policy", top_k=5)
    
    assert isinstance(result, RetrievalResult)
    assert result.query == "vacation policy"
    assert len(result.results) <= 5
    assert result.total_results <= 5
    
    # Check that results have required fields
    if result.results:
        first_result = result.results[0]
        assert isinstance(first_result, SearchResult)
        assert first_result.chunk_id is not None
        assert first_result.text is not None
        assert first_result.score is not None
        assert first_result.metadata is not None


def test_top_k_results(retriever, sample_ingestion):
    """Test that top_k parameter limits results correctly."""
    result_k3 = retriever.search("employee benefits", top_k=3)
    result_k10 = retriever.search("employee benefits", top_k=10)
    
    assert len(result_k3.results) <= 3
    assert len(result_k10.results) <= 10
    
    # If we have enough results, k10 should have more than k3
    if result_k10.total_results >= 10:
        assert len(result_k10.results) >= len(result_k3.results)


def test_search_result_properties(retriever, sample_ingestion):
    """Test SearchResult property accessors."""
    result = retriever.search("policy", top_k=1)
    
    if result.results:
        search_result = result.results[0]
        
        # Test property accessors
        page_num = search_result.page_number
        section = search_result.section_title
        source = search_result.source_doc
        doc_id = search_result.document_id
        
        # These should all be present in metadata
        assert page_num is not None or 'page_number' not in search_result.metadata
        assert doc_id is not None


def test_search_by_document(retriever, sample_ingestion):
    """Test filtering search by document ID."""
    # First, get any document ID from a general search
    general_result = retriever.search("policy", top_k=1)
    
    if general_result.results:
        doc_id = general_result.results[0].document_id
        
        # Search within that specific document
        filtered_result = retriever.search_by_document("policy", doc_id, top_k=5)
        
        assert all(r.document_id == doc_id for r in filtered_result.results)
        assert filtered_result.filters_applied == {'document_id': doc_id}


def test_search_by_page(retriever, sample_ingestion):
    """Test filtering search by page number."""
    result = retriever.search_by_page("policy", page_number=1, top_k=5)
    
    # All results should be from page 1
    assert all(r.page_number == 1 for r in result.results if r.page_number is not None)
    assert result.filters_applied['page_number'] == 1


def test_get_top_k(retriever, sample_ingestion):
    """Test getting top K results from RetrievalResult."""
    result = retriever.search("employee", top_k=10)
    
    if result.total_results >= 5:
        top_3 = result.get_top_k(3)
        assert len(top_3) == 3
        
        top_5 = result.get_top_k(5)
        assert len(top_5) == 5
        
        # Top 3 should be subset of top 5
        assert all(r in top_5 for r in top_3)


def test_filter_by_document(retriever, sample_ingestion):
    """Test filtering results by document ID after retrieval."""
    result = retriever.search("policy", top_k=10)
    
    if result.results and result.results[0].document_id:
        doc_id = result.results[0].document_id
        filtered = result.filter_by_document(doc_id)
        
        assert all(r.document_id == doc_id for r in filtered)


def test_filter_by_page(retriever, sample_ingestion):
    """Test filtering results by page number after retrieval."""
    result = retriever.search("policy", top_k=10)
    
    if result.results:
        page_num = result.results[0].page_number
        if page_num is not None:
            filtered = result.filter_by_page(page_num)
            
            assert all(r.page_number == page_num for r in filtered)


def test_get_chunk_by_id(retriever, sample_ingestion):
    """Test retrieving a specific chunk by ID."""
    # First get a chunk ID from search
    result = retriever.search("policy", top_k=1)
    
    if result.results:
        chunk_id = result.results[0].chunk_id
        
        # Retrieve that specific chunk
        chunk = retriever.get_chunk_by_id(chunk_id)
        
        assert chunk is not None
        assert chunk.chunk_id == chunk_id
        assert chunk.text is not None
        assert chunk.metadata is not None


def test_get_chunk_by_id_not_found(retriever):
    """Test retrieving non-existent chunk returns None."""
    chunk = retriever.get_chunk_by_id("non-existent-id-12345")
    assert chunk is None


def test_get_document_chunks(retriever, sample_ingestion):
    """Test retrieving all chunks for a document."""
    # Get a document ID first
    result = retriever.search("policy", top_k=1)
    
    if result.results:
        doc_id = result.results[0].document_id
        
        # Get all chunks for this document
        chunks = retriever.get_document_chunks(doc_id)
        
        assert len(chunks) > 0
        assert all(c.document_id == doc_id for c in chunks)
        
        # Chunks should be sorted by chunk_index if available
        if chunks and 'chunk_index' in chunks[0].metadata:
            indices = [c.metadata['chunk_index'] for c in chunks]
            assert indices == sorted(indices)


def test_get_document_chunks_by_page(retriever, sample_ingestion):
    """Test retrieving chunks for a specific page in a document."""
    # Get a document ID and page number
    result = retriever.search("policy", top_k=1)
    
    if result.results:
        doc_id = result.results[0].document_id
        page_num = result.results[0].page_number
        
        if page_num is not None:
            chunks = retriever.get_document_chunks(doc_id, page_number=page_num)
            
            assert all(c.document_id == doc_id for c in chunks)
            assert all(c.page_number == page_num for c in chunks)


def test_multi_query_search(retriever, sample_ingestion):
    """Test searching with multiple queries."""
    queries = ["vacation policy", "employee benefits"]
    result = retriever.multi_query_search(queries, top_k=3)
    
    assert isinstance(result, RetrievalResult)
    assert len(result.results) <= 6  # 3 per query
    assert ' OR ' in result.query


def test_get_statistics(retriever, sample_ingestion):
    """Test retrieval statistics."""
    stats = retriever.get_statistics()
    
    assert 'total_chunks' in stats
    assert stats['total_chunks'] >= 0
    assert stats['search_mode'] == 'text-based'
    assert 'collection_name' in stats


def test_relevance_scoring(retriever, sample_ingestion):
    """Test that results are sorted by relevance."""
    result = retriever.search("vacation policy", top_k=5)
    
    if len(result.results) > 1:
        # Scores should be in ascending order (lower is better in ChromaDB)
        scores = [r.score for r in result.results]
        assert scores == sorted(scores)


def test_context_window(retriever, sample_ingestion):
    """Test getting context window around a result."""
    result = retriever.search("policy", top_k=5)
    
    if result.results:
        # Get context window around first result
        context = result.get_context_window(result_index=0, window_size=2)
        
        assert len(context) >= 1  # At least the target result
        assert result.results[0] in context
        
        # All context chunks should be from same document
        doc_ids = {c.document_id for c in context}
        assert len(doc_ids) == 1


def test_min_score_filter(retriever, sample_ingestion):
    """Test filtering results by minimum score threshold."""
    result_unfiltered = retriever.search("policy", top_k=10, min_score=None)
    result_filtered = retriever.search("policy", top_k=10, min_score=0.5)
    
    # Filtered results should be <= unfiltered
    assert len(result_filtered.results) <= len(result_unfiltered.results)
    
    # All filtered results should have score <= 0.5
    assert all(r.score <= 0.5 for r in result_filtered.results)


def test_search_with_special_characters(retriever, sample_ingestion):
    """Test search with special characters in query."""
    queries = [
        "employee's benefits",
        "vacation (paid time off)",
        "401k retirement plan",
        "email: hr@company.com"
    ]
    
    for query in queries:
        result = retriever.search(query, top_k=3)
        # Should not raise exception
        assert isinstance(result, RetrievalResult)


def test_search_case_insensitive(retriever, sample_ingestion):
    """Test that search is case-insensitive."""
    result_lower = retriever.search("vacation policy", top_k=3)
    result_upper = retriever.search("VACATION POLICY", top_k=3)
    result_mixed = retriever.search("Vacation Policy", top_k=3)
    
    # Should return similar numbers of results
    # (exact match not guaranteed due to text-based search)
    assert abs(result_lower.total_results - result_upper.total_results) <= 2
    assert abs(result_lower.total_results - result_mixed.total_results) <= 2
