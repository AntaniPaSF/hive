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

# Optional: Measure /api/chat latency (p50/p95)
if [[ "${MEASURE_LATENCY:-}" == "1" ]]; then
  if [[ -z "${APP_PORT:-}" ]]; then
    echo "[measure] APP_PORT not set; skipping latency measurement."
    exit 0
  fi
  COUNT=${COUNT:-20}
  TMPFILE=$(mktemp)
  echo "[measure] Measuring latency over ${COUNT} requests to /api/chat..."
  for i in $(seq 1 "$COUNT"); do
    curl -s -o /dev/null -w "%{time_total}\n" \
      -H 'Content-Type: application/json' \
      -d '{"session_id":"measure-1","prompt":"Benchmark ping"}' \
      -X POST "http://localhost:${APP_PORT}/api/chat" >> "$TMPFILE" || true
  done
  N=$(wc -l < "$TMPFILE")
  if [[ "$N" -eq 0 ]]; then
    echo "[measure] No samples collected."
    rm -f "$TMPFILE"
    exit 0
  fi
  P50_INDEX=$(awk -v n="$N" 'BEGIN{print int(n*0.5 + 0.5)}')
  P95_INDEX=$(awk -v n="$N" 'BEGIN{print int(n*0.95 + 0.5)}')
  P50=$(sort -n "$TMPFILE" | awk -v idx="$P50_INDEX" 'NR==idx{print $1}')
  P95=$(sort -n "$TMPFILE" | awk -v idx="$P95_INDEX" 'NR==idx{print $1}')
  echo "[measure] Samples: $N"
  echo "[measure] p50: ${P50}s"
  echo "[measure] p95: ${P95}s (target < 10s)"
  rm -f "$TMPFILE"
fi
