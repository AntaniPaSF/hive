"""RAG (Retrieval-Augmented Generation) pipeline for HR Data Pipeline."""

from .pipeline import RAGPipeline, RAGResponse, Citation, LLMProvider

__version__ = "1.0.0"
__all__ = ['RAGPipeline', 'RAGResponse', 'Citation', 'LLMProvider']
