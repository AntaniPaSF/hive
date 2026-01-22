# Implementation Plan: HR Data Pipeline & Knowledge Base

**Branch**: `020-hr-data-pipeline` | **Date**: January 21, 2026 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/020-hr-data-pipeline/spec.md`

## Summary

Build a data ingestion pipeline that converts the provided HR policy PDF into a searchable vector database for text-based retrieval. The pipeline will chunk documents optimally and store them in ChromaDB in text-only mode (no embeddings). All source documents will be version-controlled in git for reproducibility.

**Technical Approach**: Python-based ETL pipeline using PyPDF2 for extraction, tiktoken for token counting, and ChromaDB for text storage. No external data sources required - pipeline operates exclusively with PDF content.

## Technical Context

**Language/Version**: Python 3.11+ (from existing Dockerfile)  
**Primary Dependencies**: PyPDF2 3.0.1, ChromaDB 0.4.22, tiktoken 0.5.0, numpy<2.0 (ChromaDB compatibility), pytest 7.0+  
**Storage**: ChromaDB (local SQLite-based text storage), Git repository for source documents  
**Testing**: pytest with unit test structure  
**Target Platform**: Docker containers on Linux/macOS, CPU-only hardware (no GPU requirement)  
**Project Type**: Single project (data pipeline extending existing app/ structure)  
**Performance Goals**: 
  - Process 100 PDF pages in <10 minutes
  - Query retrieval in <500ms (p95)
  - 5 minute end-to-end ingestion for provided PDF
**Constraints**: 
  - Self-contained: No external API dependencies (no OpenAI/Anthropic)
  - CPU-only: Embedding model must run on standard hardware
  - Local storage: Vector database persists via Docker volume
  - Semantic similarity thresholds: 0.75 for relevance, 0.85 for duplicates
**Scale/Scope**: 
  - Initial: Single PDF document (~100-500 pages)
  - Extended: Additional Kaggle/HuggingFace documents aligned to PDF topics
  - Target: 1000+ chunks in vector database

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Accuracy Over Speed**: RAG retrieval mechanism designed to prevent hallucinations?
  - ✅ Semantic similarity validation (0.75 threshold) ensures only relevant external data is ingested
  - ✅ Contradiction detection prevents conflicting information from entering knowledge base
  - ✅ Duplicate detection (0.85 threshold) prevents redundant chunks that could dilute retrieval quality
  - ✅ PDF document is authoritative source; external data supplements but cannot override

- [x] **Transparency**: All responses include source citations (document + section)?
  - ✅ Every chunk stores metadata: `source_doc`, `source_type`, `page_number`, `section_title`
  - ✅ Data schema defines citation format compatible with `app/core/citations.py`
  - ✅ Chunk index enables sequential retrieval for context expansion
  - ✅ RAG Engineer can construct citations from metadata fields

- [x] **Self-Contained**: No external API dependencies (OpenAI, Anthropic, etc.)?
  - ✅ ChromaDB runs locally (SQLite backend, no cloud service)
  - ✅ sentence-transformers with `all-MiniLM-L6-v2` model (CPU-only, 384 dimensions)
  - ✅ PyPDF2 for local PDF parsing (no external OCR service)
  - ✅ External data sourced once during setup, then git-tracked (no runtime API calls)

- [x] **Reproducible**: Setup achievable in <15 minutes via single command?
  - ✅ All source documents stored in `data/` folder (git-tracked)
  - ✅ Single command ingestion: `bash scripts/ingest.sh --all`
  - ✅ Docker Compose handles all dependencies (no manual Python setup)
  - ✅ Manifest file (`data/manifest.json`) tracks ingestion state with checksums

- [x] **Performance**: Architecture supports <10s response time on CPU-only hardware?
  - ✅ `all-MiniLM-L6-v2` is optimized for CPU inference (fast embedding generation)
  - ✅ ChromaDB query performance: <500ms for p95 queries (FR-009)
  - ✅ Chunking strategy balances context (512 tokens) with retrieval speed
  - ✅ Ingestion is one-time cost; retrieval latency is what matters for user experience

- [x] **Citation Check**: 100% of answers traceable to source documents?
  - ✅ Every chunk includes `source_doc`, `page_number`, `section_title` metadata
  - ✅ Validation ensures no chunks are ingested without complete metadata
  - ✅ Data schema export (FR-015) documents citation format for RAG Engineer
  - ✅ No external data ingested without linkage to PDF topics (traceability)

**Gate Status**: ✅ **PASS** - All constitution principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/020-hr-data-pipeline/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── chunk-schema.json         # Chunk data structure
│   ├── metadata-schema.json      # Metadata fields
│   └── ingestion-api.yaml        # CLI interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── core/
│   ├── citations.py       # Existing: Citation enforcement
│   ├── config.py          # Existing: Environment config - EXTEND with pipeline settings
│   └── __init__.py
├── data/
│   └── seed/              # Existing: Demo policies
├── ingestion/             # NEW: Data pipeline code
│   ├── __init__.py
│   ├── pdf_parser.py      # PDF text extraction
│   ├── chunker.py         # Document chunking logic
│   ├── embeddings.py      # Embedding generation
│   ├── validator.py       # Contradiction/duplicate detection
│   └── cli.py             # CLI interface for ingestion
├── vectordb/              # NEW: Vector database wrapper
│   ├── __init__.py
│   ├── client.py          # ChromaDB client wrapper
│   └── models.py          # Data models for chunks/metadata
├── server.py              # Existing: HTTP server - RAG Engineer will integrate
└── ui/
    └── static/            # Existing: UI files

data/                      # NEW: Actual HR documents (git-tracked)
├── README.md              # Existing: Usage guide
├── manifest.json          # NEW: Ingestion tracking
├── schema.json            # NEW: Data schema export (FR-015)
├── pdf/                   # Authoritative PDF source
│   └── Software_Company_Docupedia_FILLED.pdf
├── kaggle/                # External augmentation
└── huggingface/           # External augmentation

vectordb_storage/          # NEW: Vector DB persistence (Docker volume, not git-tracked)
└── chroma.sqlite3         # ChromaDB storage

scripts/
├── setup.sh               # Existing: Docker build
├── start.sh               # Existing: Docker run
├── verify.sh              # Existing: Health checks
├── package.sh             # Existing: Distribution
└── ingest.sh              # NEW: Wrapper for ingestion CLI

tests/
├── contract/              # Existing structure
│   └── test_ingestion_contract.py  # NEW: Validate CLI interface
├── integration/           # Existing structure
│   └── test_ingestion_e2e.py       # NEW: End-to-end ingestion test
└── unit/                  # Existing structure
    ├── test_pdf_parser.py          # NEW: PDF extraction tests
    ├── test_chunker.py             # NEW: Chunking logic tests
    ├── test_embeddings.py          # NEW: Embedding generation tests
    └── test_validator.py           # NEW: Validation logic tests
```

**Structure Decision**: Single project structure extending existing `app/` directory. The data pipeline is a foundational service that other components (RAG server, UI) will consume. Following the existing pattern of `app/core/`, `app/data/`, we add `app/ingestion/` and `app/vectordb/` as new modules. Source documents are stored in `data/` folder (git-tracked for reproducibility per constitution), while the vector database persists via Docker volume (not git-tracked due to size/binary format).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. All constitution principles are satisfied without compromises.

---

## Phase 0: Outline & Research

**Objective**: Resolve all technical unknowns and document best practices for implementation.

### Research Tasks

1. **ChromaDB Configuration for CPU-Only Deployment**
   - **Question**: What ChromaDB settings optimize for CPU-only hardware without GPU?
   - **Why**: Constitution requires <10s response time on standard hardware (no GPU requirement)
   - **Deliverable**: Configuration parameters for ChromaDB initialization

2. **Sentence-Transformers Model Selection**
   - **Question**: Which sentence-transformers model balances embedding quality with CPU inference speed?
   - **Why**: Need fast embeddings (<500ms per chunk) while maintaining retrieval accuracy (>0.7 similarity)
   - **Deliverable**: Model name, dimensions, performance benchmarks

3. **PDF Text Extraction Edge Cases**
   - **Question**: How does PyPDF2 handle tables, multi-column layouts, headers/footers?
   - **Why**: FR-001 requires preserving structural information; edge cases identified in spec
   - **Deliverable**: Extraction strategy with preprocessing steps

4. **Semantic Chunking Strategies**
   - **Question**: What chunking approach preserves HR policy context (section boundaries, complete statements)?
   - **Why**: Poor chunking degrades retrieval quality (impacts Accuracy principle)
   - **Deliverable**: Chunking algorithm with overlap strategy

5. **Contradiction Detection Implementation**
   - **Question**: How to detect semantic contradictions between external data and PDF content?
   - **Why**: FR-006 requires excluding contradictory information to maintain Accuracy
   - **Deliverable**: Semantic similarity approach, threshold calibration method

6. **Kaggle/HuggingFace HR Dataset Discovery**
   - **Question**: Which Kaggle/HuggingFace datasets contain relevant HR policy information?
   - **Why**: FR-005 requires external augmentation with topic alignment
   - **Deliverable**: List of candidate datasets with relevance assessment

7. **Vector Database Indexing for Retrieval Speed**
   - **Question**: What ChromaDB indexing parameters ensure <500ms query performance (SC-009)?
   - **Why**: Performance requirement for RAG pipeline responsiveness
   - **Deliverable**: Index configuration and benchmarking approach

8. **Git LFS for Large Document Storage**
   - **Question**: Should large PDFs use Git LFS or direct storage in repository?
   - **Why**: Reproducibility principle requires git-tracked documents; need to balance repo size
   - **Deliverable**: Storage decision with size thresholds

### Research Output

All findings will be consolidated in `research.md` following this format:

```markdown
## [Research Task Title]

**Decision**: [what was chosen]  
**Rationale**: [why chosen - reference constitution principles where applicable]  
**Alternatives Considered**: [what else was evaluated and why rejected]  
**Implementation Notes**: [specific configuration values, code snippets, references]
```

---

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete (all NEEDS CLARIFICATION resolved)

### Design Deliverables

#### 1. Data Model (`data-model.md`)

Extract entities from feature spec and define schema:

**Entities**:
- **HR Document**: filename, source_type, file_size, page_count, checksum, timestamp
- **Document Chunk**: chunk_id, text, token_count, chunk_index, embedding_vector
- **Chunk Metadata**: source_doc, source_type, page_number, section_title, related_topic, validation_status
- **Vector Database Entry**: chunk_id (FK), embedding, metadata_dict, similarity_score (computed)
- **Data Manifest**: document_path, source_type, checksum, ingestion_timestamp, chunk_count, validation_results

**Relationships**:
- HR Document (1) → (many) Document Chunks
- Document Chunk (1) → (1) Chunk Metadata
- Document Chunk (1) → (1) Vector Database Entry
- Data Manifest (many) → (many) HR Documents (tracking table)

**Validation Rules**:
- `source_type` ∈ {pdf, kaggle, huggingface}
- `similarity_threshold_relevance` = 0.75 (external data must exceed)
- `similarity_threshold_duplicate` = 0.85 (duplicates must not exceed)
- `chunk_size` = 512 tokens (default, configurable)
- `chunk_overlap` = 50 tokens (default, configurable)

**State Transitions**:
- Document: Discovered → Validated → Chunked → Embedded → Stored
- Chunk: Created → Validated (contradiction check) → Validated (duplicate check) → Ingested

#### 2. API Contracts (`contracts/`)

Generate contracts from functional requirements:

**`contracts/chunk-schema.json`** (FR-011, FR-015):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Chunk",
  "type": "object",
  "required": ["id", "text", "embedding", "metadata"],
  "properties": {
    "id": {"type": "string", "format": "uuid"},
    "text": {"type": "string", "minLength": 1},
    "embedding": {
      "type": "array",
      "items": {"type": "number"},
      "minItems": 384,
      "maxItems": 384
    },
    "metadata": {"$ref": "#/definitions/metadata"}
  },
  "definitions": {
    "metadata": {
      "type": "object",
      "required": ["source_doc", "source_type", "page_number", "section_title", "chunk_index", "timestamp"],
      "properties": {
        "source_doc": {"type": "string"},
        "source_type": {"type": "string", "enum": ["pdf", "kaggle", "huggingface"]},
        "page_number": {"type": "integer", "minimum": 1},
        "section_title": {"type": "string"},
        "chunk_index": {"type": "integer", "minimum": 0},
        "timestamp": {"type": "string", "format": "date-time"},
        "related_topic": {"type": "string"},
        "validation_status": {
          "type": "object",
          "properties": {
            "contradiction_check": {"type": "boolean"},
            "duplicate_check": {"type": "boolean"}
          }
        }
      }
    }
  }
}
```

**`contracts/ingestion-api.yaml`** (FR-012, FR-013):
OpenAPI spec for CLI interface (even though it's CLI, define the programmatic interface):
```yaml
openapi: 3.0.0
info:
  title: Ingestion Pipeline CLI
  version: 1.0.0
paths:
  /ingest:
    post:
      summary: Ingest documents from specified source
      parameters:
        - name: source
          in: query
          schema:
            type: string
            enum: [pdf, kaggle, huggingface, all]
        - name: rebuild
          in: query
          schema:
            type: boolean
        - name: validate_only
          in: query
          schema:
            type: boolean
      responses:
        '200':
          description: Ingestion completed successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: {type: string}
                  documents_processed: {type: integer}
                  chunks_created: {type: integer}
                  contradictions_excluded: {type: integer}
                  duplicates_skipped: {type: integer}
                  processing_time_seconds: {type: number}
```

#### 3. Quickstart Guide (`quickstart.md`)

Step-by-step guide for RAG Engineer to consume the vector database:

```markdown
# HR Data Pipeline Quickstart

## Prerequisites
- Docker & Docker Compose installed
- Git repository cloned
- HR policy PDF placed in `data/pdf/`

## Setup (One-Time)

1. Build containers: `bash scripts/setup.sh`
2. Start services: `bash scripts/start.sh`
3. Ingest data: `bash scripts/ingest.sh --all`
4. Verify: Check `data/manifest.json` for chunk counts

## Querying Vector Database

### Python Example
```python
from app.vectordb.client import ChromaDBClient

client = ChromaDBClient()
results = client.query(
    query_text="What is the vacation policy?",
    n_results=5
)

for chunk in results:
    print(f"Source: {chunk['metadata']['source_doc']}")
    print(f"Section: {chunk['metadata']['section_title']}")
    print(f"Text: {chunk['text']}")
```

### Data Schema
See `data/schema.json` for complete field definitions.

## Troubleshooting
- **No results returned**: Run `bash scripts/ingest.sh --rebuild`
- **Slow queries**: Check ChromaDB index status
- **Missing metadata**: Validate PDF extraction via logs
```

#### 4. Agent Context Update

Run agent context update script:
```bash
bash .specify/scripts/bash/update-agent-context.sh copilot
```

This will:
- Detect VS Code Copilot agent
- Update `.github/copilot-instructions.md`
- Add only new technologies from this plan (PyPDF2, ChromaDB, sentence-transformers)
- Preserve manual additions between `<!-- MANUAL -->` markers

---

## Phase 2: Tasks Breakdown

**Prerequisites**: Phase 1 complete (data-model.md, contracts/, quickstart.md generated)

**STOP HERE**: The `/speckit.plan` command ends after Phase 1 planning. Phase 2 is triggered separately via `/speckit.tasks` command.

---

## Summary

**Branch**: `020-hr-data-pipeline`  
**Specification**: `specs/020-hr-data-pipeline/spec.md` (363 lines, 4 user stories, 19 FRs, 11 SCs)  
**Plan Status**: Constitution Check ✅ PASS | Phase 0 Research (8 tasks) | Phase 1 Design (data-model, 3 contracts, quickstart, agent context)

**Next Steps**:
1. Execute Phase 0: Generate `research.md` by dispatching 8 research agents
2. Execute Phase 1: Generate `data-model.md`, `contracts/`, `quickstart.md`, update agent context
3. Re-evaluate Constitution Check post-design
4. Command ends - report branch, plan path, and generated artifacts

**Key Decisions**:
- Technology: Python 3.11, ChromaDB 0.4.22, sentence-transformers (all-MiniLM-L6-v2), PyPDF2 3.0.1
- Structure: Extend `app/` directory with `app/ingestion/`, `app/vectordb/`
- Storage: Git-tracked `data/` folder for documents, Docker volume for vector database
- Integration: Compatible with `app/core/citations.py`, extends `app/core/config.py`
- Performance: <10 min for 100 pages, <500ms query retrieval, CPU-only

**Constitution Compliance**: All 6 principles satisfied without violations or compromises.
