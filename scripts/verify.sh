#!/usr/bin/env bash
set -euo pipefail

# Verify compose config and health endpoint if running

echo "[verify] Checking docker compose config (base)..."
docker compose -f docker-compose.yml config >/dev/null

echo "[verify] Checking runtime health (if started)..."
if [[ -n "${APP_PORT:-}" ]]; then
  if curl -fsS "http://localhost:${APP_PORT}/health" >/dev/null; then
    echo "[verify] App healthy at :${APP_PORT}"
  else
    echo "[verify] App not responding at :${APP_PORT} (this is okay if not started)."
  fi
else
  echo "[verify] APP_PORT not set; skipping health check."
fi

echo "[verify] Done."
