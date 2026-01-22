# Implementation Plan: N8N Chat Workflow (HR Policy RAG)

**Branch**: `001-n8n-chat-workflow` | **Date**: 2026-01-21 | **Spec**: specs/001-n8n-chat-workflow/spec.md
**Input**: Feature specification from `specs/001-n8n-chat-workflow/spec.md`

## Summary

Implement a self-contained N8N workflow (Webhook-triggered) that accepts user chat input, forwards it to the backend `/api/chat` over internal Docker service DNS, and renders the assistant response plus citations. Enforce citation presence at the workflow UI path, support `session_id` for context continuity, and provide one-command local orchestration and offline packaging.

## Technical Context

**Language/Version**: N8N (node-based workflow runtime), Backend: Python 3.11 stdlib HTTP server  
**Primary Dependencies**: Docker Compose, N8N (no paid APIs), Python stdlib (no external packages)  
**Storage**: N/A for workflow; backend may use ephemeral in-memory or Redis (future) for sessions  
**Testing**: curl-based webhook tests, backend contract tests (manual for MVP)  
**Target Platform**: Linux server (containers), localhost for demos  
**Project Type**: Web orchestration + backend API  
**Performance Goals**: p95 < 10s response time on CPU-only hardware  
**Constraints**: Offline-capable, self-contained, env-only ports, citation enforcement  
**Scale/Scope**: MVP scope (single workflow, single backend endpoint), extensible later

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Accuracy Over Speed**: Backend/UI enforce citation requirement; no answer without sources
- [x] **Transparency**: Responses include source citations (document + section)
- [x] **Self-Contained**: No external paid APIs; all local containers
- [x] **Reproducible**: Single-command startup targeted in quickstart; version-pinned containers
- [x] **Performance**: Architecture targets <10s p95 on CPU-only
- [x] **Citation Check**: 100% of displayed answers traceable to sources

## Final Validation

- [x] Error UX: Workflow displays a clear banner and guidance when citations are missing.
- [x] Log correlation: `request_id` visible in UI and backend for cross-system tracing.
- [x] Edge cases documented: Long messages, port conflicts, health check caveats.
- [x] Contract updated: `/ask` endpoint defined for citation enforcement stub.

## Project Structure

### Documentation (this feature)

```text
specs/001-n8n-chat-workflow/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)

```text
docker-compose.yml              # base compose (includes backend + n8n)
docker-compose.runtime.yml      # ports overlay (env-configurable)

app/
└── server.py                   # stdlib HTTP server exposing /api/chat

specs/
└── 001-n8n-chat-workflow/     # docs + contracts for this feature
```

**Structure Decision**: Use containerized backend (`app/server.py`) and N8N, orchestrated via compose; env-only ports; internal service DNS for inter-service calls.

## Complexity Tracking

No constitution violations requiring justification at this stage.
