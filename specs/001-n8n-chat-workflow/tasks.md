# Tasks: N8N Chat Workflow (HR Policy RAG)

Feature: N8N Chat Workflow (HR Policy RAG)
Branch: 001-n8n-chat-workflow
Spec: specs/001-n8n-chat-workflow/spec.md
Plan: specs/001-n8n-chat-workflow/plan.md

> Canonical workflow export: `specs/001-n8n-chat-workflow/workflow.fixed.json` is the source of truth for imports.

## Phase 1: Setup (Project Initialization)

 [x] T001 Create N8N workflow export file scaffold at specs/001-n8n-chat-workflow/workflow.fixed.json
 [x] T002 Define environment placeholders in README for N8N_PORT and N8N_BASE_PATH at README.md
 [x] T003 Add N8N service to compose with env-only ports at docker-compose.yml
 [x] T004 Add runtime ports overlay for N8N at docker-compose.runtime.yml
 [x] T005 Document single-command startup in quickstart at specs/001-n8n-chat-workflow/quickstart.md

## Phase 2: Foundational (Blocking Prerequisites)

 [x] T006 [P] Add OpenAPI contract for /api/chat at specs/001-n8n-chat-workflow/contracts/openapi.yaml
 [x] T007 Ensure backend exposes /api/chat and /health at app/server.py
 [x] T008 Add structured JSON logging with request_id propagation at app/server.py
 [x] T009 Compose healthcheck for backend and N8N at docker-compose.yml

## Phase 3: User Story 1 (P1) — N8N Chat UI sends messages to backend

Goal: User can submit a message via N8N UI, backend returns cited answer; UI enforces citations.
Independent Test: Trigger workflow; response renders answer + citations; errors show inline banner.

- [x] T010 [US1] Create N8N Webhook Trigger node under base path at specs/001-n8n-chat-workflow/workflow.fixed.json
- [x] T011 [P] [US1] Configure HTTP Request node to call backend via internal DNS at specs/001-n8n-chat-workflow/workflow.fixed.json
- [x] T012 [US1] Map request/response schema to OpenAPI fields at specs/001-n8n-chat-workflow/workflow.fixed.json
- [x] T013 [US1] Implement UI path to render answer + citations at specs/001-n8n-chat-workflow/workflow.fixed.json
- [x] T014 [US1] Add citation enforcement: show banner if citations missing at specs/001-n8n-chat-workflow/workflow.fixed.json
- [x] T015 [P] [US1] Propagate request_id across nodes and logs at specs/001-n8n-chat-workflow/workflow.fixed.json
 - [x] T042 [US1] Set HTTP Request timeout=5000ms and retries=5 in specs/001-n8n-chat-workflow/workflow.fixed.json
- [x] T016 [US1] Document webhook URL and UI path in quickstart at specs/001-n8n-chat-workflow/quickstart.md
- [x] T017 [US1] Validate acceptance scenarios via curl examples at specs/001-n8n-chat-workflow/quickstart.md

## Phase 4: User Story 2 (P2) — Session continuity via session_id

Goal: Maintain per-session context across turns using session_id.
Independent Test: Two consecutive messages with same session_id show context; different session_id isolated.

- [x] T018 [US2] Include session_id in Webhook→HTTP Request payload at specs/001-n8n-chat-workflow/workflow.json
- [x] T019 [US2] Update backend to accept session_id and maintain ephemeral context at app/server.py
- [x] T020 [P] [US2] Add minimal in-memory session store with TTL at app/server.py
- [x] T021 [US2] Document session behavior and constraints at specs/001-n8n-chat-workflow/quickstart.md
- [x] T022 [US2] Add structured logs including session_id at app/server.py
- [x] T023 [US2] Provide test examples for continuity and isolation at specs/001-n8n-chat-workflow/quickstart.md

## Phase 5: User Story 3 (P2) — One-command local orchestration

Goal: Start N8N + backend + RAG stub with one command; offline demo on localhost.
Independent Test: Single command brings services up; health OK; UI path works offline.

- [x] T024 [US3] Ensure compose includes N8N + backend by default at docker-compose.yml
- [x] T025 [US3] Add env-only port mappings for localhost demo at docker-compose.runtime.yml
- [x] T026 [P] [US3] Add startup script shortcut in Makefile at Makefile
- [x] T027 [US3] Add verify script and health checks at scripts/verify.sh
- [x] T028 [US3] Update packaging script for offline images at scripts/package.sh
- [x] T029 [US3] Document offline run using docker load at specs/001-n8n-chat-workflow/quickstart.md

## Final Phase: Polish & Cross-Cutting Concerns

 - [x] T030 Improve error messages and banner UX text at specs/001-n8n-chat-workflow/workflow.fixed.json
 - [ ] T036 Validate clickable citations (FR-013): Ensure N8N UI renders links to `/docs/<doc>#<section>` and backend serves docs anchors.
 - [ ] T037 Enforce performance gate: extend `scripts/verify.sh` to exit non-zero if p95 ≥ 10s; document in quickstart; gate merges.
 - [ ] T038 Define offline packaging artifacts: produce tarball + manifest.json with SHA256 checksums in `scripts/package.sh`; document verification steps.
 - [ ] T039 Test env-only N8N config: vary `N8N_PORT` and `N8N_BASE_PATH` and verify endpoints; add steps in quickstart.
 - [ ] T040 Verify self-contained constraints: add check in `scripts/verify.sh` to detect external paid API usage (OpenAI/Anthropic/Cohere) and fail.
 - [ ] T041 Resolve prerequisites prefix collision: enhance `.specify/scripts/bash/check-prerequisites.sh` to accept explicit feature selection or adjust docs.
 - [x] T031 Add log correlation guide in README at README.md
 - [x] T032 Add edge case docs (long messages, port conflicts) at specs/001-n8n-chat-workflow/quickstart.md
 - [x] T033 Add minimal RAG stub contract and sample data at specs/001-n8n-chat-workflow/contracts/openapi.yaml
 - [x] T034 Validate constitution gates and update plan checkboxes at specs/001-n8n-chat-workflow/plan.md
 - [x] T035 [P] Measure /api/chat latency (p50/p95) via scripts/verify.sh and document command in specs/001-n8n-chat-workflow/quickstart.md

## Dependencies

- Story order: US1 → US2; US3 depends on Foundational and US1 for UI demo path.
- Blocking prerequisites: Phase 1 and Phase 2 must be completed before US stories.

## Parallel Execution Examples

- [P] T006 (OpenAPI) can be done in parallel with T008 (logging).
- [P] T011 (HTTP Request config) can be done in parallel with T015 (request_id propagation).
- [P] T020 (session store) can be done in parallel with T022 (session_id logging).
- [P] T026 (Makefile startup) can be done in parallel with T028 (packaging script).

## Implementation Strategy

- MVP First: Deliver US1 (Webhook UI → backend → cited answer with enforcement).
- Incremental: Add US2 (session continuity) next; finalize US3 (one-command orchestration and offline packaging).
- Documentation-driven: Keep quickstart and contracts updated alongside implementation for testability.
