# Quickstart Guide: RAG LLM Service

**Date**: 2026-01-21  
**Feature**: Intelligent Knowledge Retrieval Service (RAG Pipeline & LLM Service)  
**Phase**: 1 (Design & Service Interface)

---

## Overview

This guide helps developers set up and use the RAG LLM Service locally. You'll be able to:
1. Run Ollama with Mistral 7B model
2. Start the RAG LLM Service container
3. Query the service and receive answers with citations
4. Run tests to verify functionality

**Time to complete**: ~15 minutes

---

## Prerequisites

- Docker and Docker Compose installed
- 8GB+ RAM available (for Ollama + Mistral 7B)
- Access to ChromaDB instance (URL provided by data engineer)
- Git repository cloned

---

## Step 1: Environment Setup

### 1.1 Create Environment File

Copy the example environment file and configure it:

```bash
cd services/rag-llm-service
cp .env.example .env
```

### 1.2 Configure Environment Variables

Edit `.env` file:

```bash
# Ollama Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral:7b
OLLAMA_TIMEOUT_SECONDS=10

# Vector Store Configuration (provided by data engineer)
VECTOR_STORE_URL=http://chromadb:8001
VECTOR_STORE_COLLECTION=corporate_documents
VECTOR_STORE_TIMEOUT_SECONDS=5

# Embedding Configuration (must match HR Data Pipeline)
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_RETRIEVAL_RESULTS=5
MIN_CONFIDENCE_THRESHOLD=0.5

# Logging
LOG_LEVEL=INFO
```

**Note**: Replace `VECTOR_STORE_URL` with the actual ChromaDB endpoint provided by your data engineer.

---

## Step 2: Start Ollama and Download Model

### 2.1 Start Ollama Container

```bash
docker-compose up -d ollama
```

### 2.2 Download Mistral 7B Model

This may take a few minutes (~4-5GB download):

```bash
docker exec -it rag-llm-service-ollama-1 ollama pull mistral:7b
```

**Note**: The embedding model (`all-MiniLM-L6-v2`) is automatically managed by the HR Data Pipeline service. The RAG service consumes pre-computed embeddings.

**Expected output**:
```
pulling manifest
pulling 4a03d6d1aa9c... 100% ▕████████████████▏ 4.1 GB
pulling 8c5d9cd8e0e9... 100% ▕████████████████▏  127 B
pulling 5c9a1f3bbda1... 100% ▕████████████████▏   32 B
pulling f04a4b4c2d90... 100% ▕████████████████▏  490 B
success
```

### 2.3 Verify Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

**Expected output**:
```json
{
  "models": [
    {
      "name": "mistral:7b",
      "modified_at": "2026-01-21T14:00:00Z",
      "size": 4109865159
    }
  ]
}
```

---

## Step 3: Build and Start RAG Service

### 3.1 Build Docker Image

```bash
docker-compose build rag-service
```

### 3.2 Start RAG Service

```bash
docker-compose up -d rag-service
```

### 3.3 Check Service Health

```bash
docker-compose logs rag-service
```

**Expected output**:
```json
{
  "timestamp": "2026-01-21T14:32:15.123Z",
  "level": "INFO",
  "component": "initialization",
  "event": "service_started",
  "data": {
    "ollama_status": "connected",
    "vector_store_status": "connected",
    "embedding_model": "loaded"
  }
}
```

---

## Step 4: Test the Service

### 4.1 Interactive Python Test

Start a Python shell in the container:

```bash
docker exec -it rag-llm-service-rag-service-1 python
```

Run a test query:

```python
from src import RAGService

# Initialize service
service = RAGService()

# Query the service
answer = service.query(
    question="What are the safety protocols for handling chemicals?"
)

print(f"Answer: {answer.answer}")
print(f"Citations: {[c.document_name for c in answer.citations]}")
print(f"Confidence: {answer.confidence}")
print(f"Processing time: {answer.processing_time_ms}ms")
```

**Expected output** (if vector store has safety_manual.pdf):
```
Answer: Personnel handling Class A chemicals must wear protective eyewear and gloves at all times [safety_manual.pdf, p.5]...
Citations: ['safety_manual.pdf']
Confidence: 0.87
Processing time: 3420ms
```

### 4.2 Test "I Don't Know" Scenario

```python
answer = service.query(question="What is the meaning of life?")

print(f"Answer: {answer.answer}")
print(f"Message: {answer.message}")
print(f"Citations: {answer.citations}")
```

**Expected output**:
```
Answer: None
Message: Information not found in the knowledge base.
Citations: []
```

### 4.3 Run Automated Tests

Exit Python shell and run pytest:

```bash
docker exec -it rag-llm-service-rag-service-1 pytest tests/ -v
```

**Expected output**:
```
tests/unit/test_ollama_client.py::test_generate PASSED
tests/unit/test_retrieval.py::test_query_vector_store PASSED
tests/unit/test_citation_parser.py::test_extract_citations PASSED
tests/integration/test_query_flow.py::test_end_to_end_query PASSED
======================== 4 passed in 12.3s ========================
```

---

## Step 5: Sample Query Workflow

### 5.1 Load Sample Queries

Sample test queries are provided in `sample_queries.json`:

```bash
cat sample_queries.json
```

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
    }
]
```

### 5.2 Run Sample Queries

```bash
docker exec -it rag-llm-service-rag-service-1 python scripts/run_sample_queries.py
```

**Expected output**:
```
Running sample queries...
[1/2] What are the safety protocols for handling chemicals?
  ✓ Answer generated
  ✓ Citations found: 1
  ✓ Expected source: safety_manual.pdf
  ✓ Processing time: 3420ms

[2/2] What is the company vacation policy?
  ✓ Answer generated
  ✓ Citations found: 1
  ✓ Expected source: hr_policy.pdf
  ✓ Processing time: 2890ms

All sample queries passed!
```

---

## Step 6: Integration with FastAPI Wrapper

### 6.1 Usage Pattern for FastAPI Developer

Your colleague developing the FastAPI wrapper can import and use the RAG service:

```python
# In FastAPI project
from rag_service import RAGService
from fastapi import FastAPI

app = FastAPI()
rag = RAGService()

@app.post("/query")
async def query_endpoint(question: str):
    answer = rag.query(question=question)
    return {
        "answer": answer.answer,
        "citations": [c.dict() for c in answer.citations],
        "confidence": answer.confidence
    }
```

### 6.2 API Contract

See [service-interface.md](service-interface.md) for complete API contract and integration patterns.

---

## Troubleshooting

### Issue: Ollama model not found

**Symptom**:
```
ERROR: Model 'mistral:7b' not found
```

**Solution**:
```bash
docker exec -it rag-llm-service-ollama-1 ollama pull mistral:7b
```

---

### Issue: Vector store connection timeout

**Symptom**:
```json
{
  "error_type": "VectorStoreUnavailable",
  "error_details": "Connection to vector store timed out"
}
```

**Solution**:
1. Verify ChromaDB is running:
   ```bash
   curl http://localhost:8001/api/v1/heartbeat
   ```
2. Check `VECTOR_STORE_URL` in `.env` file
3. Contact data engineer for correct ChromaDB endpoint

---

### Issue: Slow response time (>10s)

**Symptom**: Queries take longer than expected

**Solutions**:
1. Check CPU usage: `docker stats`
2. Reduce `MAX_RETRIEVAL_RESULTS` in `.env` (try 3 instead of 5)
3. Use faster model: `OLLAMA_MODEL=mistral:7b-instruct-q4_0` (quantized version)

---

### Issue: No citations in answer

**Symptom**: Answer generated but `citations` array is empty

**Solution**:
1. Check LLM output in logs for citation markers
2. Verify prompt template includes citation instructions
3. Adjust temperature (lower = more factual): Edit prompt in `src/prompts/qa_prompt.py`

---

## Performance Benchmarks

Expected performance on a modern 8-core CPU:

| Operation | Latency (p50) | Latency (p95) |
|-----------|---------------|---------------|
| Embedding generation | 300ms | 500ms |
| Vector store query | 600ms | 1000ms |
| Ollama generation | 3000ms | 5000ms |
| **Total end-to-end** | **4000ms** | **6500ms** |

**Note**: Performance improves with GPU acceleration (not required for MVP).

---

## Next Steps

1. **Review Data Model**: See [data-model.md](data-model.md) for entity schemas
2. **Review Service Interface**: See [service-interface.md](service-interface.md) for API contracts
3. **Add Custom Prompts**: Edit `src/prompts/qa_prompt.py` to customize LLM behavior
4. **Run Integration Tests**: See `tests/integration/` for end-to-end test examples
5. **Monitor Logs**: Use `docker-compose logs -f rag-service` to watch structured logs

---

## Support

- **Data Model Questions**: See [data-model.md](data-model.md)
- **Integration Questions**: See [service-interface.md](service-interface.md)
- **Dependency Issues**: Contact data engineer (ChromaDB) or backend engineer (FastAPI)
- **LLM Issues**: Check Ollama documentation: https://ollama.ai/docs

---

**Congratulations!** You now have a running RAG LLM Service that can answer questions with citations.
