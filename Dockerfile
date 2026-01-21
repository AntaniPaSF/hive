# Self-contained CPU-only container for local MVP
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

# No external dependencies; use stdlib-only server
COPY app /workspace/app

# Expose internal app port (host mapping handled by compose via env)
EXPOSE 8000

CMD ["python", "-u", "app/server.py", "0.0.0.0", "8000"]
