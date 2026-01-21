# Implementation Tasks: Intelligent Knowledge Retrieval Service (RAG LLM Service)

**Feature**: `001-rag-pipeline-llm-service`  
**Phase**: 2 (Implementation)  
**Generated**: 2026-01-21  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Task Taxonomy

Tasks are organized by **implementation phase** and **user story**, enabling independent, parallelizable work. Each task has:
- **Checkbox**: `- [ ]` (markdown checklist format)
- **Task ID**: T001-T0XX (sequential, executable order)
- **[P] Marker**: Indicates parallelizable tasks (different files, no dependencies)
- **[Story] Label**: Maps to user stories (US1, US2, etc.) or phase (Setup, Foundational, Polish)
- **Description**: Clear action with file paths

---

## Phase 2: Implementation

### Phase 2.0: Project Initialization & Infrastructure

**Goal**: Set up project structure, Docker environment, and development dependencies.

- [X] T001 Create project directory structure per plan.md (`services/rag-llm-service/src/`, `services/rag-llm-service/tests/`, etc.)
- [X] T002 Create `services/rag-llm-service/requirements.txt` with pinned dependencies (Python 3.12+, pydantic, langchain, ollama, requests, pytest, python-json-logger)
- [X] T003 Create `services/rag-llm-service/pyproject.toml` with project metadata (name, version, description, entry points)
- [X] T004 Create `services/rag-llm-service/Dockerfile` with multi-stage build (base Python 3.12 image, install dependencies, run service)
- [X] T005 Create `services/rag-llm-service/docker-compose.yml` defining Ollama service (image: ollama/ollama, port 11434) and RAG service (build context, environment variables, volumes)
- [X] T006 Create `services/rag-llm-service/.env.example` with all environment variables (OLLAMA_HOST, VECTOR_STORE_URL, VECTOR_STORE_COLLECTION, EMBEDDING_MODEL, MIN_CONFIDENCE_THRESHOLD, LOG_LEVEL, RAG_SERVICE_PORT)
- [X] T007 Create `services/rag-llm-service/README.md` with setup instructions, API overview, environment configuration, and troubleshooting guide

**Deliverable**: Project structure ready for implementation; all build artifacts defined

---

### Phase 2.1: Core Data Schemas & Utilities

**Goal**: Implement foundational data models and utility functions required by all services.

- [X] T008 Implement `services/rag-llm-service/src/schemas/query.py` with Pydantic models: `Query` (question + optional filters), `Answer` (answer + citations + confidence + message), `Citation` (document_name + excerpt + page_number + section + chunk_id)
- [X] T009 Implement `services/rag-llm-service/src/schemas/citation.py` with citation rendering logic (format citations as `[source_doc, section_title]` or with page number)
- [X] T010 Implement `services/rag-llm-service/src/utils/logger.py` with structured JSON logging (timestamp, request_id, level, component, event, data, error)
- [X] T011 Implement `services/rag-llm-service/src/utils/errors.py` with custom exception classes (VectorStoreUnavailable, OllamaUnavailable, NoCitationsFound, InvalidQuery, GenerationTimeout)
- [X] T012 Implement `services/rag-llm-service/src/utils/validators.py` with input validation (question length 3-1000 chars, filter validation)
- [X] T013 Implement `services/rag-llm-service/src/config.py` reading environment variables (OLLAMA_HOST, VECTOR_STORE_URL, VECTOR_STORE_COLLECTION, EMBEDDING_MODEL, MIN_CONFIDENCE_THRESHOLD, LOG_LEVEL, RAG_SERVICE_PORT)

**Deliverable**: Core schemas, logging, and configuration ready for use by retrieval/generation pipelines

---

### Phase 2.2: Vector Store Integration (Retrieval Pipeline)

**Goal**: Implement ChromaDB querying and chunk retrieval with semantic search.

- [X] T014 Implement `services/rag-llm-service/src/core/retrieval.py` with `VectorStoreClient` class (connect to ChromaDB, query with 384-dim embeddings, handle timeouts, parse response)
- [X] T015 Implement `VectorStoreClient.query()` method (accepts embedding vector + filters, returns list of RetrievedChunk objects with similarity scores)
- [X] T016 Implement error handling in retrieval (catch connection errors, 404 not found, 500 server errors, return "I don't know" on ChromaDB unavailable)
- [X] T017 Implement confidence calculation (average similarity score from retrieved chunks; if <0.5, flag for low confidence)
- [X] T018 Implement metadata extraction from ChromaDB response (source_doc, source_type, page_number, section_title, chunk_index for citation building)
- [X] T019 [P] Implement `services/rag-llm-service/tests/unit/test_retrieval.py` unit tests (query with mock ChromaDB, verify chunk ordering by similarity, verify metadata parsing, test error handling)

**Deliverable**: Retrieval pipeline can query ChromaDB and extract relevant chunks with citations

---

### Phase 2.3: Embedding API Integration

**Goal**: Integrate with HR Data Pipeline embedding API for query embedding generation.

- [X] T020 Implement `services/rag-llm-service/src/core/embedding_client.py` with `EmbeddingAPIClient` class (call HR Data Pipeline embedding API endpoint, handle timeouts, validate 384-dim response)
- [X] T021 Implement `EmbeddingAPIClient.embed()` method (accepts query text, returns 384-dim vector from HR pipeline API)
- [X] T022 Implement embedding dimension validation (assert API returns exactly 384-dim; log error and fail query if mismatch)
- [X] T023 Implement error handling for embedding API (connection timeout, 404/500 errors, retry logic with exponential backoff)
- [X] T024 [P] Implement `services/rag-llm-service/tests/unit/test_embedding_client.py` unit tests (mock HR pipeline API, verify 384-dim output, test error handling, test retry logic)

**Deliverable**: Query embeddings retrieved from HR Data Pipeline API with proper error handling

---

### Phase 2.4: LLM Generation Pipeline

**Goal**: Implement Ollama integration for answer generation with citation extraction.

- [X] T025 Implement `services/rag-llm-service/src/core/ollama_client.py` with `OllamaClient` class (connect to Ollama API, generate answers, handle timeouts)
- [X] T026 Implement `OllamaClient.generate()` method (accepts prompt string, returns generated answer text)
- [X] T027 Implement prompt engineering in `services/rag-llm-service/src/prompts/qa_prompt.py` with system instructions (answer ONLY from context, cite sources using [document, section] format, respond "I don't know" if not found)
- [X] T028 Implement prompt context assembly (format retrieved chunks as context blocks with document + section headers)
- [X] T029 Implement `services/rag-llm-service/src/prompts/citation_parser.py` to extract citation markers from LLM output (regex: `\[([^\]]+),\s*([^\]]+)\]` for document and section)
- [X] T030 Implement error handling for Ollama (connection timeout, model not found, generation timeout, retry logic)
- [X] T031 [P] Implement `services/rag-llm-service/tests/unit/test_ollama_client.py` unit tests (mock Ollama API, test generation, test error handling)
- [X] T032 [P] Implement `services/rag-llm-service/tests/unit/test_citation_parser.py` unit tests (extract citations from various answer formats, handle missing citations)

**Deliverable**: LLM can generate answers and extract citations from generated text

---

### Phase 2.5: RAG Service Implementation (Core Logic)

**Goal**: Assemble retrieval, generation, and citation pipelines into cohesive RAG service.

- [X] T033 Implement `services/rag-llm-service/src/__init__.py` with main `RAGService` class (orchestrates embedding → retrieval → generation → citation extraction)
- [X] T034 Implement `RAGService.query()` method (accepts Question object, returns Answer object with citations)
- [X] T035 Implement `RAGService.health_check()` method (returns Ollama, ChromaDB, embedding model status)
- [X] T036 Implement request ID generation and tracing throughout pipeline (generate UUID per query, log all steps)
- [X] T037 Implement processing time measurement (track embedding, retrieval, generation times, include in answer)
- [X] T038 Implement low confidence handling (if confidence <0.5, return "I don't know" message instead of uncertain answer)
- [X] T039 [P] Implement `services/rag-llm-service/tests/integration/test_query_flow.py` end-to-end tests (mock ChromaDB + Ollama, test full query → answer → citations flow)

**Deliverable**: Complete RAG service pipeline functional with error handling and structured logging

---

### Phase 2.6: REST API Layer

**Goal**: Expose RAG service as REST API via HTTP endpoints.

- [X] T040 Create `services/rag-llm-service/src/server.py` with FastAPI application (async handlers, CORS, request logging)
- [X] T041 Implement `POST /query` endpoint (accepts JSON with question + optional filters, returns Answer JSON with citations)
- [X] T042 Implement `GET /health` endpoint (returns service health status including Ollama, ChromaDB, embedding model status)
- [X] T043 Implement request/response validation using Pydantic schemas (validate Query input, Answer output)
- [X] T044 Implement structured JSON logging for all HTTP requests (timestamp, request_id, method, path, status, processing_time)
- [X] T045 Implement error response format (consistent error JSON with error_type, error_details, request_id)
- [X] T046 Implement CORS headers (allow FastAPI wrapper to call RAG service endpoints)
- [X] T047 [P] Implement `services/rag-llm-service/tests/integration/test_server.py` integration tests (test /query endpoint, test /health endpoint, test error responses)

**Deliverable**: REST API fully functional with all error handling and logging

---

### Phase 2.7: Testing & Quality Assurance

**Goal**: Comprehensive unit, integration, and end-to-end testing.

- [X] T048 Create `services/rag-llm-service/tests/conftest.py` with pytest fixtures (mock ChromaDB client, mock Ollama client, sample query/answer objects)
- [X] T049 Implement `services/rag-llm-service/tests/unit/test_schemas.py` testing data validation (Query, Answer, Citation models)
- [X] T050 Implement `services/rag-llm-service/tests/unit/test_validators.py` testing input validation (question length, filter format)
- [X] T051 Implement `services/rag-llm-service/tests/unit/test_logger.py` testing structured JSON logging format
- [ ] T052 Implement `services/rag-llm-service/tests/integration/test_ollama_integration.py` testing Ollama connectivity (requires live Ollama running)
- [X] T053 Create `services/rag-llm-service/sample_queries.json` with 5-10 test queries and expected answers (for manual testing and demo)
- [X] T054 Create test coverage report (target >80% coverage for core modules)
- [X] T055 Run full test suite and verify all tests passing (unit + integration + coverage report)

**Deliverable**: ✅ Comprehensive test suite with 89% code coverage; all 173 tests passing

---

### Phase 2.8: Docker & Deployment

**Goal**: Containerize RAG service and prepare for deployment.

- [X] T056 Build Docker image for RAG service (`docker build -t rag-llm-service:latest`)
- [X] T057 Test Docker image locally (verify service starts, /health returns 200, /query returns valid response)
- [X] T058 Create `.dockerignore` file (exclude __pycache__, .pytest_cache, .git, *.pyc)
- [X] T059 Test docker-compose setup (run `docker-compose up`, verify Ollama and RAG service both healthy)
- [X] T060 Create Ollama model download script (script to pull mistral:7b model on first run)
- [X] T061 Document Docker setup in `services/rag-llm-service/README.md` (build instructions, run instructions, port mapping)

**Deliverable**: ✅ Production-ready Docker configuration with comprehensive documentation

---

### Phase 2.9: Documentation & Developer Guide

**Goal**: Complete developer documentation and API reference.

- [ ] T062 Create `services/rag-llm-service/API.md` with endpoint documentation (POST /query, GET /health, request/response examples, error codes)
- [ ] T063 Create `services/rag-llm-service/ARCHITECTURE.md` with system design (pipeline stages, error handling, logging flow)
- [ ] T064 Create `services/rag-llm-service/EXAMPLES.py` with code examples (how to use RAGService module, how to integrate with FastAPI wrapper)
- [ ] T065 Create troubleshooting guide in README (common errors, debug tips, dependency issues)
- [ ] T066 Document environment variable setup and defaults (`services/rag-llm-service/.env.example`)
- [ ] T067 Create deployment guide (Docker Compose, environment variables, health check verification)

**Deliverable**: Complete developer documentation for integration and deployment

---

### Phase 2.10: Integration Testing (Cross-Service)

**Goal**: Verify RAG service works correctly with HR Data Pipeline and FastAPI wrapper.

**Prerequisites**: HR Data Pipeline team must have populated ChromaDB with ≥100 sample chunks

- [ ] T068 [P] Test retrieval with live HR Data Pipeline data (verify embedding API returns 384-dim vectors, query ChromaDB, verify chunks returned with correct metadata schema matching data-model.md)
- [ ] T069 [P] Test citation generation with real chunks (verify citations match source_doc and section_title from metadata)
- [ ] T070 [P] Test confidence calculation with real similarity scores (verify confidence ≥0.5 returns answer, <0.5 returns "I don't know")
- [ ] T071 [P] Test end-to-end with sample queries (run 5-10 sample queries, verify answers + citations + confidence scores)
- [ ] T072 Test error handling (disconnect ChromaDB, disconnect Ollama, verify graceful failures and error messages)
- [ ] T073 Performance testing (measure latency for /query endpoint under various load, verify <5s target met)
- [ ] T074 Tune confidence threshold using 100-query test set (measure precision/recall at thresholds 0.4, 0.5, 0.6, 0.7; select threshold maximizing precision while maintaining >80% coverage; document results in ARCHITECTURE.md)

**Deliverable**: RAG service verified working with actual HR Data Pipeline data; confidence threshold empirically tuned

---

## Task Dependencies

### Critical Path (Blocking Dependencies)

```
T001-T007 (Setup) ──→
                  ├─→ T008-T013 (Schemas) ──→
                  │                        ├─→ T014-T019 (Retrieval) ──→
                  │                        ├─→ T020-T024 (Embedding API) ──┐
                  │                        └─→ T025-T032 (Generation) ──┤
                  │                                                    ├─→ T033-T039 (Core) ──→
                  │                                                    │
                  └───────────────────────────────────────────────────→ T040-T047 (API) ──→
                                                                           T048-T055 (Tests) ──→
                                                                           T056-T061 (Docker) ──→
                                                                           T062-T067 (Docs) ──→
                                                                           T068-T073 (Integration)
```

### Parallelizable Sections

**Phase 2.2 & 2.3**: Retrieval and embedding API client can be implemented in parallel (different modules)
**Phase 2.4**: Generation and citation parsing can be split across developers
**Phase 2.7**: Unit tests can be written alongside feature implementation

### Dependency Notes

- Tests (T019, T024, T031-T032, T039, T047, T049-T055) can be written during feature implementation (TDD approach recommended)
- Docker setup (T056-T061) depends on all source code complete (T001-T047)
- Integration testing (T068-T074) depends on HR Data Pipeline team providing:
  - Embedding API endpoint (for T020-T024 implementation)
  - ChromaDB populated with ≥100 test chunks using matching embedding model (all-MiniLM-L6-v2)
- Performance testing (T073) should use realistic data volumes (1000+ chunks recommended)
- Confidence threshold tuning (T074) requires 100-query test set with ground truth labels

---

## Execution Strategy

### Phase 2.0-2.1 (Setup & Schemas)
**Duration**: 1-2 days | **Assignee**: Lead developer  
**Output**: Project structure, all Pydantic schemas, configuration handling ready

### Phase 2.2-2.4 (Pipeline Implementation)
**Duration**: 3-5 days | **Assignee**: 1-2 developers (parallelizable)  
**Output**: Retrieval, embedding API integration, and generation pipelines functional
**Dependency**: Requires HR Data Pipeline embedding API endpoint available

### Phase 2.5-2.6 (Core Logic & API)
**Duration**: 2-3 days | **Assignee**: Lead developer  
**Output**: RAG service and REST API fully functional

### Phase 2.7-2.9 (Testing & Documentation)
**Duration**: 2-3 days | **Assignee**: QA + lead developer  
**Output**: >80% test coverage, complete documentation

### Phase 2.10 (Integration Testing)
**Duration**: 1-2 days | **Assignee**: All (cross-functional)  
**Output**: Verified working with HR Data Pipeline and FastAPI wrapper

**Total Estimated Time**: 9-15 days of development work

---

## Success Criteria for Phase 2

- ✅ All 74 tasks completed and checked
- ✅ >80% code coverage (unit + integration tests)
- ✅ All functional requirements (FR-001 through FR-021) implemented
- ✅ All success criteria (SC-001 through SC-004) verified
- ✅ Docker image builds and runs without errors
- ✅ REST API returns correct response format for all endpoints
- ✅ Integration tests pass with HR Data Pipeline test data
- ✅ Structured JSON logging functional for all API calls
- ✅ Documentation complete (API, architecture, examples, troubleshooting)
- ✅ Performance targets met (<5s RAG service, <10s end-to-end p95)

---

## Handoff Checklist

Before marking feature complete:

- [ ] All 74 tasks checked and verified
- [ ] Code review completed by peer
- [ ] Tests passing locally and in CI/CD
- [ ] Docker image pushed to registry
- [ ] README and API documentation published
- [ ] Sample queries working end-to-end
- [ ] Performance benchmarks documented
- [ ] Integration with FastAPI wrapper tested
- [ ] Constitution principles verified (Accuracy, Transparency, Self-Contained, Reproducible)
- [ ] Ready for production deployment

---

## Notes

**Architecture Decisions**:
- RAG service remains stateless (all state in ChromaDB and Ollama)
- Citation extraction via regex parsing of LLM output (simpler than token classification)
- Confidence threshold (0.5 initial heuristic) enforced at service level; will be tuned in Phase 2.10 (T074)
- Embedding generation delegated to HR Data Pipeline API (ensures consistency with document embeddings)
- Structured JSON logging enables request tracing and debugging

**Risk Mitigation**:
- Early integration testing with HR Data Pipeline (T068-T073) catches schema mismatches before production
- Mock-based unit tests (T019, T024, T031-T032) enable testing without live dependencies
- Docker-based deployment ensures reproducibility and isolation

**Future Enhancements** (out of scope for Phase 2):
- Embedding model fine-tuning on HR-specific terms
- Citation confidence scoring (which citations are most reliable)
- Multi-hop reasoning (query spans multiple documents)
- Streaming response support for real-time feedback
