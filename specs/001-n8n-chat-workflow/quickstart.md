# Quickstart: N8N Chat Workflow (HR Policy RAG)

## Prerequisites
- Docker + Docker Compose installed
- Environment configured (offline-capable)

## Environment
 Set `N8N_PORT` and `N8N_BASE_PATH=/n8n`
 Ensure backend internal port is exposed to compose network as `${INTERNAL_PORT}` (service name: `app`)

## Start (one command)
 Open N8N at `http://localhost:${N8N_PORT}/n8n`
 Import the version-controlled workflow JSON (committed under `specs/001-n8n-chat-workflow/workflow.fixed.json`)
 Confirm Webhook node path `chat` and that it forwards to `http://app:${INTERNAL_PORT}/api/chat`
docker compose -f docker-compose.yml -f docker-compose.runtime.yml up -d
```

 # Test webhook (requires clicking "Execute workflow" in the editor)
 curl -X POST \
   http://localhost:${N8N_PORT}/webhook-test/chat \
- Open N8N at `http://localhost:${N8N_PORT}/n8n`
- Import the version-controlled workflow JSON (committed under `specs/001-n8n-chat-workflow/` when available)
- Confirm Webhook URL path (under `/n8n`) and that it forwards to `http://backend:${INTERNAL_PORT}/api/chat`

## Test

```bash
# Send a message via webhook-test (replace HOST/PORT/PATH accordingly)
curl -X POST \
  http://localhost:${N8N_PORT}/webhook-test/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-1","prompt":"What is our vacation policy?"}'
```

Expected: Response shows `answer` and `citations[]`. If no citations are present, see an inline error banner in the UI path and a 400 error from the backend.

### Session Continuity

Send two messages with the same `session_id` to observe continuity and turns count:

```bash
curl -fsS -X POST \
  http://localhost:${APP_PORT}/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-1","prompt":"First question"}'

curl -fsS -X POST \
  http://localhost:${APP_PORT}/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-1","prompt":"Follow-up question"}'
```

Use a different `session_id` to confirm isolation:

```bash
curl -fsS -X POST \
  http://localhost:${APP_PORT}/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-2","prompt":"Unrelated session"}'
```

Sessions are ephemeral with a 10-minute TTL.

## Logs & Health
- Backend: `GET /health` on internal port
- Structured JSON logs include `request_id` for traceability

## Performance
- Measure chat API latency (p50/p95 target: p95 < 10s):

```bash
export APP_PORT=${APP_PORT:-8080}
MEASURE_LATENCY=1 COUNT=20 bash scripts/verify.sh
```

The script runs N requests to `/api/chat` and prints p50/p95.

## Packaging (offline)
- Use existing packaging scripts to build and save images as tar; run offline via `docker load`.

### Offline Run

Backend-only (no N8N):

```bash
make package
docker load -i dist/hive-assistant-0.1.0.tar
export APP_PORT=8080
docker compose -f docker-compose.yml -f docker-compose.runtime.yml up -d
```

Optional N8N: prepare a local `n8n` image tar and load it, then:

```bash
export COMPOSE_PROFILES=n8n
export N8N_PORT=5678
export N8N_BASE_PATH=/n8n
docker compose -f docker-compose.yml -f docker-compose.runtime.yml up -d
```

### Production Webhook
Activate the workflow (toggle in top-right of the editor), then call:

```bash
curl -X POST \
  http://localhost:${N8N_PORT}/webhook/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-1","prompt":"What is our vacation policy?"}'
```

## Edge Cases
- **Long messages**: Prompts longer than ~4k characters may be rejected or truncated; keep messages concise.
- **Port conflicts**: If `APP_PORT` or `N8N_PORT` are already in use, choose different ports before starting.
- **Missing or inactive workflow**: If `POST /webhook/chat` returns 404, import the workflow JSON and activate it; for testing without activation, use `/webhook-test/chat` after clicking "Execute workflow".
- **Unhealthy container status**: The app image may lack `curl`; health checks can show `unhealthy` while endpoints still work.
