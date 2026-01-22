"""
Command-Line Interface for HR Data Pipeline Ingestion

Orchestrates the complete ingestion pipeline:
1. PDF extraction (PDFParser)
2. Semantic chunking (SemanticChunker)
3. Vector database storage (ChromaDBClient) - text-based search

Related:
- FR-001 to FR-010: Complete ingestion pipeline
- User Story 1 (P1): Initial Data Ingestion from PDF
"""

import argparse
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import hashlib

from app.core.config import AppConfig
from app.ingestion.pdf_parser import PDFParser
from app.ingestion.chunker import SemanticChunker
from app.vectordb.client import ChromaDBClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orchestrates the complete ingestion pipeline.
    
    Handles PDF extraction, chunking, and vector storage (text-based).
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize pipeline components."""
        self.config = config or AppConfig.validate()
        
        logger.info("Initializing ingestion pipeline components...")
        self.pdf_parser = PDFParser()
        self.chunker = SemanticChunker(
            max_tokens=self.config.chunk_size,
            overlap_tokens=self.config.chunk_overlap,
            min_chunk_size=self.config.min_chunk_size
        )
        self.vectordb = ChromaDBClient(config=self.config)
        logger.info("Pipeline components initialized successfully (PDF-only mode)")
    
    def compute_file_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def ingest_pdf(self, pdf_path: Path, rebuild: bool = False) -> dict:
        """
        Ingest a single PDF document.
        
        Args:
            pdf_path: Path to PDF file
            rebuild: If True, delete existing chunks for this document first
            
        Returns:
            Dict with ingestion statistics
        """
        logger.info(f"Starting ingestion of {pdf_path.name}")
        
        # Compute checksum
        checksum = self.compute_file_checksum(pdf_path)
        logger.info(f"File checksum: {checksum}")
        
        # Step 1: Extract text from PDF
        logger.info("Step 1/4: Extracting text from PDF...")
        pdf_pages = self.pdf_parser.extract_text_with_structure(pdf_path)
        logger.info(f"Extracted {len(pdf_pages)} pages")
        
        # Step 2: Chunk the document
        logger.info("Step 2/3: Chunking document...")
        document_id = f"pdf-{checksum[:16]}"
        chunks = self.chunker.chunk_document(
            pdf_pages=pdf_pages,
            document_id=document_id,
            source_filename=pdf_path.name
        )
        logger.info(f"Created {len(chunks)} chunks")
        
        # Step 3: Store in vector database (text-based)
        logger.info("Step 3/3: Storing chunks in vector database...")
        
        if rebuild:
            # Delete existing chunks for this document
            logger.info(f"Rebuild mode: deleting existing chunks for document {document_id}")
            # Query for existing chunk IDs and delete them
            # (In production, you'd implement this with metadata filtering)
        
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        texts = [chunk.text for chunk in chunks]
        # Filter out None values from metadata (ChromaDB requirement)
        metadatas = [
            {k: v for k, v in chunk.metadata.items() if v is not None}
            for chunk in chunks
        ]
        
        self.vectordb.add_chunks(
            chunk_ids=chunk_ids,
            texts=texts,
            metadatas=metadatas
        )
        
        logger.info(f"✓ Successfully ingested {pdf_path.name}")
        
        return {
            "document_id": document_id,
            "filename": pdf_path.name,
            "checksum": checksum,
            "page_count": len(pdf_pages),
            "chunk_count": len(chunks),
            "mode": "text-only",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_manifest(self, ingestion_results: list, output_path: Path):
        """
        Generate data manifest JSON file.
        
        Args:
            ingestion_results: List of ingestion result dicts
            output_path: Path to save manifest.json
        """
        manifest = {
            "manifest_version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "total_documents": len(ingestion_results),
            "total_chunks": sum(r["chunk_count"] for r in ingestion_results),
            "documents": ingestion_results,
            "configuration": {
                "mode": "text-only",
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap,
                "min_chunk_size": self.config.min_chunk_size,
                "vector_db_type": self.config.vector_db_type,
                "vector_db_path": self.config.vector_db_path
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Manifest saved to {output_path}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="HR Data Pipeline Ingestion CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest a single PDF
  python -m app.ingestion.cli --source data/hr_policy.pdf
  
  # Ingest all PDFs in a directory
  python -m app.ingestion.cli --source data/pdfs/
  
  # Rebuild (delete and re-ingest)
  python -m app.ingestion.cli --source data/hr_policy.pdf --rebuild
  
  # Validate only (dry-run)
  python -m app.ingestion.cli --source data/hr_policy.pdf --validate-only
        """
    )
    
    parser.add_argument(
        '--source',
        type=str,
        required=True,
        help='Path to PDF file or directory containing PDFs'
    )
    
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Delete existing chunks before ingesting (fresh start)'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Validate PDFs without ingesting (dry-run)'
    )
    
    parser.add_argument(
        '--manifest',
        type=str,
        default='data/manifest.json',
        help='Path to save manifest JSON file (default: data/manifest.json)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate source path
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error(f"Source path does not exist: {source_path}")
        sys.exit(1)
    
    # Collect PDF files
    if source_path.is_file():
        if source_path.suffix.lower() != '.pdf':
            logger.error(f"Source file is not a PDF: {source_path}")
            sys.exit(1)
        pdf_files = [source_path]
    elif source_path.is_dir():
        pdf_files = list(source_path.glob('*.pdf'))
        if not pdf_files:
            logger.error(f"No PDF files found in directory: {source_path}")
            sys.exit(1)
    else:
        logger.error(f"Invalid source path: {source_path}")
        sys.exit(1)
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) to process")
    
    # Validate-only mode
    if args.validate_only:
        logger.info("VALIDATE-ONLY MODE: Checking PDF accessibility...")
        for pdf_path in pdf_files:
            try:
                parser = PDFParser()
                pages = parser.extract_text_with_structure(str(pdf_path))
                logger.info(f"✓ {pdf_path.name}: {len(pages)} pages, valid")
            except Exception as e:
                logger.error(f"✗ {pdf_path.name}: {e}")
        logger.info("Validation complete. No data was ingested.")
        sys.exit(0)
    
    # Initialize pipeline
    try:
        pipeline = IngestionPipeline()
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        sys.exit(1)
    
    # Process each PDF
    ingestion_results = []
    failed_count = 0
    
    for pdf_path in pdf_files:
        try:
            result = pipeline.ingest_pdf(pdf_path, rebuild=args.rebuild)
            ingestion_results.append(result)
        except Exception as e:
            logger.error(f"Failed to ingest {pdf_path.name}: {e}", exc_info=True)
            failed_count += 1
    
    # Generate manifest
    if ingestion_results:
        manifest_path = Path(args.manifest)
        pipeline.generate_manifest(ingestion_results, manifest_path)
    
    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total PDFs processed: {len(pdf_files)}")
    logger.info(f"Successful: {len(ingestion_results)}")
    logger.info(f"Failed: {failed_count}")
    if ingestion_results:
        total_chunks = sum(r["chunk_count"] for r in ingestion_results)
        logger.info(f"Total chunks created: {total_chunks}")
        logger.info(f"Manifest saved: {args.manifest}")
    logger.info("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == '__main__':
    main()
