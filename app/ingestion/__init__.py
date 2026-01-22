"""Ingestion pipeline for HR data processing."""

from .pdf_parser import PDFParser
from .chunker import SemanticChunker, Chunk

__version__ = "1.0.0"
__all__ = ['PDFParser', 'SemanticChunker', 'Chunk']
