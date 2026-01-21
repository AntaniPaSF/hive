# LLM API Contract for Benchmark Suite

**Version**: 1.0  
**Date**: 2026-01-21  
**Purpose**: Defines the expected HTTP API contract between the benchmark suite and the LLM backend

---

## Base URL

**Development/Local**: `http://localhost:8080`  
**Configurable via**: `BENCHMARK_API_URL` environment variable or `--api-url` CLI argument

---

## Endpoints

### POST /ask

Send a question to the LLM and receive an answer with citations.

**Request**:
```http
POST /ask HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "question": "How do I request vacation time?"
}
```

**Request Schema**:
```yaml
type: object
required:
  - question
properties:
  question:
    type: string
    description: The question to ask the LLM
    minLength: 1
    example: "How do I request vacation time?"
```

**Response** (Success - 200 OK):
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "answer": "Submit a vacation request through the employee portal at least 2 weeks in advance.",
  "citations": [
    {
      "document": "HR_Policy_2026.md",
      "section": "Time Off"
    }
  ]
}
```

**Response Schema**:
```yaml
type: object
required:
  - answer
  - citations
properties:
  answer:
    type: string
    description: The LLM's response to the question
  citations:
    type: array
    description: List of source documents referenced
    minItems: 0
    items:
      type: object
      required:
        - document
        - section
      properties:
        document:
          type: string
          description: Document name or identifier
          example: "HR_Policy_2026.md"
        section:
          type: string
          description: Section within the document
          example: "Time Off"
        relevance_score:
          type: number
          description: Optional relevance score from RAG pipeline
          minimum: 0.0
          maximum: 1.0
```

**Response** (Error - 4xx/5xx):
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "CITATION_REQUIRED",
  "message": "This system requires source citations. Please provide or ingest documents and reference at least one source."
}
```

**Error Response Schema**:
```yaml
type: object
required:
  - error
  - message
properties:
  error:
    type: string
    description: Error code
    enum: [CITATION_REQUIRED, INVALID_REQUEST, INTERNAL_ERROR, TIMEOUT]
  message:
    type: string
    description: Human-readable error description
```

**Timeout**: 5 seconds (per FR-011)  
**Retry Logic**: Single retry with exponential backoff (benchmark suite handles)

---

### GET /health

Health check endpoint to verify the API is reachable.

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:8080
```

**Response** (Success - 200 OK):
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok"
}
```

**Response Schema**:
```yaml
type: object
required:
  - status
properties:
  status:
    type: string
    enum: [ok, degraded, error]
```

---

## Constitution Compliance

### Accuracy Over Speed
- The API MUST NOT return answers without supporting citations (enforced at response layer)
- Responses without citations MUST return HTTP 400 with error code `CITATION_REQUIRED`

### Transparency
- The `citations` array MUST include at least one citation per response
- Each citation MUST include both `document` and `section` fields

### Self-Contained
- The API runs locally on localhost (no external dependencies)
- All required models/embeddings are pre-downloaded and self-hosted

### Reproducible
- The API endpoint is deterministic for the same input (given the same knowledge base state)
- Version information should be available via `/health` or similar endpoint (future enhancement)

---

## Benchmark Suite Expectations

The benchmark suite will:

1. **Send Questions**: POST each question from `ground_truth.yaml` to `/ask`
2. **Measure Latency**: Record time from request start to response receipt
3. **Validate Citations**: 
   - Check that `citations` array exists and is non-empty
   - Validate each citation has `document` and `section` fields
   - Count citation coverage across all responses
4. **Validate Accuracy**:
   - Compare `answer` to `expected_answer` using fuzzy matching
   - Accept answer variations as defined in ground truth
5. **Handle Errors**:
   - Treat HTTP 4xx/5xx as `ERROR` status in results
   - Retry once on timeout/connection errors
   - Continue with remaining questions (don't fail entire suite)

---

## Example Interaction

**Scenario**: Benchmark asks a vacation policy question

```bash
# Request (from benchmark suite)
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I request vacation time?"}'

# Response (from LLM API)
{
  "answer": "You can submit a vacation request through the employee portal with at least 2 weeks notice.",
  "citations": [
    {
      "document": "HR_Policy_2026.md",
      "section": "Time Off"
    }
  ]
}

# Benchmark Validation:
# 1. Latency: 2340 ms (< 10s ✓)
# 2. Citation: Present, valid structure ✓
# 3. Accuracy: Fuzzy match score = 0.87 (>= 0.8 ✓)
# Result: PASS
```

---

## Future Extensions (Post-MVP)

- **Authentication**: Add bearer token or API key support
- **Batch Requests**: POST multiple questions in single request
- **Streaming**: Server-sent events for long-running responses
- **Versioning**: `/v1/ask` endpoint with version negotiation
- **Feedback**: POST `/feedback` to report incorrect answers
- **Metrics**: GET `/metrics` for Prometheus scraping

---

## Contract Versioning

**Current Version**: 1.0  
**Breaking Changes**: Require MAJOR version bump (2.0)  
**Additive Changes**: Require MINOR version bump (1.1)  
**Fixes/Clarifications**: PATCH version bump (1.0.1)

**Compatibility**: The benchmark suite should gracefully handle:
- Additional fields in responses (ignore unknown fields)
- Missing optional fields (e.g., `relevance_score`)
- New error codes (treat as generic `INTERNAL_ERROR`)
