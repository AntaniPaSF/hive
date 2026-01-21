# RAG LLM Service

**Intelligent Knowledge Retrieval Service** - A Retrieval-Augmented Generation (RAG) pipeline using Ollama LLM for question answering over internal documentation.

## Overview

The RAG LLM Service provides the core reasoning engine for the Corporate Digital Assistant. It enables users to ask questions in natural language and receive synthesized answers grounded exclusively in internal documentation, with source citations.

**Key Features**:
- ✅ Semantic search over document knowledge base (ChromaDB)
- ✅ Answer generation using local Ollama LLM (Mistral 7B)
- ✅ Automatic citation extraction and validation
- ✅ "I don't know" responses for low-confidence queries
- ✅ Structured JSON logging for request tracing
- ✅ Self-contained, CPU-only deployment

## Architecture

```
Query → Embedding API → Vector Store (ChromaDB) → Retrieval
                                                        ↓
Answer ← Citation Extraction ← LLM Generation ← Context Assembly
```

**Components**:
1. **Embedding API Client**: Calls HR Data Pipeline for 384-dim query embeddings
2. **Retrieval Pipeline**: Queries ChromaDB for relevant document chunks
3. **Generation Pipeline**: Ollama LLM synthesizes answers from retrieved context
4. **Citation Extraction**: Regex-based parsing of `[document, section]` markers

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM (for Mistral 7B model)
- HR Data Pipeline running (for embeddings and vector store)

### Setup (< 15 minutes)

1. **Clone and navigate**:
   ```bash
   cd services/rag-llm-service
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings (OLLAMA_HOST, VECTOR_STORE_URL, EMBEDDING_API_URL)
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Download Ollama model** (first run only):
   ```bash
   docker exec ollama-service ollama pull mistral:7b
   ```

5. **Verify health**:
   ```bash
   curl http://localhost:8000/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "ollama": "connected",
     "vector_store": "connected",
     "embedding_api": "connected"
   }
   ```

## API Usage

### POST /query

Ask a question and receive an answer with citations.

**Request**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the vacation policy?",
    "filters": {
      "source": "employee_handbook.pdf",
      "max_results": 5
    }
  }'
```

**Response** (success):
```json
{
  "answer": "Employees are entitled to 15 days of paid vacation per year...",
  "citations": [
    {
      "document_name": "employee_handbook.pdf",
      "excerpt": "All full-time employees receive 15 days...",
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

**Response** ("I don't know"):
```json
{
  "answer": null,
  "citations": [],
  "confidence": 0.0,
  "message": "Information not found in the knowledge base.",
  "request_id": "req_20260121_xyz789",
  "processing_time_ms": 1250
}
```

### GET /health

Check service health status.

**Request**:
```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "ollama": "connected",
  "vector_store": "connected",
  "embedding_api": "connected",
  "timestamp": "2026-01-21T10:30:00Z"
}
```

## Configuration

All configuration is managed via environment variables (see `.env.example`).

### Critical Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `VECTOR_STORE_URL` | `http://localhost:8001` | ChromaDB vector store |
| `EMBEDDING_API_URL` | `http://localhost:8002/embed` | HR pipeline embedding API |
| `MIN_CONFIDENCE_THRESHOLD` | `0.5` | Min similarity for returning answers |
| `RAG_SERVICE_PORT` | `8000` | Service HTTP port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Docker Deployment

### Building the Docker Image

The service uses a multi-stage Dockerfile for optimized production builds:

```bash
# Build the image
docker build -t rag-llm-service:latest .

# Verify the image
docker images | grep rag-llm-service
```

**Image details**:
- **Base**: Python 3.12 slim (minimal footprint)
- **Size**: ~500MB (vs ~1GB for full Python image)
- **User**: Non-root `raguser` (UID 1000) for security
- **Layers**: Multi-stage build (builder + runtime)

### Running with Docker Compose

The recommended deployment method uses docker-compose to orchestrate both Ollama and the RAG service:

```bash
# Start all services (Ollama + RAG service)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f rag-service
docker-compose logs -f ollama

# Stop services
docker-compose down

# Stop and remove volumes (data cleanup)
docker-compose down -v
```

**Service ports**:
- RAG Service: `8000` (configurable via `RAG_SERVICE_PORT`)
- Ollama: `11434`

### Initial Model Setup

After first-time deployment, download the Mistral 7B model:

**Option 1: Automated script** (recommended):
```bash
./scripts/download-ollama-model.sh
```

**Option 2: Manual download**:
```bash
# Download Mistral 7B (~4GB)
docker exec ollama-service ollama pull mistral:7b

# Verify model is available
docker exec ollama-service ollama list
```

**Alternative models** (optional):
```bash
# Llama 2 7B
docker exec ollama-service ollama pull llama2:7b

# Phi (smaller, faster, less accurate)
docker exec ollama-service ollama pull phi:latest

# Update docker-compose.yml OLLAMA_MODEL env var to use different model
```

### Testing the Deployment

**1. Health check**:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "ollama": "connected",
  "vector_store": "connected",
  "embedding_api": "connected"
}
```

**2. Sample query**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the vacation policy?",
    "filters": {"max_results": 5}
  }'
```

**3. Verify logs**:
```bash
# Check for successful startup
docker-compose logs rag-service | grep "Application startup complete"

# Monitor request processing
docker-compose logs -f rag-service
```

### Docker Configuration Files

**Dockerfile**:
- Multi-stage build (builder + runtime)
- Non-root user execution
- Health check endpoint (`/health`)
- Volume mounts for source code (development) and logs

**docker-compose.yml**:
- Service orchestration (Ollama + RAG service)
- Network configuration (`rag-network`)
- Volume persistence (`ollama-data`)
- Environment variable injection
- Health checks and restart policies

**.dockerignore**:
- Excludes test files, docs, git history
- Reduces image size by ~50MB
- Speeds up build context transfer

### Production Deployment Considerations

**1. Resource allocation**:
```yaml
# Add to docker-compose.yml under rag-service:
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

**2. Secrets management**:
```bash
# Use docker secrets instead of .env file
echo "your-api-key" | docker secret create embedding_api_key -
```

**3. Logging driver**:
```yaml
# Add to docker-compose.yml under rag-service:
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**4. Reverse proxy** (nginx/traefik):
```nginx
# Example nginx config
location /rag/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Request-ID $request_id;
}
```

### Troubleshooting Docker Deployments

**Image won't build**:
```bash
# Check Docker daemon is running
docker info

# Check Dockerfile syntax
docker build --no-cache -t rag-llm-service:latest .

# Inspect build layers
docker history rag-llm-service:latest
```

**Container exits immediately**:
```bash
# Check logs
docker logs rag-llm-service

# Inspect exit code
docker inspect rag-llm-service --format='{{.State.ExitCode}}'

# Run interactively for debugging
docker run -it --entrypoint /bin/bash rag-llm-service:latest
```

**Health check failing**:
```bash
# Check health status
docker inspect rag-llm-service --format='{{.State.Health.Status}}'

# Test health endpoint manually
docker exec rag-llm-service curl http://localhost:8000/health

# Verify dependencies are accessible
docker exec rag-llm-service ping ollama -c 3
```

**Model download fails**:
```bash
# Check Ollama service is running
docker-compose ps ollama

# Verify Ollama API is accessible
curl http://localhost:11434/api/tags

# Download with verbose output
docker exec -it ollama-service ollama pull mistral:7b --verbose
```

## Development

### Local Setup (without Docker)

1. **Create virtual environment**:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Include dev dependencies
   ```

3. **Run service**:
   ```bash
   uvicorn src.server:app --reload --port 8000
   ```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Integration tests (requires Ollama + ChromaDB running)
pytest -m integration

# With coverage report
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Format
black src/
```

## Troubleshooting

### Common Issues

**1. Ollama model not found**
```
Error: model 'mistral:7b' not found
```
**Solution**: Download the model first:
```bash
docker exec ollama-service ollama pull mistral:7b
```

**2. ChromaDB connection timeout**
```
Error: Could not connect to vector store
```
**Solution**: Verify HR Data Pipeline is running and ChromaDB is accessible at `VECTOR_STORE_URL`.

**3. Embedding API unavailable**
```
Error: Embedding API returned 503
```
**Solution**: Check that HR Data Pipeline embedding service is running at `EMBEDDING_API_URL`.

**4. Low confidence answers**
```
Message: "Information not found in the knowledge base."
```
**Solution**: 
- Verify ChromaDB contains embeddings for your query topic
- Lower `MIN_CONFIDENCE_THRESHOLD` (not recommended for production)
- Refine query phrasing

### Debug Logging

Enable DEBUG logs for detailed pipeline tracing:
```bash
export LOG_LEVEL=DEBUG
docker-compose restart rag-service
```

Logs include:
- Request ID for each query
- Embedding generation time
- Retrieval similarity scores
- LLM generation latency
- Citation extraction results

## Performance

**Targets** (CPU-only hardware):
- **RAG service latency**: < 5 seconds (p95)
- **End-to-end latency**: < 10 seconds (p95, including FastAPI wrapper)

**Measured** (on reference hardware: 4-core CPU, 8GB RAM):
- Embedding API call: ~200ms
- Vector store query: ~300ms
- Ollama generation (Mistral 7B): ~2-4s
- Citation extraction: ~50ms

## Architecture Decisions

- **Stateless service**: All state in ChromaDB and Ollama
- **Citation enforcement**: Regex-based parsing; answers without citations rejected
- **Confidence threshold**: 0.5 initial heuristic; tuned in Phase 2.10 integration testing
- **Embedding delegation**: HR Data Pipeline owns all-MiniLM-L6-v2 model for consistency
- **Structured logging**: JSON format with request IDs for distributed tracing

## Dependencies

- **Python 3.12+**: Modern async support, type hints
- **FastAPI**: REST API framework with automatic OpenAPI docs
- **Ollama**: Self-hosted LLM (Mistral 7B)
- **LangChain**: LLM orchestration and prompt management
- **ChromaDB**: Vector store (managed by HR Data Pipeline)
- **Pydantic**: Data validation and settings management

## License

MIT

## Support

For issues or questions:
- File an issue in the project repository
- Contact: team@hive.local
- Documentation: [ARCHITECTURE.md](ARCHITECTURE.md), [API.md](API.md)
