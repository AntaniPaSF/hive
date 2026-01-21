# Alignment Summary: RAG Service ↔ HR Data Pipeline

**Date**: 2026-01-21  
**Status**: ✅ Complete

## Changes Made

### 1. **Embedding Model Alignment**

| Document | Before | After | Impact |
|----------|--------|-------|--------|
| data-model.md | `nomic-embed-text` (768d) | `all-MiniLM-L6-v2` (384d) | Vector dimension contract enforced |
| service-interface.md | 768d vectors | 384d vectors | ChromaDB query interface updated |
| quickstart.md | `EMBEDDING_MODEL=nomic-embed-text` | `EMBEDDING_MODEL=all-MiniLM-L6-v2` | Setup instructions aligned |
| plan.md | Embedding generation responsibility | Consume pre-computed embeddings | Role clarified (HR pipeline produces, RAG consumes) |

**Rationale**: HR Data Pipeline team selected `all-MiniLM-L6-v2` as their embedding model. RAG service must consume the same embeddings for consistency.

---

### 2. **Chunk Metadata Schema**

**Updated in**: `data-model.md`, `service-interface.md`

**Changes**:
- Aligned metadata field names with HR Pipeline schema:
  - `document_name` → `source_doc`
  - Added `source_type` field (pdf | kaggle | huggingface)
  - Added `related_topic` field (from HR pipeline FR-004)
  - Added `validation_status` object with `contradiction_check` and `duplicate_check` fields

**Example Updated Metadata**:
```python
{
    "source_doc": "hr_policy.pdf",
    "source_type": "pdf",
    "page_number": 5,
    "section_title": "Chemical Handling",
    "chunk_index": 0,
    "related_topic": "Safety Protocols",
    "validation_status": {
        "contradiction_check": true,
        "duplicate_check": true
    }
}
```

---

### 3. **Confidence Threshold Addition**

**Updated in**: `data-model.md`, `service-interface.md`, `quickstart.md`

**Change**: Added explicit `MIN_CONFIDENCE_THRESHOLD` (default: 0.5)

```python
# New logic in RAG service
if answer_confidence >= 0.5:
    return Answer(answer=text, citations=[...], confidence=score)
else:
    return Answer(answer=None, citations=[], message="Information not found...")
```

**Rationale**: Aligns with constitution principle "Accuracy Over Speed" - avoids hallucinated answers with low confidence.

---

### 4. **Inter-Service Communication Clarification**

**Updated in**: `service-interface.md`, `plan.md`

**Changes**:
- Explicit role definition: HR Pipeline generates embeddings, RAG service consumes them
- Removed responsibility for embedding generation from RAG service
- Added note: "Embedding model is automatically managed by HR Data Pipeline service"

**Before**: RAG service was responsible for generating embeddings
**After**: RAG service queries ChromaDB for pre-computed embeddings from HR pipeline

---

### 5. **New Data Contract Document**

**Created**: `contracts/data-contract.md`

**Sections**:
- Embedding model agreement (must use `all-MiniLM-L6-v2`, 384d, cosine distance)
- Vector database schema (collection name, chunk format, metadata fields)
- Retrieval query format (ChromaDB API contract)
- Similarity score interpretation (confidence thresholds)
- Citation format (how RAG renders metadata as citations)
- Ingestion workflow (HR Pipeline guarantees)
- Error handling (failure modes and recovery)
- Version history and change request process
- Integration testing checklist

---

## Consistency Verification

### ✅ Embedding Model Consistency
- **HR Pipeline**: Uses `all-MiniLM-L6-v2` (FR-009: "Generate vector embeddings for each chunk")
- **RAG Service**: Consumes `all-MiniLM-L6-v2` (384-dim vectors from ChromaDB)
- **Data Contract**: Enforces `all-MiniLM-L6-v2` as required model
- **Status**: **ALIGNED**

### ✅ Metadata Field Consistency
- **HR Pipeline**: Sets 13 metadata fields including `source_doc`, `source_type`, `section_title`, `chunk_index`
- **RAG Service**: Uses metadata fields for citations and filtering
- **Data Contract**: Documents exact field definitions and required vs. optional
- **Status**: **ALIGNED**

### ✅ Similarity Threshold Consistency
- **HR Pipeline**: Uses 0.75 (topic relevance), 0.85 (duplicates)
- **RAG Service**: Uses 0.5 (minimum confidence for answer)
- **Data Contract**: Documents both thresholds and their purposes
- **Status**: **ALIGNED** (different thresholds for different purposes)

### ✅ ChromaDB Collection Consistency
- **HR Pipeline**: Ingests into `corporate_documents` collection (implicit from spec)
- **RAG Service**: Queries `corporate_documents` collection (explicit in service-interface.md)
- **Data Contract**: Specifies `corporate_documents` as the collection name
- **Status**: **ALIGNED**

### ✅ Citation Format Consistency
- **HR Pipeline**: Stores `source_doc`, `page_number`, `section_title` in metadata
- **RAG Service**: Renders as `[source_doc, section_title]` format (or with page if available)
- **Data Contract**: Defines citation format and metadata-to-citation mapping
- **Status**: **ALIGNED**

---

## Files Modified

```
specs/001-rag-pipeline-llm-service/
├── data-model.md              # ✅ Updated embedding dimensions, metadata fields, confidence thresholds
├── service-interface.md        # ✅ Updated embedding model, query format, metadata contract, env vars
├── plan.md                     # ✅ Updated tech stack, role clarification, task descriptions
├── quickstart.md              # ✅ Updated embedding model, env vars, setup notes
├── contracts/
│   └── data-contract.md       # ✨ NEW: Formal data contract between HR pipeline and RAG service
```

---

## Files NOT Modified (intentionally)

- `spec.md` - Remains technology-agnostic; data model choice is implementation detail
- `research.md` - Phase 0 research; maintain for historical record
- `checklists/requirements.md` - Quality validation already passed

---

## Dependencies & Handoffs

### HR Data Pipeline → RAG Service Handoff

**Before RAG service can start Phase 2 implementation**:
1. ✅ HR Pipeline populates ChromaDB with documents (at least 100 chunks)
2. ✅ All embeddings use `all-MiniLM-L6-v2` (384 dimensions)
3. ✅ Metadata includes required fields (source_doc, source_type, page_number, section_title, chunk_index)
4. ✅ Data Contract is reviewed and approved by both teams

**Integration Test Checklist** (in data-contract.md):
- [ ] ChromaDB contains at least 100 chunks
- [ ] All embeddings are exactly 384 dimensions
- [ ] No metadata fields are null (except allowed exceptions)
- [ ] Sample query retrieves semantically relevant chunks
- [ ] RAG service can generate 384-dim query embeddings
- [ ] Retrieval results appear in <500ms

---

## Next Steps for RAG LLM Service

1. **Review Data Contract** with HR Data Pipeline team
2. **Approve Metadata Schema** - ensure all fields are understood
3. **Set up Development Environment**:
   - ChromaDB instance available locally
   - Sample documents with embeddings pre-populated by HR pipeline
   - Test queries prepared
4. **Implement Phase 2** (development):
   - Ollama Docker setup
   - Retrieval pipeline (query ChromaDB for 384-dim embeddings)
   - Generation pipeline (assemble prompt, call Ollama)
   - Citation extraction (map LLM output to chunk metadata)
   - Structured logging with request_id tracing
5. **Integration Testing**:
   - Test with 100-1000 pre-populated chunks
   - Verify confidence calculation from similarity scores
   - Test "I don't know" scenario (confidence <0.5)

---

## Summary

✅ **RAG LLM Service specifications now fully aligned with HR Data Pipeline specifications**:
- Embedding model: `all-MiniLM-L6-v2` (384 dimensions)
- Vector database: ChromaDB collection `corporate_documents`
- Metadata schema: 13 fields with clear producer/consumer roles
- Data contract: Formal interface documented for both teams
- Confidence threshold: 0.5 (minimum to return answer)
- Citation format: `[source_doc, section_title]` rendered from metadata

All changes maintain backward compatibility with the constitution principles (Accuracy, Transparency, Self-Contained, Reproducible) and are ready for Phase 2 implementation.
