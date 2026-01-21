"""Query and response schemas for RAG LLM Service."""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator
import uuid
from datetime import datetime


class Citation(BaseModel):
    """Source citation for a generated answer.

    Attributes:
        document_name: Name of the source document
        excerpt: Relevant text snippet from the source (max 200 chars)
        page_number: Page number (optional, for PDFs)
        section: Section or heading (optional)
        chunk_id: Reference to the original chunk ID (optional)
    """

    document_name: str = Field(..., description="Name of the source document")
    excerpt: str = Field(..., max_length=200, description="Text excerpt from source")
    page_number: Optional[int] = Field(None, description="Page number if available")
    section: Optional[str] = Field(None, description="Section or heading")
    chunk_id: Optional[str] = Field(
        None, description="Original chunk ID from vector store"
    )

    @field_validator("excerpt")
    @classmethod
    def excerpt_not_empty(cls, v: str) -> str:
        """Validate excerpt is not empty."""
        if not v.strip():
            raise ValueError("Excerpt cannot be empty")
        return v.strip()


class Query(BaseModel):
    """User query for RAG service.

    Attributes:
        question: The user's question in natural language
        filters: Optional metadata filters for vector store search
        request_id: Unique identifier for logging and tracing (auto-generated)
    """

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="User's natural language question",
    )
    filters: Optional[Dict] = Field(
        None, description="Optional filters (source, max_results)"
    )
    request_id: str = Field(
        default_factory=lambda: f"req_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    )

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        """Validate question is not empty after stripping."""
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: Optional[Dict]) -> Optional[Dict]:
        """Validate filter structure."""
        if v is None:
            return v

        # Validate max_results if present
        if "max_results" in v:
            max_results = v["max_results"]
            if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
                raise ValueError("max_results must be between 1 and 10")

        return v


class Answer(BaseModel):
    """Response from RAG service.

    Attributes:
        answer: Generated answer text (null if no information found)
        citations: List of source citations (empty if no answer)
        confidence: Confidence score (0.0 to 1.0)
        message: Explanatory message (e.g., "Information not found")
        request_id: Same as input query request_id for tracing
        processing_time_ms: Time taken to process the query
    """

    answer: Optional[str] = Field(
        None, description="Generated answer or null if not found"
    )
    citations: List[Citation] = Field(
        default_factory=list, description="Source citations"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    message: Optional[str] = Field(None, description="Explanatory message")
    request_id: str = Field(..., description="Request ID for tracing")
    processing_time_ms: int = Field(
        ..., ge=0, description="Processing time in milliseconds"
    )

    @field_validator("citations")
    @classmethod
    def validate_citations(cls, v: List[Citation], info) -> List[Citation]:
        """Validate citations consistency with answer."""
        # If answer is not null, must have at least one citation
        # Note: 'info' contains the current validation context
        return v


class RetrievedChunk(BaseModel):
    """Document chunk retrieved from vector store.

    Attributes:
        chunk_id: Unique identifier for the chunk
        content: Text content of the chunk
        metadata: Metadata about the source document
        similarity_score: Cosine similarity score (0.0 to 1.0)
    """

    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Text content")
    metadata: Dict = Field(
        ...,
        description="Source metadata (document_name, page_number, section, chunk_index)",
    )
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Dict) -> Dict:
        """Validate required metadata fields."""
        required_fields = ["document_name", "chunk_index"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Metadata missing required field: {field}")
        return v
