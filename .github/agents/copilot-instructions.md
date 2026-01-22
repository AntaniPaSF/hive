# hive Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-21

## Active Technologies
- Python 3.11+ (application code), YAML (GitHub Actions workflows) + GitHub Actions, Docker, GitHub Container Registry (ghcr.io), pytest, black, ruff, mypy, bandit, pip-audit, Trivy (066-cicd-pipeline)
- GitHub Container Registry (images), GitHub Actions logs (build artifacts) (066-cicd-pipeline)

- Python 3.11+ (aligns with existing `app/server.py` Python stack) + PyYAML (YAML parsing), python-Levenshtein (fuzzy matching), requests (HTTP client); no external AI/ML libraries (001-llm-benchmark-suite)
- N8N (node-based workflow runtime), Backend: Python 3.11 stdlib HTTP server + Docker Compose, N8N (no paid APIs), Python stdlib (no external packages) (001-n8n-chat-workflow)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

- Python 3.11+ (aligns with existing `app/server.py` Python stack): Follow standard conventions
- N8N (node-based workflow runtime), Backend: Python 3.11 stdlib HTTP server: Follow standard conventions

## Recent Changes
- 066-cicd-pipeline: Added Python 3.11+ (application code), YAML (GitHub Actions workflows) + GitHub Actions, Docker, GitHub Container Registry (ghcr.io), pytest, black, ruff, mypy, bandit, pip-audit, Trivy

- 001-llm-benchmark-suite: Added Python 3.11+ (aligns with existing `app/server.py` Python stack) + PyYAML (YAML parsing), python-Levenshtein (fuzzy matching), requests (HTTP client); no external AI/ML libraries
- 001-n8n-chat-workflow: Added N8N (node-based workflow runtime), Backend: Python 3.11 stdlib HTTP server + Docker Compose, N8N (no paid APIs), Python stdlib (no external packages)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
