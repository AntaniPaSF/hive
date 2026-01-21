# Service Interface: RAG LLM Service

**Date**: 2026-01-21  
**Feature**: Intelligent Knowledge Retrieval Service (RAG Pipeline & LLM Service)  
**Phase**: 1 (Design & Service Interface)

---

## Overview

This document defines how to interact with the RAG LLM Service and how it communicates with other system components. The RAG LLM Service is responsible for:
1. Generating embeddings for user queries
2. Querying the vector store (ChromaDB) for relevant document chunks
3. Calling Ollama to generate answers with citations
4. Returning structured responses

---

## Service Architecture

```
┌─────────────────┐
│   FastAPI       │ (Developed by colleague)
│   Wrapper       │
└────────┬────────┘
         │ HTTP/Function Call
         ▼
┌─────────────────────────────────────────┐
│   RAG LLM Service (This Component)      │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐│
│  │Embedding │─▶│Retrieval │─▶│  LLM  ││
│  │Generator │  │ Pipeline │  │Gen    ││
│  └──────────┘  └──────────┘  └───────┘│
└───────┬─────────────┬──────────────────┘
        │             │
        │             ▼
        │      ┌──────────────┐
        │      │  ChromaDB    │ (Managed externally)
        │      │ Vector Store │
        │      └──────────────┘
        ▼
  ┌──────────┐
  │  Ollama  │ (Containerized with service)
  │ Mistral  │
  │   7B     │
  └──────────┘
```

---

## Public Interface

### Method: `query(question: str, filters: Optional[Dict] = None) -> Answer`

**Purpose**: Main entry point for the RAG service. Takes a natural language question and returns an answer with citations.

**Input**:
- `question` (string, required): User's natural language question
- `filters` (dict, optional): Optional filters for vector store query
  - `source` (string): Filter by document name
  - `max_results` (int): Maximum chunks to retrieve (default: 5)

**Output**: `Answer` object (see [data-model.md](data-model.md))

**Example Usage**:
```python
from rag_service import RAGService

# Initialize service
service = RAGService(
    ollama_host="http://localhost:11434",
    vector_store_url="http://localhost:8001",
    embedding_model="nomic-embed-text"
)

# Query the service
answer = service.query(
    question="What are the safety protocols for handling chemicals?",
    filters={"source": "safety_manual.pdf", "max_results": 5}
)

print(f"Answer: {answer.answer}")
print(f"Citations: {answer.citations}")
print(f"Confidence: {answer.confidence}")
```

**Processing Flow**:
1. Generate embedding vector from question
2. Query vector store with embedding
3. Retrieve top-k relevant chunks
4. Assemble prompt context
5. Call Ollama LLM to generate answer
6. Extract citations from LLM output
7. Validate citations against retrieved chunks
8. Return Answer object

---

### Method: `health_check() -> Dict`

**Purpose**: Check service health and dependencies.

**Output**:
```python
{
    "status": "healthy" | "degraded" | "unhealthy",
    "ollama": "connected" | "unreachable",
    "vector_store": "connected" | "unreachable",
    "embedding_model": "loaded" | "not_loaded",
    "timestamp": "2026-01-21T14:32:15.123Z"
}
```

---

## Inter-Service Communication

### 1. Vector Store (ChromaDB) Integration

**Purpose**: Query vector store for semantically similar document chunks.

**Communication Protocol**: HTTP REST API

**Endpoint**: `POST {VECTOR_STORE_URL}/api/v1/collections/{collection_name}/query`

**Request**:
```python
{
    "query_embeddings": [[0.023, -0.145, ...]],  # 384-dim vector (all-MiniLM-L6-v2)
    "n_results": 5,
    "where": {"source_type": "pdf"},  # Optional metadata filter
    "include": ["documents", "metadatas", "distances"]
}
```

**Response**:
```python
{
    "ids": [["chunk_id_1", "chunk_id_2", ...]],
    "documents": [["chunk text 1", "chunk text 2", ...]],
    "metadatas": [[
        {
            "source_doc": "safety_manual.pdf",
            "source_type": "pdf",
            "page_number": 5,
            "section_title": "Chemical Handling",
            "chunk_index": 0,
            "related_topic": "Safety Protocols",
            "validation_status": {"contradiction_check": true, "duplicate_check": true}
        },
        {...}
    ]],
    "distances": [[0.13, 0.25, ...]]  # Lower is more similar (cosine)
}
```

**Error Handling**:
- Connection timeout: Retry up to 3 times with exponential backoff
- 404 Not Found: Collection doesn't exist → return "I don't know" response
- 500 Server Error: Log error and return degraded service response

**Configuration**:
- Environment variable: `VECTOR_STORE_URL` (e.g., `http://chromadb:8001`)
- Collection name: `VECTOR_STORE_COLLECTION` (e.g., `corporate_documents`)
- Timeout: `VECTOR_STORE_TIMEOUT_SECONDS` (default: 5)

---

### 2. Ollama LLM Integration

**Purpose**: Generate natural language answers from retrieved context.

**Communication Protocol**: HTTP REST API (Ollama native API)

**Endpoint**: `POST {OLLAMA_HOST}/api/generate`

**Request**:
```python
{
    "model": "mistral:7b",
    "prompt": """You are a helpful assistant. Answer the question based ONLY on the provided context. If the context does not contain the answer, respond with "I don't know." Always cite your sources using the format [document_name, page X].

Context:
[safety_manual.pdf, p.5]: All personnel must wear protective eyewear and gloves when handling Class A chemicals...
[safety_manual.pdf, p.7]: Emergency procedures require immediate notification...

Question: What are the safety protocols for handling chemicals?

Answer:""",
    "stream": false,
    "options": {
        "temperature": 0.1,  # Low temperature for factual accuracy
        "top_p": 0.9,
        "max_tokens": 500
    }
}
```

**Response**:
```python
{
    "model": "mistral:7b",
    "created_at": "2026-01-21T14:32:18.456Z",
    "response": "Personnel handling Class A chemicals must wear protective eyewear and gloves at all times [safety_manual.pdf, p.5]...",
    "done": true
}
```

**Citation Extraction**:
- Parse LLM response for citation markers: `[document_name, page X]` or `[document_name, section Y]`
- Match citations back to retrieved chunks
- If no citations found in LLM output: Return "I don't know" response

**Error Handling**:
- Connection timeout: Retry once, then fail gracefully
- Model not found: Log error and return service unavailable
- Generation timeout (>10s): Cancel request and return timeout error

**Configuration**:
- Environment variable: `OLLAMA_HOST` (e.g., `http://ollama:11434`)
- Model name: `OLLAMA_MODEL` (default: `mistral:7b`)
- Generation timeout: `OLLAMA_TIMEOUT_SECONDS` (default: 10)

---

### 3. FastAPI Wrapper Integration

**Purpose**: The RAG LLM Service is consumed by a FastAPI wrapper that exposes REST endpoints.

**Integration Pattern**: Function Call / Module Import

**Example Integration in FastAPI**:
```python
# FastAPI wrapper (developed by colleague)
from fastapi import FastAPI, HTTPException
from rag_service import RAGService
from pydantic import BaseModel

app = FastAPI()
rag_service = RAGService(
    ollama_host=os.getenv("OLLAMA_HOST"),
    vector_store_url=os.getenv("VECTOR_STORE_URL")
)

class QueryRequest(BaseModel):
    question: str
    filters: Optional[Dict] = None

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        answer = rag_service.query(
            question=request.question,
            filters=request.filters
        )
        return answer.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_endpoint():
    return rag_service.health_check()
```

**Contract**:
- RAG LLM Service provides: `RAGService` class with `query()` and `health_check()` methods
- FastAPI wrapper consumes: Import RAGService and call methods
- Data exchange: Pydantic models from [data-model.md](data-model.md)

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `mistral:7b` | Ollama model name |
| `OLLAMA_TIMEOUT_SECONDS` | `10` | Generation timeout |
| `VECTOR_STORE_URL` | `http://chromadb:8001` | ChromaDB API endpoint |
| `VECTOR_STORE_COLLECTION` | `corporate_documents` | Collection name |
| `VECTOR_STORE_TIMEOUT_SECONDS` | `5` | Query timeout |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model (must match HR pipeline) |
| `MIN_CONFIDENCE_THRESHOLD` | `0.5` | Minimum answer confidence to avoid "I don't know" |
| `MAX_RETRIEVAL_RESULTS` | `5` | Default max chunks to retrieve |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Docker Compose Integration

```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  rag-service:
    build: ./services/rag-llm-service
    environment:
      OLLAMA_HOST: http://ollama:11434
      OLLAMA_MODEL: mistral:7b
      VECTOR_STORE_URL: http://chromadb:8001
      VECTOR_STORE_COLLECTION: corporate_documents
      LOG_LEVEL: INFO
    depends_on:
      - ollama

volumes:
  ollama_data:
```

---

## Error Handling

### Error Types

1. **VectorStoreUnavailable**: ChromaDB is unreachable
   - HTTP 503 Service Unavailable
   - Log structured error with request_id

2. **OllamaUnavailable**: Ollama is unreachable or model not loaded
   - HTTP 503 Service Unavailable
   - Log structured error with request_id

3. **NoCitationsFound**: LLM generated answer without citations
   - Return "I don't know" response
   - Log warning with request_id and LLM output

4. **InvalidQuery**: Malformed query input
   - HTTP 400 Bad Request
   - Return validation error details

5. **GenerationTimeout**: Ollama generation exceeded timeout
   - HTTP 504 Gateway Timeout
   - Log timeout event with request_id

### Error Response Format

```python
{
    "answer": null,
    "citations": [],
    "confidence": 0.0,
    "message": "Service temporarily unavailable. Please try again.",
    "request_id": "req_20260121_abc123",
    "processing_time_ms": 0,
    "error_type": "VectorStoreUnavailable",
    "error_details": "Connection to vector store timed out after 5s"
}
```

---

## Performance Considerations

### Latency Targets

- Embedding generation: <500ms
- Vector store query: <1s
- Ollama generation: <5s
- Total end-to-end: <5s (p95)

### Optimization Strategies
Reuse**: Reuse embeddings from HR pipeline (all-MiniLM-L6-v2) without regeneration
2. **Connection Pooling**: Maintain persistent HTTP connections to vector store
3. **Parallel Retrieval**: Query vector store while initializing Ollama context
4. **Result Filtering**: Filter retrieved chunks by confidence threshold (>0.5) before sending to LLM
4. **Streaming**: Consider streaming LLM output for faster perceived response time (future enhancement)

---

## Testing Interface

### Sample Test Queries

Provided in `sample_queries.json`:

```json
[
    {
        "question": "What are the safety protocols for handling chemicals?",
        "expected_sources": ["safety_manual.pdf"],
        "expected_citations_count": 1
    },
    {
        "question": "What is the company vacation policy?",
        "expected_sources": ["hr_policy.pdf"],
        "expected_citations_count": 1
    },
    {
        "question": "What is the meaning of life?",
        "expected_answer": null,
        "expected_message": "Information not found in the knowledge base."
    }
]
```

### Integration Test Script

```python
# tests/integration/test_service_interface.py
import pytest
from rag_service import RAGService

@pytest.fixture
def service():
    return RAGService(
        ollama_host="http://localhost:11434",
        vector_store_url="http://localhost:8001"
    )

def test_query_with_citations(service):
    answer = service.query("What are the safety protocols?")
    assert answer.answer is not None
    assert len(answer.citations) > 0
    assert answer.confidence > 0.5

def test_query_no_information(service):
    answer = service.query("What is the meaning of life?")
    assert answer.answer is None
    assert len(answer.citations) == 0
    assert "Information not found" in answer.message
```

---

## Summary

This service interface provides:
- **Clear entry points**: `query()` and `health_check()` methods
- **Inter-service contracts**: How to communicate with ChromaDB and Ollama
- **FastAPI integration pattern**: How colleague's wrapper consumes this service
- **Configuration management**: Environment variables for all dependencies
- **Error handling**: Comprehensive error types and responses
- **Performance targets**: <5s end-to-end latency
