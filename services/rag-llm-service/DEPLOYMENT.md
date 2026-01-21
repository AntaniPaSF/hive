# RAG LLM Service - Deployment Guide

## Overview

This guide covers deploying the RAG LLM Service in different environments, from local development to production.

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- 4GB+ RAM
- HR Data Pipeline running (ChromaDB + Embedding API)

### Steps

1. **Clone repository**:
   ```bash
   cd services/rag-llm-service
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Download Ollama model** (first time only):
   ```bash
   ./scripts/download-ollama-model.sh
   # Or manually:
   docker exec ollama-service ollama pull mistral:7b
   ```

5. **Verify deployment**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Deployment Methods

### Method 1: Docker Compose (Recommended)

**Advantages**:
- Easy setup and teardown
- Automatic service orchestration
- Volume persistence for models
- Health checks and auto-restart

**Configuration** (`docker-compose.yml`):
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 30s
    networks:
      - rag-network

  rag-service:
    build: .
    ports:
      - "${RAG_SERVICE_PORT:-8000}:8000"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - VECTOR_STORE_URL=${VECTOR_STORE_URL}
      - EMBEDDING_API_URL=${EMBEDDING_API_URL}
    depends_on:
      ollama:
        condition: service_healthy
    networks:
      - rag-network
```

**Commands**:
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f rag-service

# Restart service
docker-compose restart rag-service

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

### Method 2: Standalone Docker Container

**Use case**: Integration with existing Docker infrastructure

**Build image**:
```bash
docker build -t rag-llm-service:latest .
```

**Run container**:
```bash
docker run -d \
  --name rag-service \
  -p 8000:8000 \
  -e OLLAMA_HOST=http://ollama:11434 \
  -e VECTOR_STORE_URL=http://chromadb:8001 \
  -e EMBEDDING_API_URL=http://hr-pipeline:8002/embed \
  -e MIN_CONFIDENCE_THRESHOLD=0.5 \
  -e LOG_LEVEL=INFO \
  --network rag-network \
  rag-llm-service:latest
```

**Stop container**:
```bash
docker stop rag-service
docker rm rag-service
```

---

### Method 3: Local Python (Development)

**Use case**: Active development, debugging, testing

**Setup**:
```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Ollama separately (Docker or native)
docker run -d -p 11434:11434 ollama/ollama:latest
docker exec ollama-service ollama pull mistral:7b

# Start service
uvicorn src.server:app --reload --port 8000
```

**Advantages**:
- Fast iteration (hot reload)
- Easy debugging
- Direct code access

**Disadvantages**:
- Manual dependency management
- No automatic restarts

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama API URL | `http://localhost:11434` |
| `VECTOR_STORE_URL` | ChromaDB URL | `http://localhost:8001` |
| `EMBEDDING_API_URL` | Embedding API endpoint | `http://localhost:8002/embed` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_SERVICE_PORT` | `8000` | API server port |
| `MIN_CONFIDENCE_THRESHOLD` | `0.5` | Answer confidence threshold |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `OLLAMA_MODEL` | `mistral:7b` | LLM model name |

### Setting Variables

**Docker Compose** (.env file):
```env
OLLAMA_HOST=http://ollama:11434
VECTOR_STORE_URL=http://chromadb:8001
EMBEDDING_API_URL=http://hr-pipeline:8002/embed
MIN_CONFIDENCE_THRESHOLD=0.5
```

**Docker Run** (command line):
```bash
docker run -e OLLAMA_HOST=http://ollama:11434 ...
```

**Python** (.env file or export):
```bash
export OLLAMA_HOST=http://localhost:11434
python -m uvicorn src.server:app
```

---

## Health Checks

### Endpoint: GET /health

**Healthy Response** (200 OK):
```json
{
  "status": "healthy",
  "ollama": "connected",
  "vector_store": "connected",
  "embedding_api": "connected",
  "timestamp": "2026-01-21T10:30:00Z"
}
```

**Degraded Response** (503 Service Unavailable):
```json
{
  "status": "degraded",
  "ollama": "disconnected",
  "vector_store": "connected",
  "embedding_api": "connected",
  "timestamp": "2026-01-21T10:30:00Z"
}
```

### Monitoring Health

**Script**:
```bash
#!/bin/bash
while true; do
  STATUS=$(curl -s http://localhost:8000/health | jq -r '.status')
  if [ "$STATUS" != "healthy" ]; then
    echo "Service degraded! Status: $STATUS"
    # Send alert
  fi
  sleep 30
done
```

**Docker Compose Health Check**:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=5)"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

---

## Production Considerations

### 1. Resource Allocation

**Minimum Requirements**:
- CPU: 2 cores
- RAM: 4GB
- Disk: 10GB (for models and logs)

**Recommended for Production**:
- CPU: 4 cores
- RAM: 8GB
- Disk: 20GB

**Docker Resource Limits**:
```yaml
services:
  rag-service:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

---

### 2. Scaling Strategy

**Horizontal Scaling**:
```bash
# Run multiple instances behind load balancer
docker-compose up --scale rag-service=3 -d
```

**Load Balancer Configuration** (nginx):
```nginx
upstream rag_backend {
    least_conn;
    server rag-service-1:8000;
    server rag-service-2:8000;
    server rag-service-3:8000;
}

server {
    listen 80;
    
    location /rag/ {
        proxy_pass http://rag_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Request-ID $request_id;
        proxy_timeout 30s;
    }
}
```

---

### 3. Security Hardening

**Use Non-Root User** (already configured in Dockerfile):
```dockerfile
USER raguser
```

**API Authentication** (add JWT middleware):
```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/query")
async def query(request: QueryRequest, token: str = Depends(security)):
    # Validate token
    pass
```

**Rate Limiting** (nginx):
```nginx
limit_req_zone $binary_remote_addr zone=rag_limit:10m rate=10r/s;

location /query {
    limit_req zone=rag_limit burst=20;
    proxy_pass http://rag-service:8000;
}
```

**HTTPS/TLS** (reverse proxy):
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    
    location / {
        proxy_pass http://rag-service:8000;
    }
}
```

---

### 4. Logging & Monitoring

**Centralized Logging** (Docker):
```yaml
services:
  rag-service:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Prometheus Metrics** (add /metrics endpoint):
```python
from prometheus_client import Counter, Histogram

query_counter = Counter('rag_queries_total', 'Total queries')
latency_histogram = Histogram('rag_query_latency_seconds', 'Query latency')

@app.post("/query")
async def query(...):
    query_counter.inc()
    with latency_histogram.time():
        result = await rag_service.query(...)
    return result
```

---

### 5. Backup & Recovery

**Model Backup**:
```bash
# Backup Ollama models
docker run --rm -v ollama-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/ollama-models.tar.gz /data
```

**Restore Models**:
```bash
docker run --rm -v ollama-data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/ollama-models.tar.gz -C /
```

---

## Troubleshooting

### Service Won't Start

**Check logs**:
```bash
docker-compose logs rag-service
```

**Common issues**:
- Port already in use: Change `RAG_SERVICE_PORT` in .env
- Ollama not ready: Wait for health check, verify `docker-compose ps`
- Missing environment variables: Check .env file exists and is loaded

---

### Health Check Failures

**Ollama disconnected**:
```bash
# Check Ollama service
docker exec ollama-service ollama list

# Verify network connectivity
docker exec rag-service ping ollama -c 3

# Check model is downloaded
docker exec ollama-service ollama pull mistral:7b
```

**Vector store disconnected**:
```bash
# Verify HR Pipeline is running
curl http://localhost:8001/api/v1/heartbeat

# Check network connectivity
docker exec rag-service curl http://chromadb:8001/api/v1/heartbeat
```

---

### High Latency

**Identify bottleneck**:
- Check `processing_time_ms` in responses
- Enable DEBUG logging: `LOG_LEVEL=DEBUG`
- Monitor component latencies in logs

**Optimization**:
- Reduce `max_results` in filters (less chunks = faster)
- Use GPU for Ollama (much faster generation)
- Increase timeout limits if needed

---

### Out of Memory

**Symptoms**:
- Container exits with code 137
- Docker logs show "Killed"

**Solutions**:
```yaml
# Increase memory limit
deploy:
  resources:
    limits:
      memory: 8G
```

Or use smaller model:
```env
OLLAMA_MODEL=phi:latest  # 2GB instead of 4GB
```

---

## Updating the Service

### Rolling Update (Docker Compose)

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose build rag-service

# Restart with new image (zero downtime with multiple instances)
docker-compose up -d --no-deps rag-service
```

### Blue-Green Deployment

```bash
# Deploy new version (green)
docker-compose -f docker-compose.yml -f docker-compose.green.yml up -d

# Test new version
curl http://localhost:8001/health

# Switch traffic (update load balancer)
# If successful, stop old version (blue)
docker-compose down
```

---

## Maintenance Tasks

### Model Updates

```bash
# Download new model version
docker exec ollama-service ollama pull mistral:latest

# Update .env
OLLAMA_MODEL=mistral:latest

# Restart service
docker-compose restart rag-service
```

### Log Rotation

```bash
# Manual rotation
docker-compose logs rag-service > rag-service-$(date +%Y%m%d).log

# Or configure Docker logging driver
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Cleanup

```bash
# Remove old containers
docker-compose down --remove-orphans

# Remove unused images
docker image prune -a

# Remove unused volumes (WARNING: deletes models)
docker volume prune
```

---

## Performance Benchmarking

### Load Testing

```bash
# Using Apache Bench
ab -n 100 -c 10 -p query.json -T application/json \
  http://localhost:8000/query

# Using wrk
wrk -t 4 -c 100 -d 30s \
  -s post.lua \
  http://localhost:8000/query
```

### Expected Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| p50 latency | < 3s | Median response time |
| p95 latency | < 5s | 95th percentile |
| p99 latency | < 10s | 99th percentile |
| Throughput | 15-20 req/min | Single instance |
| Error rate | < 1% | Excludes "I don't know" |

---

## Support & Contacts

- **Documentation**: README.md, API.md, ARCHITECTURE.md
- **Issues**: GitHub repository issues
- **Team**: team@hive.local
- **On-call**: ops@hive.local
