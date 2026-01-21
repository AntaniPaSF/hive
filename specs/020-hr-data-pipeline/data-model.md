# Data Model: HR Data Pipeline & Knowledge Base

**Branch**: `020-hr-data-pipeline` | **Date**: January 21, 2026  
**Purpose**: Define entities, relationships, and validation rules for the ingestion pipeline

---

## Entities

### 1. HR Document

Represents an HR policy document from any source (PDF, Kaggle, HuggingFace).

**Attributes**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `document_id` | UUID | Unique identifier | Auto-generated |
| `filename` | String | Original filename | Required, max 255 chars |
| `source_type` | Enum | Document origin | Must be: `pdf`, `kaggle`, `huggingface` |
| `file_path` | String | Relative path from repo root | Required, starts with `data/` |
| `file_size_bytes` | Integer | File size in bytes | Positive integer |
| `page_count` | Integer | Number of pages (0 for non-PDF) | Non-negative integer |
| `language` | String | Document language | ISO 639-1 code, default `en` |
| `checksum` | String | SHA-256 hash | Required, 64 hex chars |
| `created_at` | DateTime | First ingestion timestamp | ISO 8601 format |
| `updated_at` | DateTime | Last modification timestamp | ISO 8601 format |
| `related_topics` | List[String] | PDF topics this document relates to | Empty for PDF source, required for external |

**Example**:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "Software_Company_Docupedia_FILLED.pdf",
  "source_type": "pdf",
  "file_path": "data/pdf/Software_Company_Docupedia_FILLED.pdf",
  "file_size_bytes": 2097152,
  "page_count": 421,
  "language": "en",
  "checksum": "a3b2c1d4e5f6...",
  "created_at": "2026-01-21T10:30:00Z",
  "updated_at": "2026-01-21T10:30:00Z",
  "related_topics": []
}
```

---

### 2. PDF Topic

Represents a major topic extracted from the authoritative PDF document using TF-IDF.

**Attributes**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `topic_id` | UUID | Unique identifier | Auto-generated |
| `topic_name` | String | Human-readable topic | Required, max 100 chars |
| `keywords` | List[String] | TF-IDF terms for this topic | Min 3, max 10 keywords |
| `section_reference` | String | PDF section where topic appears | Optional, format "§1.2" |
| `external_chunk_count` | Integer | Number of external chunks linked | Non-negative, default 0 |

**Example**:
```json
{
  "topic_id": "650e8400-e29b-41d4-a716-446655440001",
  "topic_name": "vacation policy",
  "keywords": ["vacation", "paid time off", "pto", "leave", "holiday"],
  "section_reference": "§3.1",
  "external_chunk_count": 15
}
```

---

### 3. Document Chunk

Represents a segment of text optimized for retrieval (512 tokens with 50 token overlap).

**Attributes**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `chunk_id` | UUID | Unique identifier | Auto-generated |
| `document_id` | UUID | Foreign key to HR Document | Required, must exist |
| `text` | String | Chunk content | Required, min 100 chars |
| `token_count` | Integer | Number of tokens | Range: 100-512 |
| `chunk_index` | Integer | Position in document (0-based) | Non-negative |
| `embedding_vector` | Array[Float] | 384-dimensional embedding | Required, exactly 384 floats |
| `created_at` | DateTime | Chunk creation timestamp | ISO 8601 format |

**Example**:
```json
{
  "chunk_id": "750e8400-e29b-41d4-a716-446655440002",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Employees are entitled to 15 days of paid vacation per year...",
  "token_count": 487,
  "chunk_index": 12,
  "embedding_vector": [0.023, -0.145, 0.891, ...],
  "created_at": "2026-01-21T10:35:22Z"
}
```

---

### 4. Chunk Metadata

Information associated with each chunk for retrieval context and citation generation.

**Attributes**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `chunk_id` | UUID | Foreign key to Document Chunk | Required, must exist |
| `source_doc` | String | Document filename | Required, max 255 chars |
| `source_type` | Enum | Document origin | Must be: `pdf`, `kaggle`, `huggingface` |
| `page_number` | Integer | Page where chunk appears | Positive integer (0 for non-PDF) |
| `section_title` | String | Section heading | Optional, max 200 chars |
| `related_topic` | String | PDF topic this chunk addresses | Required for external sources |
| `validation_status` | Object | Validation results | See Validation Status schema below |
| `embedding_model` | String | Model used for embedding | Required, e.g., "all-MiniLM-L6-v2" |
| `embedding_model_version` | String | Model version | Required, e.g., "v2.2.2" |

**Validation Status Schema**:
```json
{
  "contradiction_check": {
    "passed": true,
    "checked_against": ["chunk_uuid_1", "chunk_uuid_2"],
    "max_similarity": 0.65
  },
  "duplicate_check": {
    "passed": true,
    "checked_against": ["chunk_uuid_3"],
    "max_similarity": 0.78
  }
}
```

**Example**:
```json
{
  "chunk_id": "750e8400-e29b-41d4-a716-446655440002",
  "source_doc": "Software_Company_Docupedia_FILLED.pdf",
  "source_type": "pdf",
  "page_number": 42,
  "section_title": "Vacation and Paid Time Off",
  "related_topic": null,
  "validation_status": {
    "contradiction_check": {"passed": true, "checked_against": [], "max_similarity": null},
    "duplicate_check": {"passed": true, "checked_against": [], "max_similarity": null}
  },
  "embedding_model": "all-MiniLM-L6-v2",
  "embedding_model_version": "2.2.2"
}
```

---

### 5. Vector Database Entry

Represents a stored chunk with its embedding in ChromaDB.

**Attributes**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `id` | String | ChromaDB document ID | Auto-generated by ChromaDB |
| `embedding` | Array[Float] | 384-dimensional vector | Required, exactly 384 floats |
| `document` | String | Chunk text content | Required, min 100 chars |
| `metadata` | Object | Dictionary of metadata fields | Required, see Metadata Schema |
| `distance` | Float | Computed at query time | Non-negative, 0-2 range for cosine |

**Metadata Schema** (stored in ChromaDB):
```json
{
  "chunk_id": "string (UUID)",
  "document_id": "string (UUID)",
  "source_doc": "string",
  "source_type": "string (pdf|kaggle|huggingface)",
  "page_number": "integer",
  "section_title": "string",
  "chunk_index": "integer",
  "related_topic": "string",
  "timestamp": "string (ISO 8601)"
}
```

**Example** (ChromaDB format):
```json
{
  "id": "chunk_750e8400-e29b-41d4-a716-446655440002",
  "embedding": [0.023, -0.145, 0.891, ...],
  "document": "Employees are entitled to 15 days of paid vacation per year...",
  "metadata": {
    "chunk_id": "750e8400-e29b-41d4-a716-446655440002",
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_doc": "Software_Company_Docupedia_FILLED.pdf",
    "source_type": "pdf",
    "page_number": 42,
    "section_title": "Vacation and Paid Time Off",
    "chunk_index": 12,
    "related_topic": null,
    "timestamp": "2026-01-21T10:35:22Z"
  }
}
```

---

### 6. Data Manifest

Tracks all documents in the knowledge base for version control and reproducibility.

**Attributes**:

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `manifest_version` | String | Semantic version | Required, e.g., "1.0.0" |
| `generated_at` | DateTime | Manifest generation timestamp | ISO 8601 format |
| `total_documents` | Integer | Count of all documents | Non-negative |
| `total_chunks` | Integer | Count of all chunks | Non-negative |
| `total_size_bytes` | Integer | Total data directory size | Non-negative |
| `documents` | Array[Object] | List of document entries | See Document Entry schema |
| `configuration` | Object | Pipeline configuration snapshot | See Configuration schema |

**Document Entry Schema**:
```json
{
  "document_id": "string (UUID)",
  "filename": "string",
  "source_type": "string",
  "file_path": "string",
  "checksum": "string (SHA-256)",
  "ingestion_timestamp": "string (ISO 8601)",
  "chunk_count": "integer",
  "related_topics": "array[string]",
  "validation_results": {
    "contradictions_excluded": "integer",
    "duplicates_skipped": "integer"
  }
}
```

**Configuration Schema**:
```json
{
  "embedding_model": "string",
  "chunk_size": "integer",
  "chunk_overlap": "integer",
  "similarity_threshold_relevance": "float",
  "similarity_threshold_duplicate": "float",
  "vector_db_type": "string",
  "vector_db_path": "string"
}
```

**Example** (`data/manifest.json`):
```json
{
  "manifest_version": "1.0.0",
  "generated_at": "2026-01-21T10:45:00Z",
  "total_documents": 3,
  "total_chunks": 1247,
  "total_size_bytes": 52428800,
  "documents": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "Software_Company_Docupedia_FILLED.pdf",
      "source_type": "pdf",
      "file_path": "data/pdf/Software_Company_Docupedia_FILLED.pdf",
      "checksum": "a3b2c1d4e5f6...",
      "ingestion_timestamp": "2026-01-21T10:30:00Z",
      "chunk_count": 1050,
      "related_topics": [],
      "validation_results": {
        "contradictions_excluded": 0,
        "duplicates_skipped": 0
      }
    },
    {
      "document_id": "650e8400-e29b-41d4-a716-446655440003",
      "filename": "hr-benefits-guide.json",
      "source_type": "kaggle",
      "file_path": "data/kaggle/hr-benefits-guide.json",
      "checksum": "b4c3d2e1f0a9...",
      "ingestion_timestamp": "2026-01-21T10:40:00Z",
      "chunk_count": 150,
      "related_topics": ["vacation policy", "healthcare benefits"],
      "validation_results": {
        "contradictions_excluded": 3,
        "duplicates_skipped": 12
      }
    }
  ],
  "configuration": {
    "embedding_model": "all-MiniLM-L6-v2",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "similarity_threshold_relevance": 0.75,
    "similarity_threshold_duplicate": 0.85,
    "vector_db_type": "chromadb",
    "vector_db_path": "/app/vectordb_storage"
  }
}
```

---

## Relationships

### Entity Relationship Diagram

```
┌─────────────────┐
│   HR Document   │
│  (source file)  │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────▼────────┐
│ Document Chunk  │
│ (text segment)  │
└────────┬────────┘
         │ 1
         │
    ┌────┴────┐
    │ 1       │ 1
┌───▼──────┐ ┌▼──────────────┐
│  Chunk   │ │ Vector DB     │
│ Metadata │ │ Entry         │
│(citation)│ │(ChromaDB)     │
└──────────┘ └───────────────┘

┌─────────────────┐
│  PDF Topic      │
│ (extracted)     │
└────────┬────────┘
         │
         │ M:N
         │
┌────────▼────────┐
│  HR Document    │
│ (external only) │
└─────────────────┘

┌─────────────────┐
│ Data Manifest   │
│ (tracking)      │
└────────┬────────┘
         │
         │ references
         │
┌────────▼────────┐
│  HR Document    │
│ (all sources)   │
└─────────────────┘
```

### Relationship Descriptions

1. **HR Document → Document Chunk** (1:N)
   - One document produces many chunks
   - Cascade delete: If document deleted, remove all chunks

2. **Document Chunk → Chunk Metadata** (1:1)
   - Every chunk has exactly one metadata record
   - Cascade update: If chunk ID changes, update metadata FK

3. **Document Chunk → Vector Database Entry** (1:1)
   - Every chunk has exactly one vector DB entry
   - Synchronization: Chunk updates must propagate to ChromaDB

4. **PDF Topic → HR Document** (M:N)
   - One topic can relate to multiple external documents
   - One external document can address multiple topics
   - PDF source document has no topic relations (it defines topics)

5. **Data Manifest → HR Document** (1:N)
   - Manifest references all documents
   - Read-only: Manifest doesn't modify documents

---

## Validation Rules

### Document-Level Validation

| Rule | Validation Logic | Error Message |
|------|------------------|---------------|
| **VR-001** | `source_type ∈ {pdf, kaggle, huggingface}` | "Invalid source_type: must be pdf, kaggle, or huggingface" |
| **VR-002** | `file_path` starts with `data/` | "Invalid file_path: must start with data/" |
| **VR-003** | `checksum` is 64-character hex string | "Invalid checksum: must be SHA-256 hash (64 hex chars)" |
| **VR-004** | `page_count >= 0` | "Invalid page_count: must be non-negative" |
| **VR-005** | External sources must have `related_topics` non-empty | "External document must link to PDF topics" |

### Chunk-Level Validation

| Rule | Validation Logic | Error Message |
|------|------------------|---------------|
| **VR-101** | `100 <= token_count <= 512` | "Invalid token_count: must be 100-512" |
| **VR-102** | `len(embedding_vector) == 384` | "Invalid embedding: must be 384 dimensions" |
| **VR-103** | `chunk_index >= 0` | "Invalid chunk_index: must be non-negative" |
| **VR-104** | `text` length >= 100 characters | "Chunk too short: minimum 100 characters" |
| **VR-105** | All floats in `embedding_vector` are finite | "Invalid embedding: contains NaN or Inf" |

### Metadata Validation

| Rule | Validation Logic | Error Message |
|------|------------------|---------------|
| **VR-201** | `page_number > 0` for PDF source | "Invalid page_number: must be positive for PDF" |
| **VR-202** | `page_number == 0` for non-PDF source | "Invalid page_number: must be 0 for non-PDF" |
| **VR-203** | `related_topic` required if `source_type != pdf` | "Missing related_topic for external source" |
| **VR-204** | `validation_status.contradiction_check.passed == true` | "Chunk failed contradiction check" |
| **VR-205** | `validation_status.duplicate_check.passed == true` | "Chunk failed duplicate check" |

### Semantic Validation (FR-005, FR-006, FR-007)

| Rule | Validation Logic | Error Message |
|------|------------------|---------------|
| **VR-301** | External chunk similarity to PDF topic >= 0.75 | "Chunk not relevant: similarity {score} < 0.75" |
| **VR-302** | External chunk similarity to PDF chunks < 0.85 | "Chunk is duplicate: similarity {score} >= 0.85" |
| **VR-303** | External chunk has no contradictions with PDF | "Chunk contradicts PDF content at {location}" |

---

## State Transitions

### Document Ingestion Lifecycle

```
┌─────────────┐
│ Discovered  │  File found in data/ directory
└──────┬──────┘
       │
       │ Validate format, checksum
       ▼
┌─────────────┐
│  Validated  │  File passes basic checks
└──────┬──────┘
       │
       │ Extract text, detect sections
       ▼
┌─────────────┐
│   Chunked   │  Text split into chunks
└──────┬──────┘
       │
       │ Generate embeddings
       ▼
┌─────────────┐
│  Embedded   │  Embeddings computed
└──────┬──────┘
       │
       │ Store in ChromaDB
       ▼
┌─────────────┐
│   Stored    │  Ready for retrieval
└─────────────┘
```

### Chunk Validation Lifecycle (External Sources Only)

```
┌─────────────┐
│   Created   │  Chunk extracted from document
└──────┬──────┘
       │
       │ Check relevance to PDF topics
       ▼
┌─────────────┐
│  Relevance  │  Similarity >= 0.75
│   Check     │  If fail: REJECT
└──────┬──────┘
       │ PASS
       │
       │ Check for contradictions with PDF
       ▼
┌─────────────┐
│Contradiction│  No semantic conflicts
│   Check     │  If fail: REJECT
└──────┬──────┘
       │ PASS
       │
       │ Check for duplicates
       ▼
┌─────────────┐
│  Duplicate  │  Similarity < 0.85
│   Check     │  If fail: SKIP
└──────┬──────┘
       │ PASS
       │
       │ Store chunk
       ▼
┌─────────────┐
│  Ingested   │  Ready for retrieval
└─────────────┘
```

---

## Configuration

### Environment Variables (extend `app/core/config.py`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VECTOR_DB_TYPE` | String | `chromadb` | Vector database implementation |
| `VECTOR_DB_PATH` | String | `/app/vectordb_storage` | Database persistence path |
| `EMBEDDING_MODEL` | String | `all-MiniLM-L6-v2` | sentence-transformers model |
| `CHUNK_SIZE` | Integer | `512` | Maximum tokens per chunk |
| `CHUNK_OVERLAP` | Integer | `50` | Overlap tokens between chunks |
| `SIMILARITY_THRESHOLD_RELEVANCE` | Float | `0.75` | External data relevance cutoff |
| `SIMILARITY_THRESHOLD_DUPLICATE` | Float | `0.85` | Duplicate detection cutoff |
| `MIN_CHUNK_SIZE` | Integer | `100` | Minimum tokens per chunk |
| `CONTRADICTION_THRESHOLD` | Float | `0.3` | Low similarity → contradiction |
| `ALIGNMENT_THRESHOLD` | Float | `0.75` | High similarity → alignment |

---

## Performance Considerations

### Indexing Strategy

- **Primary Keys**: UUID for cross-reference safety (no auto-increment collisions)
- **Foreign Keys**: Indexed on `document_id`, `chunk_id` for join performance
- **ChromaDB**: HNSW index auto-built on `embedding` field

### Query Optimization

```python
# Efficient retrieval pattern
results = collection.query(
    query_embeddings=[embedding],
    n_results=5,
    where={"source_type": "pdf"},  # Filter by metadata
    include=['metadatas', 'documents', 'distances']
)
```

### Storage Estimates

- **Chunk**: ~2KB text + 1.5KB embedding + 0.5KB metadata = 4KB per chunk
- **1000 chunks**: ~4MB
- **10,000 chunks**: ~40MB
- **ChromaDB index overhead**: ~4x embedding size = 6KB per chunk

---

## Summary

**Entities**: 6 (HR Document, PDF Topic, Document Chunk, Chunk Metadata, Vector DB Entry, Data Manifest)  
**Relationships**: 5 (1:N, 1:1, M:N)  
**Validation Rules**: 15 (document: 5, chunk: 5, metadata: 5, semantic: 3)  
**State Machines**: 2 (document lifecycle, chunk validation)  

**Next Phase**: Generate contracts (JSON schemas) from this data model.
