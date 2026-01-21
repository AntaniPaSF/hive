# Dockerfile for RAG LLM Service
# Base: Python 3.12 slim image
# Target: Production-ready service with minimal footprint

FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 raguser && \
    chown -R raguser:raguser /app

# Copy and install dependencies
COPY requirements-prod.txt .
RUN --network=default pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY --chown=raguser:raguser src/ ./src/
COPY --chown=raguser:raguser pyproject.toml ./

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Switch to non-root user
USER raguser

# Expose service port (default: 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Run FastAPI server
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "/dev/null"]
