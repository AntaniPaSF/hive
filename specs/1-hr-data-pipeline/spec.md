# Feature Specification: HR Data Pipeline & Knowledge Base

**Feature Branch**: `1-hr-data-pipeline`  
**Created**: January 21, 2026  
**Status**: Draft  
**Input**: User description: "Create ingestion pipeline for provided HR policy PDF (docs → embeddings → vector DB), augment with relevant Kaggle/HuggingFace data aligned to PDF topics without contradictions or duplicates, chunk documents for optimal retrieval, version control knowledge base."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initial Data Ingestion from PDF (Priority: P1)

A data engineer needs to ingest the provided HR policy PDF document into the system, converting it into searchable chunks stored in a vector database for RAG retrieval.

**Why this priority**: This is the foundational capability - without data ingestion, no other RAG functionality can work. Directly impacts Accuracy (quality data source) and Self-Contained (data in repo) principles.

**Independent Test**: Can be fully tested by running the ingestion script on the provided PDF and verifying that chunks appear in the vector database with proper embeddings and metadata.

**Acceptance Scenarios**:

1. **Given** a PDF HR policy document exists, **When** the ingestion script is executed, **Then** the PDF is parsed into text chunks and stored in the `/data` folder in markdown format
2. **Given** text chunks exist in `/data` folder, **When** the embedding process runs, **Then** each chunk is converted to vector embeddings and stored in the vector database
3. **Given** chunks are in the vector database, **When** querying for a specific HR topic, **Then** relevant chunks are retrieved based on semantic similarity

---

### User Story 2 - Augment with External HR Data (Priority: P2)

A data engineer needs to enrich the knowledge base by sourcing relevant HR policy information from Kaggle/HuggingFace datasets that complement the PDF content without creating contradictions or semantic duplicates.

**Why this priority**: Expands knowledge coverage while maintaining Accuracy - the PDF document serves as the authoritative source and external data must align with it. Supports comprehensive answers without compromising correctness.

**Independent Test**: Can be tested by comparing external data chunks against PDF topics, verifying semantic similarity for relevance and detecting contradictions or duplicates before ingestion.

**Acceptance Scenarios**:

1. **Given** PDF document is ingested and topic extraction is complete, **When** sourcing external data, **Then** only documents matching PDF topics (via semantic similarity >0.75) are retrieved from Kaggle/HuggingFace
2. **Given** external document is retrieved, **When** checking for contradictions, **Then** any content that contradicts PDF policy statements is flagged and excluded from ingestion
3. **Given** external document passes contradiction check, **When** checking for duplicates, **Then** chunks with semantic similarity >0.85 to existing PDF chunks are marked as duplicates and skipped
4. **Given** external data passes all validation, **When** ingesting to vector database, **Then** chunks are labeled with source metadata (kaggle/huggingface) and linked to related PDF topics

---

### User Story 3 - Chunking Strategy Optimization (Priority: P2)

A data engineer needs to chunk documents into optimal sizes for retrieval, balancing context preservation with retrieval precision.

**Why this priority**: Directly impacts RAG Accuracy - poor chunking leads to irrelevant or incomplete answers. Must be implemented before production use.

**Independent Test**: Can be tested by comparing retrieval results using different chunk sizes (e.g., 256, 512, 1024 tokens) and measuring relevance scores.

**Acceptance Scenarios**:

1. **Given** a document with multiple HR policies, **When** chunking with semantic boundaries (section headers), **Then** each chunk contains complete policy information without mid-sentence cuts
2. **Given** chunks of varying sizes, **When** testing retrieval quality, **Then** chunk size can be adjusted via configuration parameter
3. **Given** overlapping context needs, **When** chunking is applied, **Then** chunks include configurable overlap (e.g., 50 tokens) to preserve context

---

### User Story 4 - Version Control for Knowledge Base (Priority: P3)

A data engineer needs to track changes to the knowledge base over time, including document additions, updates, and deletions.

**Why this priority**: Supports Reproducibility principle by allowing rollback to previous knowledge base states. Important for audit trails but not blocking for initial MVP.

**Independent Test**: Can be tested by making changes to `/data` folder, committing to git, and verifying that previous versions can be checked out.

**Acceptance Scenarios**:

1. **Given** documents in `/data` folder, **When** changes are committed to git, **Then** commit messages include document count, additions, and modifications
2. **Given** a vector database state, **When** exporting database metadata, **Then** a manifest file records document hashes, chunk counts, and embedding model version
3. **Given** a need to rollback, **When** checking out a previous git commit, **Then** the ingestion script can rebuild the vector database from that historical state

---

### Edge Cases

- What happens when the PDF document is corrupted or unreadable?
- How does the system handle non-English HR documents or mixed-language content?
- What happens when the vector database storage limit is reached?
- What happens when external data directly contradicts PDF content?
- How does the system handle edge cases where external data is partially contradictory (e.g., different policy effective dates)?
- What happens when no relevant external data is found for a PDF topic?
- What happens when documents contain tables, images, or complex formatting?
- How does the system handle extremely large documents (>1000 pages)?
- What happens when semantic similarity scores are borderline (e.g., 0.74 for relevance, 0.84 for duplicates)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept PDF documents as input and extract text content while preserving structural information (headings, sections)
- **FR-002**: System MUST store extracted document content in markdown format within the `/data` folder in the git repository
- **FR-003**: System MUST organize data by source with subdirectories: `/data/pdf/` for the authoritative HR policy document, `/data/kaggle/` for Kaggle-sourced documents, `/data/huggingface/` for HuggingFace-sourced documents
- **FR-004**: System MUST extract topics from the PDF document to guide external data sourcing (e.g., vacation policy, expense reimbursement, remote work guidelines)
- **FR-005**: System MUST retrieve external documents from Kaggle/HuggingFace only when semantic similarity to PDF topics exceeds 0.75 threshold
- **FR-006**: System MUST detect contradictions between external content and PDF content using semantic analysis and exclude contradictory information
- **FR-007**: System MUST identify semantic duplicates between external chunks and PDF chunks using similarity threshold of 0.85 and skip duplicate ingestion
- **FR-008**: System MUST chunk documents into retrievable segments with configurable size (default 512 tokens) and overlap (default 50 tokens)
- **FR-009**: System MUST generate vector embeddings for each chunk using a specified embedding model
- **FR-010**: System MUST store chunks and embeddings in a vector database (ChromaDB or Qdrant)
- **FR-011**: System MUST include metadata with each chunk: source document, source type (pdf/kaggle/huggingface), page number, section title, chunk index, timestamp, related PDF topic
- **FR-012**: System MUST provide a data ingestion script that processes the PDF first, then external sources with validation
- **FR-013**: System MUST support incremental ingestion (only process new or modified documents)
- **FR-014**: System MUST validate document content before ingestion (file readability, format validation, encoding check, contradiction detection, duplicate detection)
- **FR-015**: System MUST export a data schema document defining chunk structure, metadata fields, embedding dimensions, and validation rules for use by RAG engineers
- **FR-016**: System MUST log all ingestion operations including success/failure status, processing time, validation results (contradictions found, duplicates skipped), and error details
- **FR-017**: System MUST maintain a manifest file in `/data` listing all ingested documents with checksums, ingestion timestamps, source type, and related PDF topics
- **FR-018**: System MUST handle errors gracefully (skip corrupted files, continue processing remaining documents)
- **FR-019**: System MUST preserve document versioning through git commits with descriptive commit messages including validation statistics

### Key Entities

- **HR Document**: Represents an HR policy document (PDF or external source). Key attributes: filename, source (pdf/kaggle/huggingface), file size, page count, language, last modified date, checksum, related PDF topics.

- **Document Chunk**: Represents a segment of text from an HR document optimized for retrieval. Key attributes: chunk text content, chunk index within document, token count, overlap tokens, embedding vector (dimensions based on model), source type.

- **Chunk Metadata**: Information associated with each chunk for retrieval context. Key attributes: source document reference, source type (pdf/kaggle/huggingface), page number(s), section title/heading, creation timestamp, embedding model name/version, related PDF topic, validation status (passed contradiction check, duplicate check).

- **Vector Database Entry**: Represents a stored chunk with its embedding. Key attributes: unique chunk ID, embedding vector, metadata dictionary, similarity scores (computed at query time), source hierarchy (pdf=authoritative, external=supplementary).

- **Data Manifest**: Tracks all documents in the knowledge base. Key attributes: document path, source type, checksum (SHA-256), ingestion timestamp, chunk count, related PDF topics, validation results, total database size.

- **PDF Topic**: Represents a major topic extracted from the PDF document. Key attributes: topic name, section reference, keywords, external document count (how many external chunks relate to this topic).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Data engineer can ingest the provided PDF document and verify at least 90% of text content is successfully extracted and chunked within 5 minutes
- **SC-002**: Vector database contains searchable chunks that return semantically relevant results for HR policy queries with similarity scores above 0.7
- **SC-003**: The `/data/pdf/` folder contains the provided HR policy document in markdown format with proper structure preservation
- **SC-004**: External data augmentation successfully retrieves and validates documents from Kaggle/HuggingFace with 100% contradiction detection (no contradictory content ingested)
- **SC-005**: Duplicate detection identifies and skips at least 95% of semantically identical chunks from external sources
- **SC-006**: Data ingestion script processes 100 document pages in under 10 minutes on standard hardware
- **SC-007**: Data schema document is provided to RAG engineers containing complete field definitions, data types, validation rules, and example queries
- **SC-008**: Knowledge base can be fully reconstructed from git repository contents (documents + ingestion script) without external dependencies on data sources
- **SC-009**: Chunk retrieval returns results in under 500ms for 95% of queries against a database of 1000+ chunks
- **SC-010**: Zero data loss during ingestion - all source documents are preserved in `/data` folder with matching checksums
- **SC-011**: Ingestion logs clearly show validation statistics: X external chunks retrieved, Y contradictions excluded, Z duplicates skipped

## Assumptions

- The provided PDF document is in English and contains HR policy text (not scanned images requiring OCR)
- The PDF document is the authoritative source - external data must align with it, not replace or contradict it
- Semantic similarity threshold of 0.75 for topic relevance and 0.85 for duplicate detection are appropriate starting points (adjustable based on testing)
- Standard embedding models (e.g., sentence-transformers) are sufficient for similarity calculations
- ChromaDB or Qdrant vector database can be run locally for development without cloud infrastructure
- Kaggle and HuggingFace datasets contain relevant HR policy documents in English
- Git repository has sufficient storage for `/data` folder (assuming <1GB for PDF + external documents)
- Documents do not contain sensitive personal information requiring encryption or special handling
- Chunk size of 512 tokens provides good balance between context and precision (can be adjusted based on testing)
- Overlap of 50 tokens is sufficient to preserve context across chunk boundaries
- Contradiction detection can be performed using semantic analysis comparing policy statements

## Dependencies

- Git repository must be initialized and accessible for version control
- Python environment with package installation capabilities
- PDF parsing library (e.g., PyPDF2, pdfplumber) for text extraction
- Vector database (ChromaDB or Qdrant) installation and setup
- Embedding model library (e.g., sentence-transformers) for semantic similarity calculations
- Kaggle API access for dataset retrieval (requires API key)
- HuggingFace datasets library for document retrieval
- Sufficient disk space for `/data` folder and vector database storage

## Out of Scope

- Generating synthetic HR policy documents (focus on real data only)
- Real-time document ingestion or monitoring of external sources
- User interface for document upload or management
- Document access controls or permission management
- Multi-language translation or support
- OCR for scanned document images
- Custom embedding model training or fine-tuning
- Cloud deployment or distributed vector database setup
- Query interface or RAG application (handled by RAG Engineer)
- Document classification or automatic tagging
- Duplicate detection across semantically similar documents
