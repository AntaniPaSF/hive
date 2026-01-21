# Feature Specification: N8N Chat Workflow (HR Policy RAG)

**Feature Branch**: `001-n8n-chat-workflow`  
**Created**: 2026-01-21  
**Status**: Draft  
**Input**: User description: "Provide an N8N-based UI/workflow that allows a user to chat with the HR Policy RAG chatbot. N8N must send user messages to the backend and render the assistant response + citations."

## Clarifications

- Q1 Trigger: Webhook (N8N receives chat submissions via Webhook node)
- Q2 N8N Port/Path: `N8N_PORT` set via env; `N8N_BASE_PATH=/n8n`
- Q3 Error Display: Inline banner in the workflow's UI path
- Q4 Backend URL Resolution: Use Docker internal service DNS (e.g., `http://app:${INTERNAL_PORT}`) within Compose; avoid localhost coupling.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
  
  CONSTITUTION ALIGNMENT:
  Prioritize stories that directly impact core principles:
  - P1: Features affecting accuracy/transparency (RAG retrieval, citations)
  - P2: Features affecting reproducibility/self-containment (setup, dependencies)
  - P3: Nice-to-have features that don't impact core principles
-->

### User Story 1 - N8N Chat UI sends messages to backend (Priority: P1)

As a user, I can interact with a simple N8N-based chat UI that sends my message to the backend `/api/chat` and displays the assistant response along with citations (document name + section reference).

**Why this priority**: Directly supports Accuracy and Transparency by enforcing cited answers and provides a self-contained, reproducible UI path for demos.

**Independent Test**: Start services locally, trigger the N8N chat workflow with a message, verify the rendered response includes citations; if citations are absent, the workflow shows a friendly error.

**Acceptance Scenarios**:

1. Given N8N and backend are running, When I submit a chat message, Then the workflow calls `/api/chat` and renders `answer` + `citations[]`.
2. Given a query without available sources, When I submit a chat message, Then the workflow displays a clear message that citations are required and no answer is shown.
3. Given a rendered response with citations, When I click a citation link, Then the source document opens and the section reference is visible via the URL anchor.

---

### User Story 2 - Session continuity via `session_id` (Priority: P2)

As a user, my ongoing chat uses a `session_id` so the assistant can maintain conversation context across multiple turns (ephemeral, TTL-based).

**Why this priority**: Improves usability while remaining self-contained and reproducible.

**Independent Test**: Provide a `session_id` in two consecutive messages and observe contextual responses; repeat with a different `session_id` to confirm isolation.

**Acceptance Scenarios**:

1. Given a `session_id`, When I send multiple messages, Then the backend maintains context for that session.
2. Given a different `session_id`, When I send messages, Then responses do not leak context from other sessions.

---

### User Story 3 - One-command local orchestration (Priority: P2)

As a contributor, I can start N8N + backend + RAG stub with one command and verify health and demo the chat UI offline on localhost.

**Why this priority**: Aligns with Self-Contained and Reproducible principles.

**Independent Test**: Run the single startup command and confirm health endpoints are available and the N8N chat UI path works end-to-end.

**Acceptance Scenarios**:

1. Given a clean environment, When I run the startup command, Then all services are reachable on localhost and `/health` endpoints report OK.
2. Given no internet, When I run the packaged artifacts, Then the workflow and backend still function offline.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- Backend unavailable or returns error: N8N displays a clear actionable message, logs structured error details, and retries are documented.
- Missing citations: Workflow path rejects answer display and shows a citation-required message.
- Long messages: Document sensible limits and behavior (truncate or reject with guidance).
- Port conflicts: All services allow env-only port overrides without code changes.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: Provide an N8N workflow that accepts user input and calls the backend `/api/chat`, rendering `answer` + `citations` in a simple UI path.
- **FR-002**: Enforce citation requirement in the workflow by displaying a friendly error when responses lack citations.
- **FR-003**: Include `session_id` with each request; session continuity behavior is documented.
- **FR-004**: Compose includes N8N by default with env-only ports and localhost binding; packaging supports offline use.
- **FR-005**: Logs across N8N workflow and backend are structured JSON with timestamps and request IDs.
- **FR-006**: Health endpoints are available and documented for N8N, backend, and RAG stub.
- **FR-007**: Provide a version-controlled N8N workflow export (JSON) and quickstart steps to import/run.
- **FR-008**: Workflow UI path must be minimal, self-contained, and reproducible; no external paid services.

- **FR-009**: Use an N8N Webhook trigger as the chat entrypoint; document the webhook URL under `N8N_BASE_PATH` and forward requests to `/api/chat`.
- **FR-010**: Configure N8N via env with `N8N_PORT` and `N8N_BASE_PATH=/n8n`; no hardcoded defaults in code.
- **FR-011**: Display errors as an inline banner within the workflow UI path and include the `request_id` when available.

- **FR-012**: N8N MUST call the backend via internal service DNS (e.g., `app:${INTERNAL_PORT}`) inside the Compose network; no reliance on host-localhost ports for intra-service calls.
 - **FR-013**: Citations must render as clickable links that navigate to the original source document and section anchor.

### Key Entities *(include if feature involves data)*

- **ChatMessage**: `{ session_id, prompt }` sent from N8N to backend.
- **ChatResult**: `{ answer, citations[] }` rendered by N8N to the user.
- **Citation**: `{ doc, section }` with navigable references.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: A user can submit a chat message and see a cited response in under 10 seconds on CPU-only hardware (p95).
- **SC-002**: 100% of displayed responses include at least one source reference; otherwise the workflow displays a citation-required message.
- **SC-003**: One-command startup brings up N8N + backend + RAG stub in under 5 minutes on a clean machine.
- **SC-004**: Packaging enables offline startup of N8N + backend + RAG stub.
