# Hive – Corporate Digital Assistant (Local MVP Skeleton)

This repository provides a self-contained, CPU-only local MVP skeleton for the Corporate Digital Assistant, aligned with the Constitution:

- Accuracy Over Speed (citation enforcement at response layer)
- Transparency (answers include source references)
- Self-Contained (no paid/cloud APIs post-clone)
- Reproducible (single-command startup; pinned dependencies)

## Quickstart (Local)

1. Export port (no hardcoded defaults):

```bash
export APP_PORT=8080
```

2. Build and start:

```bash
make setup  # base compose only; no port needed
make start  # uses runtime compose; requires APP_PORT
```

3. Open UI:

- http://localhost:${APP_PORT}
- Health: http://localhost:${APP_PORT}/health

## Standard Commands

```bash
make setup    # Build images
make start    # Start via docker-compose (requires APP_PORT)
make verify   # Validate compose config + health (if running)
make stop     # Stop services
make package  # Produce local image tar + manifest in dist/
make clean    # Remove containers/images/volumes and dist/
```

## Dev Container

Open in VS Code and select "Reopen in Container". The devcontainer uses `docker-compose.yml` service `app` for a standardized environment.

## Citation Enforcement

- POST /ask expects `citations: [{ doc, section }]`. If absent, the API rejects with a friendly error.
- GET /demo returns a canned response with a sample citation from `app/data/seed/sample-policies.md`.

## Configuration

- Ports are environment-configured only. Set `APP_PORT` prior to start.
- Internal service port is `INTERNAL_PORT=8000` in scripts/compose and can be overridden.

## Packaging (Offline)

```bash
make package
```

Outputs:

- `dist/hive-assistant-<version>.tar`
- `dist/hive-assistant-<version>-manifest.json` (with sha256)

## Notes

- Sample policies are generic and provided strictly for demo purposes; replace with your own documents for real usage.
