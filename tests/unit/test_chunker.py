"""
Unit tests for SemanticChunker

Tests chunking logic, token counting, overlap handling, and metadata generation.
"""

import pytest
from app.ingestion.chunker import SemanticChunker, Chunk


@pytest.fixture
def chunker():
    """Create a chunker with default parameters."""
    return SemanticChunker(max_tokens=512, overlap_tokens=50, min_chunk_size=100)


@pytest.fixture
def sample_pdf_page():
    """Sample PDF page structure from PDFParser."""
    return {
        'page_number': 1,
        'text': 'This is sample text from the PDF page.',
        'sections': [
            {
                'title': 'Introduction',
                'text': 'This is the introduction section. ' * 50,  # ~350 chars
                'level': 1
            },
            {
                'title': 'Benefits Policy',
                'text': 'Employees are entitled to comprehensive benefits. ' * 100,  # ~5000 chars
                'level': 1
            }
        ],
        'metadata': {}
    }


def test_token_counting(chunker):
    """Test that token counting works correctly."""
    text = "This is a test sentence."
    token_count = chunker.count_tokens(text)
    
    assert token_count > 0
    assert token_count < 20  # Should be around 6 tokens


def test_single_chunk_section(chunker):
    """Test that small sections create single chunks."""
    pdf_pages = [{
        'page_number': 1,
        'text': 'Short section',
        'sections': [{
            'title': 'Test Section',
            'text': 'This is a short section that fits in one chunk. ' * 5,  # ~250 chars
            'level': 1
        }],
        'metadata': {}
    }]
    
    chunks = chunker.chunk_document(
        pdf_pages=pdf_pages,
        document_id='test-doc-id',
        source_filename='test.pdf'
    )
    
    assert len(chunks) == 1
    assert chunks[0].metadata['section_title'] == 'Test Section'
    assert chunks[0].metadata['page_number'] == 1
    assert chunks[0].metadata['source_type'] == 'pdf'
    assert chunks[0].token_count <= 512


def test_multi_chunk_section(chunker):
    """Test that large sections are split into multiple chunks with overlap."""
    # Create a section larger than max_tokens
    long_text = 'This is a sentence in a very long section. ' * 200  # ~8600 chars, likely >512 tokens
    
    pdf_pages = [{
        'page_number': 1,
        'text': long_text,
        'sections': [{
            'title': 'Long Section',
            'text': long_text,
            'level': 1
        }],
        'metadata': {}
    }]
    
    chunks = chunker.chunk_document(
        pdf_pages=pdf_pages,
        document_id='test-doc-id',
        source_filename='test.pdf'
    )
    
    assert len(chunks) > 1  # Should be split into multiple chunks
    
    # Verify each chunk respects max_tokens
    for chunk in chunks:
        assert chunk.token_count <= 512
        assert len(chunk.text) >= chunker.min_chunk_size
    
    # Verify chunk indices are sequential
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_overlap_between_chunks(chunker):
    """Test that consecutive chunks have overlapping content."""
    long_text = 'Sentence number one. Sentence number two. Sentence number three. ' * 100
    
    pdf_pages = [{
        'page_number': 1,
        'text': long_text,
        'sections': [{
            'title': 'Test Section',
            'text': long_text,
            'level': 1
        }],
        'metadata': {}
    }]
    
    chunks = chunker.chunk_document(
        pdf_pages=pdf_pages,
        document_id='test-doc-id',
        source_filename='test.pdf'
    )
    
    if len(chunks) > 1:
        # Check that chunks have some overlapping text
        for i in range(len(chunks) - 1):
            current_chunk_end = chunks[i].text[-100:]  # Last 100 chars
            next_chunk_start = chunks[i + 1].text[:100]  # First 100 chars
            
            # There should be some common words
            current_words = set(current_chunk_end.split())
            next_words = set(next_chunk_start.split())
            overlap_words = current_words & next_words
            
            assert len(overlap_words) > 0, "Expected overlap between consecutive chunks"


def test_metadata_preservation(chunker):
    """Test that chunk metadata contains all required fields."""
    pdf_pages = [{
        'page_number': 5,
        'text': 'Test text',
        'sections': [{
            'title': 'Policy Section',
            'text': 'This is a test policy section. ' * 10,
            'level': 2
        }],
        'metadata': {}
    }]
    
    chunks = chunker.chunk_document(
        pdf_pages=pdf_pages,
        document_id='doc-12345',
        source_filename='hr_policy.pdf'
    )
    
    chunk = chunks[0]
    
    assert chunk.chunk_id is not None
    assert chunk.metadata['document_id'] == 'doc-12345'
    assert chunk.metadata['source_doc'] == 'hr_policy.pdf'
    assert chunk.metadata['source_type'] == 'pdf'
    assert chunk.metadata['page_number'] == 5
    assert chunk.metadata['section_title'] == 'Policy Section'
    assert chunk.metadata['chunk_index'] == 0


def test_skip_small_sections(chunker):
    """Test that sections below min_chunk_size are skipped."""
    pdf_pages = [{
        'page_number': 1,
        'text': 'Test',
        'sections': [
            {
                'title': 'Tiny Section',
                'text': 'Too small',  # Much less than 100 chars
                'level': 1
            },
            {
                'title': 'Normal Section',
                'text': 'This section has enough content to be chunked properly. ' * 5,
                'level': 1
            }
        ],
        'metadata': {}
    }]
    
    chunks = chunker.chunk_document(
        pdf_pages=pdf_pages,
        document_id='test-doc-id',
        source_filename='test.pdf'
    )
    
    # Should only have one chunk from the "Normal Section"
    assert len(chunks) == 1
    assert chunks[0].metadata['section_title'] == 'Normal Section'


def test_multiple_pages(chunker):
    """Test chunking across multiple pages."""
    pdf_pages = [
        {
            'page_number': 1,
            'text': 'Page 1 content',
            'sections': [{'title': 'Section 1', 'text': 'First page section. ' * 10, 'level': 1}],
            'metadata': {}
        },
        {
            'page_number': 2,
            'text': 'Page 2 content',
            'sections': [{'title': 'Section 2', 'text': 'Second page section. ' * 10, 'level': 1}],
            'metadata': {}
        }
    ]
    
    chunks = chunker.chunk_document(
        pdf_pages=pdf_pages,
        document_id='test-doc-id',
        source_filename='test.pdf'
    )
    
    assert len(chunks) == 2
    assert chunks[0].metadata['page_number'] == 1
    assert chunks[1].metadata['page_number'] == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_sentence_splitting(chunker):
    """Test that sentence splitting handles abbreviations correctly."""
    text = "Dr. Smith works at Inc. Corp. He is a great researcher. This is another sentence."
    
    sentences = chunker._split_sentences(text)
    
    # Should not split on "Dr." or "Inc."
    assert len(sentences) == 2  # "Dr. Smith..." and "This is another..."
    assert "Dr. Smith" in sentences[0]
    assert "This is another" in sentences[1]
