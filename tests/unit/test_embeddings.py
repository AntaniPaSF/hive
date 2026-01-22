"""
Unit tests for EmbeddingGenerator

Tests embedding generation, batching, normalization, and model information.
"""

import pytest
import numpy as np
from app.ingestion.embeddings import EmbeddingGenerator, EmbeddingResult


@pytest.fixture
def generator():
    """Create an embedding generator with default model."""
    return EmbeddingGenerator(model_name="all-MiniLM-L6-v2", batch_size=32)


def test_generator_initialization(generator):
    """Test that generator initializes with correct parameters."""
    assert generator.model_name == "all-MiniLM-L6-v2"
    assert generator.batch_size == 32
    assert generator.dimension == 384  # all-MiniLM-L6-v2 has 384 dimensions
    assert generator.model is not None


def test_generate_single_embedding(generator):
    """Test generating embedding for a single text."""
    text = "This is a test sentence for embedding generation."
    
    embedding = generator.generate_single_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 384
    assert all(isinstance(x, float) for x in embedding)
    
    # Normalized embeddings should have L2 norm close to 1.0
    norm = np.linalg.norm(embedding)
    assert 0.99 <= norm <= 1.01


def test_generate_embeddings_batch(generator):
    """Test generating embeddings for multiple texts."""
    texts = [
        "Employees are entitled to 15 days of vacation.",
        "Health insurance is provided for all full-time employees.",
        "Remote work policy allows 2 days per week from home."
    ]
    
    result = generator.generate_embeddings(texts, show_progress=False)
    
    assert isinstance(result, EmbeddingResult)
    assert len(result.embeddings) == 3
    assert result.model_name == "all-MiniLM-L6-v2"
    assert result.dimension == 384
    assert result.total_chunks == 3
    
    # Check each embedding
    for embedding in result.embeddings:
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)


def test_empty_text_list(generator):
    """Test handling of empty text list."""
    result = generator.generate_embeddings([], show_progress=False)
    
    assert result.embeddings == []
    assert result.total_chunks == 0
    assert result.dimension == 384


def test_embeddings_are_different(generator):
    """Test that different texts produce different embeddings."""
    texts = [
        "Vacation policy allows 15 days off per year.",
        "The quick brown fox jumps over the lazy dog."
    ]
    
    result = generator.generate_embeddings(texts, show_progress=False)
    
    embedding1 = result.embeddings[0]
    embedding2 = result.embeddings[1]
    
    # Calculate cosine similarity
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    
    # Different texts should have lower similarity (not identical)
    assert dot_product < 0.99  # Not identical embeddings


def test_embeddings_are_similar_for_similar_text(generator):
    """Test that similar texts produce similar embeddings."""
    texts = [
        "Employees get 15 vacation days each year.",
        "Workers receive 15 days of vacation annually."
    ]
    
    result = generator.generate_embeddings(texts, show_progress=False)
    
    embedding1 = result.embeddings[0]
    embedding2 = result.embeddings[1]
    
    # Calculate cosine similarity
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    
    # Similar texts should have high similarity
    assert dot_product > 0.7  # High similarity for semantically similar texts


def test_validate_embedding_dimension(generator):
    """Test embedding dimension validation."""
    valid_embedding = [0.1] * 384
    invalid_embedding = [0.1] * 128
    
    assert generator.validate_embedding_dimension(valid_embedding) is True
    assert generator.validate_embedding_dimension(invalid_embedding) is False


def test_get_model_info(generator):
    """Test retrieving model information."""
    info = generator.get_model_info()
    
    assert info['model_name'] == "all-MiniLM-L6-v2"
    assert info['embedding_dimension'] == 384
    assert info['batch_size'] == 32
    assert 'model_version' in info
    assert 'max_sequence_length' in info


def test_large_batch_processing(generator):
    """Test processing a large batch of texts."""
    # Create 100 text samples
    texts = [f"This is test sentence number {i}." for i in range(100)]
    
    result = generator.generate_embeddings(texts, show_progress=False)
    
    assert len(result.embeddings) == 100
    assert result.total_chunks == 100
    
    # Verify all embeddings have correct dimensions
    for embedding in result.embeddings:
        assert len(embedding) == 384


def test_normalization_enabled(generator):
    """Test that embeddings are normalized when normalize=True."""
    text = "Test sentence for normalization."
    
    embedding = generator.generate_single_embedding(text, normalize=True)
    
    # Calculate L2 norm
    norm = np.linalg.norm(embedding)
    
    # Normalized embeddings should have L2 norm very close to 1.0
    assert 0.99 <= norm <= 1.01


def test_normalization_disabled(generator):
    """Test embeddings without normalization."""
    text = "Test sentence for normalization."
    
    embedding = generator.generate_single_embedding(text, normalize=False)
    
    # Calculate L2 norm
    norm = np.linalg.norm(embedding)
    
    # Without normalization, norm may not be 1.0
    # Just verify it's a positive value
    assert norm > 0
