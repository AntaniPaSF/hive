# Data Model: RAG LLM Service

**Date**: 2026-01-21  
**Feature**: Intelligent Knowledge Retrieval Service (RAG Pipeline & LLM Service)  
**Phase**: 1 (Design & Service Interface)

---

## Overview

This document defines the core data entities used by the RAG LLM Service. The service handles three primary flows:
1. **Query Flow**: Receive question → retrieve context → generate answer with citations
2. **Retrieval Flow**: Query vector store → receive document chunks with metadata
3. **Generation Flow**: LLM generates answer → extract citations → validate

---

## Core Entities

### 1. Query

Represents a user's natural language question submitted to the RAG service.

**Attributes**:
- `question` (string, required): The user's question in natural language
- `filters` (dict, optional): Optional metadata filters for vector store search
  - `source` (string): Filter by document source/name
  - `max_results` (int): Maximum number of chunks to retrieve (default: 5)
- `request_id` (string, auto-generated): Unique identifier for logging and tracing

**Example**:
```python
{
    "question": "What are the safety protocols for handling chemicals?",
    "filters": {
        "source": "safety_manual.pdf",
        "max_results": 5
    },
    "request_id": "req_20260121_abc123"
}
```

**Validation Rules**:
- `question` must be non-empty string (min 3 chars, max 1000 chars)
- `filters.max_results` must be between 1 and 10

---

### 2. RetrievedChunk

Represents a document chunk retrieved from the vector store.

**Attributes**:
- `chunk_id` (string, required): Unique identifier for the chunk in vector store
- `content` (string, required): The text content of the chunk
- `metadata` (dict, required): Metadata about the source document
  - `document_name` (string): Name of the source document
  - `page_number` (int, optional): Page number (for PDFs)
  - `section` (string, optional): Section or heading within document
  - `chunk_index` (int): Position of chunk within document
- `similarity_score` (float, required): Cosine similarity score (0.0 to 1.0)

**Example**:
```python
{
    "chunk_id": "chunk_safety_manual_p5_0",
    "content": "All personnel must wear protective eyewear and gloves when handling Class A chemicals...",
    "metadata": {
        "document_name": "safety_manual.pdf",
        "page_number": 5,
        "section": "Chemical Handling Procedures",
        "chunk_index": 0
    },
    "similarity_score": 0.87
}
```

---

### 3. Citation

Represents a source reference extracted from the generated answer.

**Attributes**:
- `document_name` (string, required): Name of the source document
- `excerpt` (string, required): Relevant text snippet from the source (max 200 chars)
- `page_number` (int, optional): Page number (if available)
- `section` (string, optional): Section or heading (if available)
- `chunk_id` (string, optional): Reference to the original chunk ID

**Example**:
```python
{
    "document_name": "safety_manual.pdf",
    "excerpt": "All personnel must wear protective eyewear and gloves when handling Class A chemicals...",
    "page_number": 5,
    "section": "Chemical Handling Procedures",
    "chunk_id": "chunk_safety_manual_p5_0"
}
```

**Citation Format**:
- Citations should be presented as: `[document_name, page X]` or `[document_name, section Y]`
- If page number unavailable: `[document_name]`

---

### 4. Answer

Represents the complete response from the RAG service.

**Attributes**:
- `answer` (string, nullable): The generated answer text (null if no information found)
- `citations` (list[Citation], required): List of source citations (empty if no answer)
- `confidence` (float, required): Confidence score (0.0 to 1.0)
- `message` (string, optional): Explanatory message (e.g., "Information not found in knowledge base")
- `request_id` (string, required): Same as input query request_id for tracing
- `processing_time_ms` (int, required): Time taken to process the query

**Example (Successful Response)**:
```python
{
    "answer": "Personnel handling Class A chemicals must wear protective eyewear and gloves at all times. This is required under Section 3.2 of the Chemical Handling Procedures.",
    "citations": [
        {
            "document_name": "safety_manual.pdf",
            "excerpt": "All personnel must wear protective eyewear and gloves when handling Class A chemicals...",
            "page_number": 5,
            "section": "Chemical Handling Procedures"
        }
    ],
    "confidence": 0.87,
    "message": null,
    "request_id": "req_20260121_abc123",
    "processing_time_ms": 3420
}
```

**Example ("I Don't Know" Response)**:
```python
{
    "answer": null,
    "citations": [],
    "confidence": 0.0,
    "message": "Information not found in the knowledge base.",
    "request_id": "req_20260121_xyz789",
    "processing_time_ms": 1250
}
```

**Validation Rules**:
- If `answer` is not null, `citations` must have at least 1 entry
- If `answer` is null, `citations` must be empty and `message` must be provided
- `confidence` calculated as average similarity score of retrieved chunks- If `confidence` < 0.5, system should return "I don't know" response instead of uncertain answer (align with SC-001: 0% hallucination)
---

## Internal Processing Entities

### 5. EmbeddingVector

Represents the vector representation of a query for semantic search.

**Attributes**:
- `vector` (list[float], required): Dense vector representation (384 dimensions)
- `model_name` (string, required): Name of embedding model used (must be "all-MiniLM-L6-v2")
- `dimension` (int, required): Vector dimensionality (384)

**Example**:
```python
{
    "vector": [0.023, -0.145, 0.892, ...],  # 384 dimensions
    "model_name": "all-MiniLM-L6-v2",
    "dimension": 384
}
```

---

### 6. PromptContext

Represents the context assembled for the LLM prompt.

**Attributes**:
- `question` (string, required): Original user question
- `retrieved_chunks` (list[RetrievedChunk], required): Retrieved document chunks
- `system_prompt` (string, required): System instructions for LLM
- `formatted_context` (string, required): Formatted context string for LLM

**Example**:
```python
{
    "question": "What are the safety protocols?",
    "retrieved_chunks": [...],  # List of RetrievedChunk objects
    "system_prompt": "You are a helpful assistant. Answer based ONLY on the provided context...",
    "formatted_context": "Context 1 [safety_manual.pdf, p.5]: All personnel must wear...\nContext 2 [...]..."
}
```

---

## Entity Relationships

```
Query
  └─> EmbeddingVector (generated from question)
      └─> Vector Store Query
          └─> RetrievedChunk[] (top-k results)
              └─> PromptContext (assembled for LLM)
                  └─> Ollama LLM Generation
                      └─> Answer
                          └─> Citation[] (extracted from chunks)
```

---

## Schema Validation

All entities should be validated using Pydantic models for type safety and runtime validation:

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict

class Query(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    filters: Optional[Dict] = None
    request_id: str = Field(default_factory=generate_request_id)
    
    @validator('question')
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()

class Citation(BaseModel):
    document_name: str
    excerpt: str = Field(..., max_length=200)
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_id: Optional[str] = None

class Answer(BaseModel):
    answer: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    message: Optional[str] = None
    request_id: str
    processing_time_ms: int
    
    @validator('citations')
    def validate_citations(cls, v, values):
        if values.get('answer') is not None and len(v) == 0:
            raise ValueError('Answer must have at least one citation')
        if values.get('answer') is None and len(v) > 0:
            raise ValueError('Citations must be empty when answer is null')
        return v
```

---

## Logging Schema

For structured JSON logging, each log entry should include:

```python
{
    "timestamp": "2026-01-21T14:32:15.123Z",
    "request_id": "req_20260121_abc123",
    "level": "INFO",  # INFO, WARNING, ERROR
    "component": "retrieval" | "generation" | "embedding",
    "event": "query_received" | "chunks_retrieved" | "answer_generated",
    "data": {
        "question_length": 45,
        "chunks_retrieved": 5,
        "processing_time_ms": 3420,
        "confidence": 0.87
    },
    "error": null  # Error details if level=ERROR
}
```

---

## Summary

This data model provides:
- **Type-safe entities** with Pydantic validation
- **Clear relationships** between query, retrieval, and generation stages
- **Citation tracking** from source chunks to final answer
- **Structured logging** for observability
- **Validation rules** to enforce constitution principles (citation requirements)
