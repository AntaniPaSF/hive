# Research: N8N Chat Workflow (HR Policy RAG)

## Decision: Webhook Trigger and Internal DNS
- Rationale: Webhook provides a simple, reproducible entrypoint from UI to workflow; Docker internal DNS (`backend:<port>`) avoids host-local coupling.
- Alternatives considered: Host `localhost:<mapped-port>` (breaks in multi-container networks), manual port wiring in nodes (less portable).

## Decision: Citation Enforcement at UI Path
- Rationale: Constitution mandates transparency; UI should block responses without citations and surface a friendly message.
- Alternatives: Silent logs only (users miss policy compliance), partial display then warn (ambiguous UX).

## Decision: `session_id` Continuity (TTL, ephemeral)
- Rationale: Improves usability with minimal complexity; can be in-memory for MVP.
- Alternatives: No session (worse UX), durable DB (not needed for MVP; adds complexity).

## Decision: Env Config (`N8N_PORT`, `N8N_BASE_PATH=/n8n`)
- Rationale: Avoid hardcoded ports/paths; complies with self-contained & reproducible principles.
- Alternatives: Fixed defaults (port conflicts, harder ops).

## Decision: Logging (structured JSON with request_id)
- Rationale: Traceability across workflow and backend; simplifies debugging.
- Alternatives: Unstructured logs (hard to correlate), per-node custom formats (inconsistent).

## Decision: Health Endpoints
- Rationale: Compose health checks and local verification; backend `/health`, N8N default health via container status.
- Alternatives: Ad-hoc checks (non-standard), none (poor operability).

## Decision: Contract Format (OpenAPI)
- Rationale: Clear backend API schema; supports testing and future automation.
- Alternatives: Ad-hoc schema (less tooling), GraphQL (overkill for single endpoint).

## Decision: Offline Packaging
- Rationale: Constitution III requires self-contained offline artifacts.
- Alternatives: Online pulls at runtime (not allowed).

## Unknowns Resolved
- Backend URL resolution within workflow: Use `http://backend:${INTERNAL_PORT}`.
- Error display location: Inline banner in workflow UI path.
- Workflow export: Provide version-controlled JSON and import instructions.

## Remaining Considerations
- Redis session store optional later; MVP uses in-memory.
- RAG stub remains minimal; ensure citation fields always present when answering.
