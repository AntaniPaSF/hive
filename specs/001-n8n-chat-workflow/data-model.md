# Data Model: N8N Chat Workflow

## Entities

- ChatMessage
  - Fields: `session_id: string`, `prompt: string`
  - Validation: `session_id` non-empty; `prompt` non-empty, length <= 4k

- Citation
  - Fields: `doc: string`, `section: string`
  - Validation: `doc` and `section` non-empty; section is navigable reference

- ChatResult
  - Fields: `answer: string`, `citations: Citation[]`, `request_id: string`
  - Validation: `citations.length >= 1` required to display `answer`

## Relationships
- A `ChatMessage` produces a single `ChatResult`.
- A `ChatResult` references one or more `Citation` entries.

## State & Transitions
- `pending` → `answered` (citations present) → `rendered`
- `pending` → `error` (backend error or missing citations) → `banner_shown`

## Constraints
- Self-contained: No external DB; session continuity ephemeral.
- Performance: p95 < 10s response time.
