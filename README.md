# Hive – Corporate Digital Assistant (Local MVP Skeleton)

This repository provides a self-contained, CPU-only local MVP skeleton for the Corporate Digital Assistant, aligned with the Constitution:

- Accuracy Over Speed (citation enforcement at response layer)
- Transparency (answers include source references)
- Self-Contained (no paid/cloud APIs post-clone)
- Reproducible (single-command startup; pinned dependencies)

## Current Status

**Phase 1 (P1): PDF Ingestion Pipeline** - ✅ Complete (Merged to main)
- PDF parsing with structure extraction
- Semantic chunking with token counting
- ChromaDB storage (text-based search)
- CLI ingestion tool

**Phase 2 (P2): Query & RAG Pipeline** - ✅ Complete (All Tasks)
- Task 2.1: Query/Retrieval Interface ✅
  - Text-based search with ChromaDB
  - Interactive CLI for testing
  - Comprehensive filtering and context retrieval
- Task 2.2: RAG Pipeline ✅
  - Multi-provider LLM support (OpenAI, Anthropic, Ollama, Mock)
  - Question answering with citations
  - Batch processing capabilities
  - Interactive Q&A interface
- Task 2.3: API Layer ✅
  - FastAPI REST API with 8 endpoints
  - OpenAPI/Swagger documentation
  - Request validation and error handling
  - 26/27 integration tests passing
- Task 2.4: Testing & Optimization ✅
  - Performance benchmarking suite
  - Query accuracy evaluation
  - Retrieval precision/recall metrics
  - Load testing & concurrency
  - Memory profiling utilities
  - Response caching layer
  - Comprehensive test runner

## Quickstart (Local)

### Using Docker (Legacy)

1. Export ports (no hardcoded defaults):

```bash
export APP_PORT=8080
export N8N_PORT=5678
export N8N_BASE_PATH=/n8n
```

2. Build and start:

```bash
make setup  # base compose only; no port needed
make start  # uses runtime compose; requires APP_PORT
```

3. Open UI:

- http://localhost:${APP_PORT}
- Health: http://localhost:${APP_PORT}/health

### Using Python (Current Development)

1. Setup virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

2. Ingest documents:

```bash
# Ingest a single PDF
python -m app.ingestion.cli --source data/pdf/your_document.pdf

# View ingestion statistics
python -m app.ingestion.cli --stats
```

3. Query documents (Retrieval only):

```bash
# Search documents
python -m app.query.cli search "vacation policy" --top-k 5

# Interactive search
python -m app.query.cli interactive
```

4. Ask questions (RAG with LLM):

```bash
# Ask with mock LLM (no API key needed)
python -m app.rag.cli ask "What is the vacation policy?"

# Interactive Q&A
python -m app.rag.cli interactive

# Batch processing
python -m app.rag.cli batch sample_questions.txt
```

5. Run the API server:

```bash
# Start FastAPI server
python -m uvicorn app.api.app:app --reload --host 0.0.0.0 --port 8000

# Access API documentation
# Open browser: http://localhost:8000/docs
```

## Standard Commands

### Docker Commands
```bash
make setup    # Build images
make start    # Start via docker-compose (requires APP_PORT)
make verify   # Validate compose config + health (if running)
make stop     # Stop services
make package  # Produce local image tar + manifest in dist/
make clean    # Remove containers/images/volumes and dist/
```

### Python Commands

#### Ingestion
```bash
# Ingest PDF document
python -m app.ingestion.cli --source data/pdf/document.pdf

# Batch ingest directory
python -m app.ingestion.cli --source data/pdf/ --batch

# View statistics
python -m app.ingestion.cli --stats
```

#### Query/Retrieval (Task 2.1)
```bash
# Search documents
python -m app.query.cli search "employee benefits" --top-k 5

# Search with filters
python -m app.query.cli search "policy" --document handbook.pdf

# Get specific chunk
python -m app.query.cli chunk <chunk-id>

# Interactive search
python -m app.query.cli interactive

# Show statistics
python -m app.query.cli stats
```

#### RAG Question Answering (Task 2.2)
```bash
# Ask question (mock mode)
python -m app.rag.cli ask "What is the vacation policy?"

# Ask with real LLM (OpenAI)
python -m app.rag.cli ask "What are employee benefits?" --provider openai --model gpt-4

# Interactive Q&A
python -m app.rag.cli interactive --provider mock

# Batch questions
python -m app.rag.cli batch questions.txt --output answers.json

# Show configuration
python -m app.rag.cli info
```

#### Testing
```bash
# Run all tests
pytest

# Run specific test module
pytest tests/unit/test_rag.py -v

# Run integration tests
pytest tests/integration/test_api.py -v

# Run with coverage
pytest --cov=app tests/
```

### API Endpoints (Task 2.3)

Once the server is running at `http://localhost:8000`:

```bash
# Health check
curl http://localhost:8000/health

# Ask a question (RAG)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the vacation policy?", "provider": "mock"}'

# Search documents (retrieval only)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "vacation", "top_k": 5}'

# List documents
curl http://localhost:8000/documents

# Ingest document
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data/pdf/handbook.pdf", "batch": false}'

# API documentation
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## Testing

### Run All Tests

```bash
# Full test suite (unit, integration, performance, accuracy, load)
python run_all_tests.py

# Quick tests only (skip slow tests)
python run_all_tests.py --quick

# Save reports
python run_all_tests.py --save-report --save-json
```

### Run Specific Test Suites

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Performance benchmarks
pytest tests/performance/ -v -s

# Accuracy evaluation
pytest tests/evaluation/test_accuracy.py -v -s

# Retrieval metrics
pytest tests/evaluation/test_retrieval.py -v -s

# Load tests
pytest tests/load/ -v -s
```

### Memory Profiling

```python
from app.utils.profiler import MemoryProfiler

profiler = MemoryProfiler()
profiler.take_snapshot()
# ... do work ...
profiler.take_snapshot()
profiler.print_summary()
```

### Caching

```python
from app.cache.manager import init_caches, get_query_cache

# Initialize caches
init_caches(query_cache_size=100, query_cache_ttl=3600)

# Use in code
cache = get_query_cache()
cached = cache.get_query(question, provider, model, top_k)
```

## Dev Container

Open in VS Code and select "Reopen in Container". The devcontainer uses `docker-compose.yml` service `app` for a standardized environment.

## Citation Enforcement

- POST /ask expects `citations: [{ doc, section }]`. If absent, the API rejects with a friendly error.
- GET /demo returns a canned response with a sample citation from `app/data/seed/sample-policies.md`.

## Configuration

- Ports are environment-configured only. Set `APP_PORT` and `N8N_PORT` prior to start.
- Internal service port is `INTERNAL_PORT=8000` in compose and can be overridden.
- N8N base path is configurable via `N8N_BASE_PATH` (default `/n8n`).

## Packaging (Offline)

```bash
make package
```

Outputs:

- `dist/hive-assistant-<version>.tar`
- `dist/hive-assistant-<version>-manifest.json` (with sha256)

## Log Correlation
- Each request carries a `request_id` generated by the backend.
- N8N nodes pass through `request_id` in HTTP responses; UI HTML includes it.
- Correlate logs by searching for the same `request_id` across backend and N8N logs.
- Backend logs are structured JSON lines including `method`, `path`, `session_id`, and `request_id`.

## Notes
- N8N workflow UI is available at http://localhost:${N8N_PORT}/n8n. Import the workflow from specs/001-n8n-chat-workflow/workflow.json.

- Sample policies are generic and provided strictly for demo purposes; replace with your own documents for real usage.
