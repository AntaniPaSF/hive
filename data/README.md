# HR Policy Data Directory

This directory contains HR policy documents organized by source.

## Directory Structure

- `pdf/` - Original PDF documents provided directly
- `kaggle/` - Documents sourced from Kaggle datasets
- `huggingface/` - Documents sourced from HuggingFace datasets
- `synthetic/` - Synthetically generated HR policy documents

## Adding Documents

### PDF Documents
Place your PDF files in the `pdf/` subdirectory. The ingestion script will:
1. Extract text content while preserving structure
2. Convert to markdown format
3. Generate chunks for vector database storage

### Usage
```bash
# Place your PDF here
data/pdf/your-hr-policy.pdf

# Run ingestion script (to be implemented)
python scripts/ingest_documents.py
```

## File Naming Convention

Use descriptive names that indicate the policy type:
- `employee-handbook-2026.pdf`
- `vacation-policy.pdf`
- `expense-reimbursement-policy.pdf`
- `remote-work-guidelines.pdf`

## Notes

- All files in this directory are version-controlled via git
- Maximum file size recommendation: <50MB per document
- Supported format: PDF (text-based, not scanned images)
- Documents should be in English for initial implementation
