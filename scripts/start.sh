#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${APP_PORT:-}" ]]; then
  echo "ERROR: APP_PORT must be set (e.g., export APP_PORT=8080)." >&2
  exit 1
fi

export INTERNAL_PORT=${INTERNAL_PORT:-8000}

echo "[start] Starting Hive Assistant on localhost:${APP_PORT}..."
docker compose -f docker-compose.yml -f docker-compose.runtime.yml up -d

echo "[start] Waiting for health..."
for i in {1..20}; do
  if curl -fsS "http://localhost:${APP_PORT}/health" >/dev/null; then
    echo "[start] Healthy at http://localhost:${APP_PORT}"
    exit 0
  fi
  sleep 1
done

echo "[start] Failed to reach healthy state." >&2
exit 1
