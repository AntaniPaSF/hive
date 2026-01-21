# Implementation Plan: Intelligent Knowledge Retrieval Service (RAG Pipeline & LLM Service)

**Branch**: `001-rag-pipeline-llm-service` | **Date**: 2026-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-rag-pipeline-llm-service/spec.md`

## Summary

The RAG Pipeline & LLM Service provides the core reasoning engine for the Corporate Digital Assistant. It enables users to ask questions in natural language and receive synthesized answers grounded exclusively in internal documentation, with source citations. The service consists of three main pipelines: (1) **Ingestion Pipeline** – converting documents (PDF/Markdown/Text) into semantic searchable vectors; (2) **Retrieval Pipeline** – performing semantic search to find relevant document chunks; (3) **Generation Pipeline** – using a local LLM to synthesize answers from retrieved context. The service enforces strict citation requirements and prevents hallucinations by rejecting answers that lack source grounding.

## Technical Context

**Language/Version**: Python 3.12+  
**LLM Host**: Ollama (self-hosted, running Llama3 or Mistral 7B)  
**Orchestration**: LangChain (embeddings, retrieval chains, prompt management)  
**Vector Store Interface**: Connects to externally managed ChromaDB instance (via client)  
**Containerization**: Docker (multi-stage build for LLM service)  
**Testing**: pytest (unit and integration tests)  
**Target Platform**: Linux/macOS (CPU-only, no GPU requirement)  
**Project Type**: RAG LLM service (Ollama + retrieval + generation)  
**Performance Goals**: RAG service <5s for query responses; end-to-end system p95 <10s  
**Constraints**: CPU-only hardware, no external paid APIs, zero internet dependency post-setup, structured JSON logging  
**Scale/Scope**: MVP supports up to ~10k documents, response time scales linearly with knowledge base size  
**Integration**: Consumes vector store API; provides retrieval/generation endpoints to FastAPI wrapper  
**Role Scope**: Ollama setup, RAG pipeline (embeddings→retrieval→generation), prompt engineering, citation extraction

## Constitution Check

*GATE: Must pass before proceeding to Phase 1. Re-check after design completion.*

- [x] **Accuracy Over Speed**: RAG retrieval with citation enforcement prevents hallucinations; answers are grounded in source documents only.
- [x] **Transparency**: All responses include source citations (document name + section reference); `/query` endpoint always returns citations or explicit "I don't know" message.
- [x] **Self-Contained**: Ollama + ChromaDB are self-hosted, open-source; no external paid APIs (OpenAI, Anthropic, etc.); all components run on CPU-only hardware.
- [x] **Reproducible**: Docker-based deployment; single `docker-compose up` command; all dependencies version-pinned; setup achievable <15 minutes.
- [x] **Performance**: Architecture targets <5s response time for RAG service (SC-003), end-to-end <10s p95 (SC-004) on CPU-only hardware.
- [x] **Citation Check**: 100% of answers traceable to source documents; "I don't know" scenario includes explicit message; no general knowledge fallback.

**Gate Status**: ✅ **PASSED** – All constitution principles are satisfied by the design.

## Project Structure

### Documentation (this feature)

```text
specs/001-rag-pipeline-llm-service/
├── plan.md              # This file (implementation plan)
├── spec.md              # Feature specification
├── research.md          # Phase 0 research artifacts (technology choices, best practices)
├── data-model.md        # Phase 1 data entities and relationships
├── service-interface.md # Phase 1 service interface (how to query RAG, inter-service communication)
├── quickstart.md        # Phase 1 developer quickstart guide
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
libraries/rag-pipeline/
├── src/
│   ├── __init__.py
services/rag-llm-service/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Configuration (env vars: Ollama host, vector store endpoint)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── embeddings.py            # Embedding generation (all-MiniLM-L6-v2, managed by HR pipeline)
│   │   ├── ollama_client.py         # Ollama LLM client wrapper
│   │   ├── retrieval.py             # Vector store query logic (calls ChromaDB via HTTP, retrieves pre-computed embeddings)
│   │   └── generation.py            # LLM answer generation with citation extraction
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── qa_prompt.py             # Q&A prompt template with citation instructions
│   │   └── citation_parser.py       # Extract citation markers from LLM output
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py                # Structured JSON logging
│   │   ├── errors.py                # Custom exceptions
│   │   └── validators.py            # Input validation
│   └── schemas/
│       ├── __init__.py
│       ├── query.py                 # Query request/response schemas
│       └── citation.py              # Citation entity schema

├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── unit/
│   │   ├── test_ollama_client.py
│   │   ├── test_retrieval.py
│   │   ├── test_generation.py
│   │   └── test_citation_parser.py
│   └── integration/
│       ├── test_query_flow.py       # End-to-end: retrieve → generate → citations
│       └── test_ollama_integration.py

├── Dockerfile                       # Multi-stage build for Ollama + RAG service
├── docker-compose.yml               # Ollama service definition
├── requirements.txt                 # Python dependencies (pinned versions)
├── pyproject.toml                   # Project metadata
├── sample_queries.json              # Test queries with expected outputs
└── README.md                        # Service README + API usage guide
```

**Structure Decision**: RAG LLM service (Ollama + retrieval + generation logic). This service handles: (1) querying the vector store (ChromaDB, managed by HR Data Pipeline), (2) consuming pre-computed embeddings (all-MiniLM-L6-v2, generated by HR pipeline), (3) calling Ollama for answer generation, (4) citation extraction. The service is stateless and communicates with external dependencies (vector store via HTTP, document ingestion pipeline) via REST. FastAPI wrapper (developed by colleague) exposes this service as REST endpoints
No constitution violations. Ollama, ChromaDB, and FastAPI are standard, lightweight choices that support the MVP goals.

**Embedding Generation Ownership**: RAG service calls HR Data Pipeline embedding API to convert queries to 384-dim vectors. HR pipeline owns the all-MiniLM-L6-v2 model and provides embeddings as a service to ensure consistency between document embeddings (stored in ChromaDB) and query embeddings.

**Confidence Threshold (0.5)**: Initial heuristic using midpoint of cosine similarity range (0.0-1.0). Will be empirically tuned during Phase 2.10 integration testing with real data to maximize precision (SC-002: 90%) while maintaining >80% answer coverage. Future enhancement: adaptive thresholds by document type.

**OCR/Table Parsing Ownership**: HR Data Pipeline is responsible for PDF parsing, OCR, and table extraction (FR-005). RAG service assumes documents are pre-processed into clean text chunks with metadata.

| Decision | Rationale |
|----------|-----------|
| **Monolithic API vs. Microservices** | MVP requires simplicity and single-command deployment; microservices add operational complexity without MVP value. |
| **LangChain for Orchestration** | Abstracts LLM and vector store interactions; standard choice for RAG systems; reduces custom code. |
| **ChromaDB (not FAISS)** | Persistent local storage with web API support; simpler than FAISS for local MVP. |
| **FastAPI (not Flask/Django)** | Async support, automatic OpenAPI docs, type safety (Pydantic); excellent for I/O-bound services like RAG. |
| **Docker Compose (not Kubernetes)** | Single-command local deployment; aligns with reproducibility requirement. |

## Development Phase

### Phase 0: Research & Technology Validation
- Validate Ollama setup and model availability (Llama3, Mistral 7B)
- Confirm ChromaDB persistence and semantic search accuracy
- Evaluate LangChain RAG patterns and document loading
- Document OCR/table parsing approach (pytesseract, pandas)
- Confirm FastAPI async patterns for citation enforcement

**Deliverable**: `research.md` with technology decisions and proof-of-concept validation

### Phase 1: Design & Module Interface
- Define data model (Query, Answer, Citation entities)
- Define service interface: how to query RAG service, expected inputs/outputs
- Document inter-service communication patterns (vector store queries, embedding API from HR pipeline, FastAPI integration)
- Design structured JSON logging schema
- Create developer quickstart guide for service usage

**Deliverables**: `data-model.md`, `service-interface.md`, `quickstart.md`

### Phase 2: Implementation
- Set up Ollama Docker container with Mistral 7B model
- Implement retrieval pipeline (call HR Data Pipeline embedding API for query embeddings, query ChromaDB with 384-dim vectors)
- Implement generation pipeline (prompt engineering, Ollama integration, citation extraction)
- Implement service methods with error handling and structured logging
- Write unit and integration tests (including sample test queries)
- Build and test Docker container for LLM service
- Create example usage script demonstrating module integration

**Deliverable**: `tasks.md` with discrete, testable task breakdown
