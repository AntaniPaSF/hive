#!/usr/bin/env bash
set -euo pipefail

# Idempotent setup: build docker image via compose (no runtime start)
# Requires APP_PORT to be set by the environment; we do not enforce here for build-only.

echo "[setup] Building images (base compose only)..."
docker compose -f docker-compose.yml build --no-cache

echo "[setup] Done."
