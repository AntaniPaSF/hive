# RAG LLM Service Architecture

## System Overview

The RAG LLM Service is a Retrieval-Augmented Generation pipeline that answers natural language questions using internal documentation as the knowledge source. It combines semantic search, context assembly, and LLM generation to produce grounded, cited answers.

**Core Principle**: Only answer questions using information present in the document corpus. If insufficient information is found, respond with "I don't know."

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG LLM Service                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   FastAPI    │  │ RAG Service  │  │   Ollama     │         │
│  │   Server     │→ │ Orchestrator │→ │   Client     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                   │               │
│         ↓                  ↓                   ↓               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Validators  │  │  Retrieval   │  │   Prompts    │         │
│  │  & Schemas   │  │   Client     │  │  & Parsers   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         │                  │                   │
         ↓                  ↓                   ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  HTTP API    │  │  ChromaDB    │  │    Ollama    │
│   Clients    │  │ Vector Store │  │ LLM Service  │
└──────────────┘  └──────────────┘  └──────────────┘
         │                  │                   │
         ↓                  ↓                   ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ HR Pipeline  │  │  Embeddings  │  │  Mistral 7B  │
│ Embedding API│  │   (384-dim)  │  │    Model     │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Component Architecture

### 1. API Layer (`src/server.py`)

**Responsibilities**:
- REST API endpoints (`/query`, `/health`)
- Request validation (Pydantic models)
- Error handling and HTTP response formatting
- Request logging with structured IDs
- CORS middleware

**Key Components**:
- **FastAPI Application**: ASGI server with automatic OpenAPI docs
- **Request Models**: `QueryRequest` with validation rules
- **Response Models**: `Answer`, `Citation` schemas
- **Exception Handlers**: Custom handlers for `InvalidQuery`, `VectorStoreUnavailable`, etc.

**Flow**:
```
HTTP Request → Validation → RAG Service → Response Formatting → HTTP Response
```

---

### 2. RAG Orchestrator (`src/rag_service.py`)

**Responsibilities**:
- Coordinate retrieval, generation, and citation extraction
- Manage confidence threshold logic
- Handle "I don't know" responses
- Request ID generation and tracking

**Pipeline Stages**:

1. **Query Embedding**
   - Calls HR Pipeline embedding API
   - Validates 384-dimensional vector

2. **Retrieval**
   - Queries ChromaDB with embedding
   - Applies filters (source, max_results)
   - Ranks chunks by similarity

3. **Context Assembly**
   - Formats retrieved chunks for LLM prompt
   - Includes document metadata for citation

4. **Generation**
   - Sends context + question to Ollama
   - Receives LLM answer with citations

5. **Citation Extraction**
   - Parses `[document, section]` markers
   - Validates citations against retrieved chunks
   - Rejects answers without valid citations

6. **Confidence Evaluation**
   - Calculates confidence from similarity scores
   - Returns "I don't know" if below threshold

**Code Structure**:
```python
class RAGService:
    def __init__(self, retrieval_client, ollama_client, embedding_client)
    
    async def query(question: str, filters: dict) -> Answer:
        # 1. Embed question
        embedding = await embedding_client.embed(question)
        
        # 2. Retrieve context
        chunks = await retrieval_client.query(embedding, filters)
        
        # 3. Generate answer
        raw_answer = await ollama_client.generate(prompt, context)
        
        # 4. Extract & validate citations
        citations = extract_citations(raw_answer, chunks)
        
        # 5. Calculate confidence
        confidence = calculate_confidence(chunks)
        
        # 6. Return answer or "I don't know"
        return Answer(...) if confidence >= threshold else I_DONT_KNOW
```

---

### 3. Retrieval Client (`src/core/retrieval.py`)

**Responsibilities**:
- Query ChromaDB vector store
- Apply filters and ranking
- Extract metadata from results
- Health check for vector store

**Features**:
- **Similarity Search**: Cosine similarity with top-k ranking
- **Metadata Extraction**: Document name, page number, section
- **Confidence Calculation**: Average of top-k similarity scores
- **Error Handling**: Retry logic for transient failures

**Configuration**:
- Vector store URL: `VECTOR_STORE_URL`
- Collection name: `VECTOR_STORE_COLLECTION`
- Default max results: 5 (configurable via filters)

---

### 4. Ollama Client (`src/core/ollama_client.py`)

**Responsibilities**:
- Interface with Ollama LLM API
- Generate answers from prompts
- Retry logic for reliability
- Health check for LLM service

**Features**:
- **Model**: Mistral 7B (configurable)
- **Temperature**: 0.1 (low randomness for factual answers)
- **Streaming**: Disabled (batch generation)
- **Retry**: Exponential backoff on 500 errors
- **Timeout**: 60 seconds

**Configuration**:
- Ollama host: `OLLAMA_HOST`
- Model name: `OLLAMA_MODEL`
- Max retries: 3

---

### 5. Embedding Client (`src/core/embedding_client.py`)

**Responsibilities**:
- Call HR Pipeline embedding API
- Validate embedding dimensions
- Cache embeddings (future optimization)

**Features**:
- **Model**: all-MiniLM-L6-v2 (384 dimensions)
- **Validation**: Dimension mismatch detection
- **Retry**: 3 attempts with exponential backoff

**Configuration**:
- API URL: `EMBEDDING_API_URL`
- Expected dimensions: 384

---

### 6. Prompt Engineering (`src/prompts/`)

**QA Prompt Template** (`qa_prompt.py`):
```
You are a corporate assistant. Answer questions using ONLY the provided context.

CONTEXT:
{context}

QUESTION: {question}

CITATION FORMAT: [document_name, section_name]

Rules:
1. Only use information from CONTEXT
2. Include citations after each fact
3. If information is insufficient, say "I don't know"
```

**Citation Parser** (`citation_parser.py`):
- Regex-based extraction: `\[([^,]+),\s*([^\]]+)\]`
- Validation against retrieved chunks
- Deduplication of citations

---

## Data Flow

### Successful Query Flow

```
1. User Question
   ↓
2. Embed Question (HR Pipeline API)
   ↓
3. Query Vector Store (ChromaDB)
   ↓
4. Retrieve Top-K Chunks (ranked by similarity)
   ↓
5. Format Prompt (context + question)
   ↓
6. Generate Answer (Ollama LLM)
   ↓
7. Extract Citations (regex parsing)
   ↓
8. Validate Citations (match against chunks)
   ↓
9. Calculate Confidence (average similarity)
   ↓
10. Return Answer (if confidence >= threshold)
    OR
    Return "I don't know" (if confidence < threshold)
```

### Low Confidence Flow

```
1. Query → Embed → Retrieve
   ↓
2. Low Similarity Scores (< 0.5 average)
   ↓
3. Confidence Evaluation
   ↓
4. Return "I don't know" Response
   {
     "answer": null,
     "citations": [],
     "confidence": 0.0,
     "message": "Information not found in the knowledge base."
   }
```

---

## Error Handling

### Error Propagation Strategy

**Principle**: Fail fast with clear error messages

```
Layer 1: External Services (ChromaDB, Ollama, Embedding API)
  → Detect errors, retry if transient
  ↓
Layer 2: Core Clients (retrieval, ollama, embedding)
  → Raise domain-specific exceptions
  ↓
Layer 3: RAG Service
  → Log error, propagate to API layer
  ↓
Layer 4: FastAPI Server
  → Convert to HTTP error, return JSON response
```

### Exception Hierarchy

```
RAGServiceException (base)
├── InvalidQuery
│   ├── QuestionTooShort
│   ├── QuestionTooLong
│   └── InvalidFilters
├── VectorStoreUnavailable
├── OllamaUnavailable
├── EmbeddingAPIUnavailable
├── EmbeddingDimensionMismatch
└── GenerationFailed
```

### Retry Logic

**Exponential Backoff**:
- Initial delay: 1 second
- Max retries: 3
- Backoff multiplier: 2x
- Max delay: 10 seconds

**Retryable Errors**:
- HTTP 500, 502, 503, 504
- Connection timeouts
- DNS errors

**Non-Retryable Errors**:
- HTTP 400, 401, 403, 404
- Validation errors
- Model not found

---

## Logging Architecture

### Structured JSON Logging

**Format**:
```json
{
  "timestamp": "2026-01-21T10:30:00Z",
  "level": "INFO",
  "component": "rag_service",
  "request_id": "req_20260121_abc123",
  "message": "Query processing started",
  "question": "What is the vacation policy?",
  "processing_time_ms": 3420
}
```

**Log Levels**:
- **DEBUG**: Detailed pipeline tracing (similarity scores, chunk content)
- **INFO**: Request lifecycle (started, completed)
- **WARNING**: Degraded performance (slow responses, low confidence)
- **ERROR**: Service failures (vector store down, LLM timeout)

**Logged Events**:
- Request received (question, filters, request_id)
- Embedding generated (time, dimension)
- Chunks retrieved (count, top similarity)
- Answer generated (time, length)
- Citations extracted (count, validity)
- Response sent (confidence, processing_time_ms)

---

## Configuration Management

### Environment Variables

**Service Configuration**:
- `RAG_SERVICE_PORT`: API port (default: 8000)
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- `MIN_CONFIDENCE_THRESHOLD`: Answer confidence threshold (default: 0.5)

**External Services**:
- `OLLAMA_HOST`: Ollama API URL
- `OLLAMA_MODEL`: LLM model name (default: mistral:7b)
- `VECTOR_STORE_URL`: ChromaDB URL
- `VECTOR_STORE_COLLECTION`: Collection name
- `EMBEDDING_API_URL`: HR Pipeline embedding API
- `EMBEDDING_MODEL`: Model name (default: all-MiniLM-L6-v2)

**Defaults** (see `.env.example`):
```env
RAG_SERVICE_PORT=8000
OLLAMA_HOST=http://localhost:11434
VECTOR_STORE_URL=http://localhost:8001
EMBEDDING_API_URL=http://localhost:8002/embed
MIN_CONFIDENCE_THRESHOLD=0.5
LOG_LEVEL=INFO
```

---

## Performance Characteristics

### Latency Breakdown (Typical Query)

| Stage | Time | Percentage |
|-------|------|------------|
| Request validation | 10ms | 0.3% |
| Embedding generation | 200ms | 5.8% |
| Vector store query | 300ms | 8.7% |
| LLM generation | 2800ms | 81.4% |
| Citation extraction | 50ms | 1.5% |
| Response formatting | 60ms | 1.7% |
| **Total** | **3420ms** | **100%** |

**Bottleneck**: Ollama LLM generation (~80% of latency)

### Throughput

**Single Instance**:
- Requests per minute: ~17 (assuming 3.5s average)
- Concurrent requests: 10 (FastAPI worker threads)

**Scaling**:
- Horizontal: Run multiple RAG service instances behind load balancer
- Vertical: Increase Ollama resources (GPU for faster generation)

---

## Security Considerations

1. **Non-Root Execution**: Docker container runs as `raguser` (UID 1000)
2. **Input Validation**: Pydantic models prevent injection attacks
3. **No Authentication** (v1.0): Add API keys or OAuth for production
4. **No Rate Limiting** (v1.0): Implement at API gateway level
5. **CORS**: Configurable origins for browser clients

---

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Individual components in isolation
- Mock external dependencies
- Validate schemas and validators
- Test error handling

### Integration Tests (`tests/integration/`)
- Full pipeline testing with mocks
- Server endpoint validation
- Error propagation testing
- Health check verification

### Coverage
- Target: >80%
- Current: 89%

---

## Deployment Architecture

### Development
```
Developer Machine
├── RAG Service (src/)
├── Ollama (local or Docker)
├── ChromaDB (HR Pipeline)
└── Embedding API (HR Pipeline)
```

### Production (Docker Compose)
```
Docker Network (rag-network)
├── ollama-service (container)
│   ├── Port: 11434
│   └── Volume: ollama-data
├── rag-llm-service (container)
│   ├── Port: 8000
│   ├── Depends: ollama-service
│   └── Volume: logs/
└── (External) HR Pipeline
    ├── ChromaDB (8001)
    └── Embedding API (8002)
```

---

## Design Decisions

### Why Ollama?
- **Self-hosted**: No external API dependencies
- **Privacy**: Data stays on-premise
- **Cost**: No per-token pricing
- **Models**: Supports Mistral, Llama, Phi

### Why ChromaDB?
- **Simple**: No complex setup
- **Fast**: Optimized for similarity search
- **Python-native**: Easy integration
- **Managed by HR Pipeline**: Single source of truth

### Why Mistral 7B?
- **Performance**: Good accuracy/speed tradeoff
- **Size**: Runs on CPU (4GB RAM)
- **License**: Apache 2.0 (commercial use)

### Why 384-dim Embeddings?
- **Model**: all-MiniLM-L6-v2 (sentence-transformers)
- **Speed**: Fast inference
- **Quality**: Sufficient for HR documentation

---

## Future Enhancements

1. **Caching**: Redis for embedding/answer caching
2. **Streaming**: Server-sent events for real-time answers
3. **Multi-hop**: Chain queries for complex questions
4. **Personalization**: User context in retrieval
5. **Analytics**: Track question patterns, low-confidence queries
6. **A/B Testing**: Experiment with models, thresholds

---

## Related Documentation

- [API.md](API.md): REST API reference
- [README.md](README.md): Quickstart and usage
- [EXAMPLES.py](EXAMPLES.py): Code examples
- [Docker Documentation](README.md#docker-deployment): Deployment guide
