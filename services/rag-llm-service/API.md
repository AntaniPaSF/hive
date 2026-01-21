# RAG LLM Service API Documentation

## Overview

The RAG LLM Service provides a REST API for intelligent question answering over internal documentation using Retrieval-Augmented Generation (RAG).

**Base URL**: `http://localhost:8000`  
**Protocol**: HTTP/1.1  
**Content-Type**: `application/json`

---

## Endpoints

### POST /query

Ask a natural language question and receive an AI-generated answer with source citations.

**Request**

```http
POST /query HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-Request-ID: custom-request-id-123 (optional)

{
  "question": "What is the vacation policy?",
  "filters": {
    "source": "employee_handbook.pdf",
    "max_results": 5
  }
}
```

**Request Schema**

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `question` | string | Yes | Natural language question | 3-1000 characters |
| `filters` | object | No | Query filters | See filters table below |

**Filters**

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `source` | string | No | Filter by document name | Must match exact filename |
| `max_results` | integer | No | Max chunks to retrieve | 1-10, default: 5 |

**Response (Success)**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "answer": "Employees are entitled to 15 days of paid vacation per year. Vacation accrues at a rate of 1.25 days per month of employment.",
  "citations": [
    {
      "document_name": "employee_handbook.pdf",
      "excerpt": "All full-time employees receive 15 days of paid vacation annually...",
      "page_number": 12,
      "section": "Vacation Policy"
    }
  ],
  "confidence": 0.87,
  "message": null,
  "request_id": "req_20260121_abc123",
  "processing_time_ms": 3420
}
```

**Response (Low Confidence - "I Don't Know")**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "answer": null,
  "citations": [],
  "confidence": 0.0,
  "message": "Information not found in the knowledge base.",
  "request_id": "req_20260121_xyz789",
  "processing_time_ms": 1250
}
```

**Response Schema**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string \| null | Generated answer (null if low confidence) |
| `citations` | Citation[] | List of source citations |
| `confidence` | float | Answer confidence score (0.0-1.0) |
| `message` | string \| null | System message (e.g., "Information not found...") |
| `request_id` | string | Unique request identifier |
| `processing_time_ms` | integer | Total processing time in milliseconds |

**Citation Schema**

| Field | Type | Description |
|-------|------|-------------|
| `document_name` | string | Source document filename |
| `excerpt` | string | Relevant text excerpt (max 200 chars) |
| `page_number` | integer \| null | Page number (if available) |
| `section` | string \| null | Section/chapter name (if available) |

**Error Responses**

**400 Bad Request - Invalid Question**
```json
{
  "detail": {
    "error": "Invalid question",
    "field": "question",
    "message": "Question too short: 2 chars (minimum 3)"
  }
}
```

**400 Bad Request - Invalid Filters**
```json
{
  "detail": {
    "error": "Invalid filters",
    "field": "filters.max_results",
    "message": "max_results must be at least 1, got 0"
  }
}
```

**500 Internal Server Error - Vector Store Unavailable**
```json
{
  "error": "VectorStoreUnavailable",
  "message": "ChromaDB is not accessible",
  "request_id": "req_20260121_error123",
  "timestamp": "2026-01-21T10:30:00Z"
}
```

**500 Internal Server Error - LLM Unavailable**
```json
{
  "error": "OllamaUnavailable",
  "message": "Ollama service is not responding",
  "request_id": "req_20260121_error456",
  "timestamp": "2026-01-21T10:31:00Z"
}
```

---

### GET /health

Check the health status of the RAG service and its dependencies.

**Request**

```http
GET /health HTTP/1.1
Host: localhost:8000
```

**Response (All Healthy)**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "ollama": "connected",
  "vector_store": "connected",
  "embedding_api": "connected",
  "timestamp": "2026-01-21T10:30:00Z"
}
```

**Response (Degraded - Some Services Down)**

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "degraded",
  "ollama": "disconnected",
  "vector_store": "connected",
  "embedding_api": "connected",
  "timestamp": "2026-01-21T10:30:00Z"
}
```

**Response Schema**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall health: "healthy", "degraded", or "unhealthy" |
| `ollama` | string | Ollama LLM status: "connected" or "disconnected" |
| `vector_store` | string | ChromaDB status: "connected" or "disconnected" |
| `embedding_api` | string | Embedding API status: "connected" or "disconnected" |
| `timestamp` | string | ISO 8601 timestamp |

**Status Codes**

| Code | Status | Description |
|------|--------|-------------|
| 200 | healthy | All services operational |
| 503 | degraded | One or more services unavailable |

---

### GET /

Get service information and API documentation link.

**Request**

```http
GET / HTTP/1.1
Host: localhost:8000
```

**Response**

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "service": "RAG LLM Service",
  "version": "1.0.0",
  "status": "operational",
  "documentation": "/docs"
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid input (question too short, invalid filters) |
| 500 | Internal Server Error | Service error (vector store unavailable, LLM error) |
| 503 | Service Unavailable | Health check failed, dependencies down |

### Application Error Codes

| Error Code | HTTP Status | Description | Resolution |
|------------|-------------|-------------|------------|
| `InvalidQuery` | 400 | Question validation failed | Check question length (3-1000 chars) |
| `InvalidFilters` | 400 | Filter validation failed | Check max_results range (1-10) |
| `VectorStoreUnavailable` | 500 | ChromaDB not accessible | Verify HR Data Pipeline is running |
| `OllamaUnavailable` | 500 | Ollama service down | Check Ollama container status |
| `EmbeddingAPIUnavailable` | 500 | Embedding API not responding | Verify HR Data Pipeline embedding service |
| `GenerationFailed` | 500 | LLM failed to generate answer | Check Ollama logs, retry request |

---

## Request/Response Examples

### Example 1: Simple Question

**Request**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many vacation days do I get?"
  }'
```

**Response**
```json
{
  "answer": "Full-time employees receive 15 days of paid vacation per year.",
  "citations": [
    {
      "document_name": "employee_handbook.pdf",
      "excerpt": "All full-time employees receive 15 days...",
      "page_number": 12,
      "section": "Vacation Policy"
    }
  ],
  "confidence": 0.92,
  "message": null,
  "request_id": "req_20260121_simple123",
  "processing_time_ms": 2800
}
```

### Example 2: Question with Filters

**Request**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the safety protocols?",
    "filters": {
      "source": "safety_manual.pdf",
      "max_results": 3
    }
  }'
```

**Response**
```json
{
  "answer": "Safety protocols require wearing protective equipment including hard hats, safety glasses, and steel-toed boots in designated areas...",
  "citations": [
    {
      "document_name": "safety_manual.pdf",
      "excerpt": "All personnel must wear PPE in construction zones...",
      "page_number": 5,
      "section": "Personal Protective Equipment"
    }
  ],
  "confidence": 0.88,
  "message": null,
  "request_id": "req_20260121_filter456",
  "processing_time_ms": 3200
}
```

### Example 3: Question Outside Knowledge Base

**Request**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the capital of France?"
  }'
```

**Response**
```json
{
  "answer": null,
  "citations": [],
  "confidence": 0.0,
  "message": "Information not found in the knowledge base.",
  "request_id": "req_20260121_unknown789",
  "processing_time_ms": 1500
}
```

### Example 4: Custom Request ID

**Request**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: my-custom-id-123" \
  -d '{
    "question": "What is the remote work policy?"
  }'
```

**Response**
```json
{
  "answer": "Employees may work remotely up to 2 days per week with manager approval...",
  "citations": [...],
  "confidence": 0.85,
  "message": null,
  "request_id": "my-custom-id-123",
  "processing_time_ms": 3100
}
```

---

## Rate Limiting

Currently, no rate limiting is enforced. For production deployments, consider:
- API gateway rate limiting (e.g., nginx limit_req)
- Per-user quotas
- Exponential backoff for retries

---

## Authentication

Currently, no authentication is required. For production deployments, consider:
- API keys (via `Authorization: Bearer <token>`)
- OAuth 2.0 / OIDC integration
- JWT tokens for user context

---

## Versioning

API version is included in the root endpoint response. Future versions may use:
- URL path versioning: `/v1/query`, `/v2/query`
- Header versioning: `Accept: application/vnd.rag.v1+json`

Current version: **1.0.0**

---

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Explore all endpoints
- Test requests directly in the browser
- View request/response schemas
- Download OpenAPI specification

---

## OpenAPI Specification

Download the OpenAPI 3.0 specification:

```bash
curl http://localhost:8000/openapi.json > openapi.json
```

Use this spec to generate client libraries in various languages.

---

## Best Practices

1. **Include Request IDs**: Use `X-Request-ID` header for request tracing
2. **Handle "I Don't Know"**: Check `answer == null` and display `message` to users
3. **Show Citations**: Always display citations to build user trust
4. **Retry on 500**: Implement exponential backoff for transient errors
5. **Validate Input**: Client-side validation prevents unnecessary API calls
6. **Monitor Latency**: Log `processing_time_ms` for performance tracking

---

## Support

For API issues or questions:
- GitHub Issues: [repository link]
- Documentation: README.md, ARCHITECTURE.md
- Contact: team@hive.local
