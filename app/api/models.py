"""
API Request/Response Models

Pydantic models for request validation and response serialization.

Related: Phase 2 (P2), Task 2.3 - API Layer
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class QueryRequest(BaseModel):
    """Request model for question answering."""
    
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Question to ask about the documents",
        examples=["What is the vacation policy?"]
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve for context"
    )
    provider: str = Field(
        default="mock",
        description="LLM provider (openai, anthropic, ollama, mock)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Model name (e.g., gpt-4, claude-3-sonnet)"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="LLM temperature (0-1, lower = more deterministic)"
    )
    max_tokens: int = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Maximum tokens in response"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata filters (e.g., {'source_filename': 'handbook.pdf'})"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is the vacation policy?",
                "top_k": 5,
                "provider": "mock",
                "temperature": 0.3
            }
        }
    )


class CitationResponse(BaseModel):
    """Citation information."""
    
    source_doc: str = Field(..., description="Source document filename")
    page_number: int = Field(..., description="Page number in document")
    section_title: Optional[str] = Field(None, description="Section title if available")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    text_excerpt: str = Field(..., description="Text excerpt from chunk")


class QueryResponse(BaseModel):
    """Response model for question answering."""
    
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer")
    citations: List[CitationResponse] = Field(
        default_factory=list,
        description="Source citations"
    )
    model: str = Field(..., description="Model used for generation")
    tokens_used: Optional[int] = Field(None, description="Tokens used (if available)")
    sources: List[str] = Field(
        default_factory=list,
        description="Unique source documents"
    )
    page_range: Optional[List[int]] = Field(
        None,
        description="Page range [min, max]"
    )
    generated_at: str = Field(..., description="ISO timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is the vacation policy?",
                "answer": "Based on the company documentation...",
                "citations": [
                    {
                        "source_doc": "handbook.pdf",
                        "page_number": 5,
                        "section_title": "Time Off",
                        "relevance_score": 0.95,
                        "text_excerpt": "Employees are entitled to..."
                    }
                ],
                "model": "gpt-4",
                "tokens_used": 150,
                "sources": ["handbook.pdf"],
                "page_range": [5, 6],
                "generated_at": "2026-01-22T12:00:00Z"
            }
        }
    )


class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    
    file_path: str = Field(
        ...,
        description="Path to PDF file to ingest",
        examples=["data/pdf/handbook.pdf"]
    )
    batch: bool = Field(
        default=False,
        description="Process entire directory if True"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_path": "data/pdf/company_handbook.pdf",
                "batch": False
            }
        }
    )


class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    
    status: str = Field(..., description="Status (success, error)")
    message: str = Field(..., description="Status message")
    documents_processed: int = Field(
        default=0,
        description="Number of documents processed"
    )
    chunks_created: int = Field(
        default=0,
        description="Number of chunks created"
    )
    processing_time: float = Field(
        default=0.0,
        description="Processing time in seconds"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors if any"
    )


class DocumentInfo(BaseModel):
    """Information about an ingested document."""
    
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Document filename")
    chunk_count: int = Field(..., description="Number of chunks")
    total_tokens: int = Field(..., description="Total tokens in document")
    page_count: int = Field(..., description="Number of pages")
    ingested_at: str = Field(..., description="Ingestion timestamp")


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    
    documents: List[DocumentInfo] = Field(
        default_factory=list,
        description="List of ingested documents"
    )
    total_count: int = Field(..., description="Total number of documents")


class ChunkInfo(BaseModel):
    """Information about a document chunk."""
    
    chunk_id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Chunk text content")
    page_number: int = Field(..., description="Page number")
    section_title: Optional[str] = Field(None, description="Section title")
    token_count: int = Field(..., description="Token count")


class ChunksResponse(BaseModel):
    """Response model for document chunks."""
    
    document_id: str = Field(..., description="Document identifier")
    chunks: List[ChunkInfo] = Field(
        default_factory=list,
        description="List of chunks"
    )
    total_count: int = Field(..., description="Total number of chunks")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    database: str = Field(..., description="Database status")
    timestamp: str = Field(..., description="Current timestamp")
    components: Dict[str, str] = Field(
        default_factory=dict,
        description="Component statuses"
    )


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Invalid request parameters",
                "detail": "Question must be between 1 and 1000 characters",
                "timestamp": "2026-01-22T12:00:00Z"
            }
        }
    )


class SearchRequest(BaseModel):
    """Request model for document search (retrieval only)."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query",
        examples=["vacation policy"]
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of results to return"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata filters"
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score"
    )


class SearchResultItem(BaseModel):
    """Single search result."""
    
    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Chunk text")
    score: float = Field(..., description="Relevance score")
    source_doc: str = Field(..., description="Source document")
    page_number: int = Field(..., description="Page number")
    section_title: Optional[str] = Field(None, description="Section title")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class SearchResponse(BaseModel):
    """Response model for search."""
    
    query: str = Field(..., description="Search query")
    results: List[SearchResultItem] = Field(
        default_factory=list,
        description="Search results"
    )
    total_results: int = Field(..., description="Total number of results")
    retrieved_at: str = Field(..., description="Retrieval timestamp")
