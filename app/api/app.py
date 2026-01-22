"""
FastAPI Application

Main API application with endpoints for document ingestion, search, and Q&A.

Related: Phase 2 (P2), Task 2.3 - API Layer
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.models import (
    QueryRequest,
    QueryResponse,
    CitationResponse,
    IngestRequest,
    IngestResponse,
    DocumentListResponse,
    ChunksResponse,
    ChunkInfo,
    HealthResponse,
    ErrorResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem
)
from app.rag.pipeline import RAGPipeline, LLMProvider
from app.query.retriever import Retriever
from app.ingestion.cli import IngestionPipeline
from app.vectordb.client import ChromaDBClient
from app.core.config import AppConfig

logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
rag_pipeline: Optional[RAGPipeline] = None
retriever: Optional[Retriever] = None
config: Optional[AppConfig] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global rag_pipeline, retriever, config
    
    logger.info("Starting up API application...")
    
    # Initialize components
    config = AppConfig.validate()
    retriever = Retriever(config=config)
    rag_pipeline = RAGPipeline(provider=LLMProvider.MOCK, config=config)
    
    logger.info("API application ready")
    
    yield
    
    logger.info("Shutting down API application...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="HR Data Pipeline API",
        description="API for document ingestion, search, and question answering",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "detail": str(exc),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    # Health check endpoint
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Health check",
        description="Check API and component health status"
    )
    async def health_check():
        """Health check endpoint."""
        try:
            # Check database
            db_config = config if config else AppConfig.validate()
            db_client = ChromaDBClient(config=db_config)
            chunk_count = db_client.count()
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            db_status = f"unhealthy: {str(e)}"
            chunk_count = 0
        
        return HealthResponse(
            status="healthy" if db_status == "healthy" else "degraded",
            version="1.0.0",
            database=db_status,
            timestamp=datetime.utcnow().isoformat(),
            components={
                "retriever": "healthy" if retriever else "not initialized",
                "rag_pipeline": "healthy" if rag_pipeline else "not initialized",
                "vector_db": db_status,
                "chunks_available": str(chunk_count)
            }
        )
    
    # Query endpoint (RAG)
    @app.post(
        "/query",
        response_model=QueryResponse,
        tags=["Question Answering"],
        summary="Ask a question",
        description="Ask a question about the documents and get an answer with citations",
        status_code=status.HTTP_200_OK
    )
    async def query(request: QueryRequest):
        """
        Ask a question and get an answer with citations.
        
        This endpoint uses RAG (Retrieval-Augmented Generation) to:
        1. Search for relevant document chunks
        2. Build context from retrieved chunks
        3. Generate answer using LLM
        4. Return answer with source citations
        """
        try:
            logger.info(f"Query request: '{request.question}' (provider={request.provider})")
            
            # Create pipeline with requested provider
            provider = LLMProvider(request.provider)
            pipeline = RAGPipeline(
                provider=provider,
                model_name=request.model,
                config=config
            )
            
            # Ask question
            response = pipeline.ask(
                question=request.question,
                top_k=request.top_k,
                filters=request.filters,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            # Convert to API response
            citations = [
                CitationResponse(
                    source_doc=c.source_doc,
                    page_number=c.page_number,
                    section_title=c.section_title,
                    relevance_score=c.relevance_score,
                    text_excerpt=c.text_excerpt
                )
                for c in response.citations
            ]
            
            page_range = response.get_page_range()
            
            return QueryResponse(
                question=response.question,
                answer=response.answer,
                citations=citations,
                model=response.model,
                tokens_used=response.tokens_used,
                sources=response.get_unique_sources(),
                page_range=list(page_range) if page_range[0] > 0 else None,
                generated_at=response.generated_at
            )
            
        except ValueError as e:
            logger.error(f"Invalid provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider: {request.provider}"
            )
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query processing failed: {str(e)}"
            )
    
    # Search endpoint (retrieval only)
    @app.post(
        "/search",
        response_model=SearchResponse,
        tags=["Search"],
        summary="Search documents",
        description="Search for relevant document chunks without LLM generation",
        status_code=status.HTTP_200_OK
    )
    async def search(request: SearchRequest):
        """
        Search for relevant document chunks.
        
        This endpoint performs retrieval only (no LLM generation).
        Useful for testing retrieval quality or building custom workflows.
        """
        try:
            logger.info(f"Search request: '{request.query}' (top_k={request.top_k})")
            
            # Initialize retriever if not available (for testing)
            search_retriever = retriever if retriever else Retriever(config=config)
            
            # Search using retriever
            result = search_retriever.search(
                query=request.query,
                top_k=request.top_k,
                filters=request.filters,
                min_score=request.min_score
            )
            
            # Convert to API response
            results = [
                SearchResultItem(
                    chunk_id=r.chunk_id,
                    text=r.text,
                    score=r.score,
                    source_doc=r.source_doc or "unknown",
                    page_number=r.page_number or 0,
                    section_title=r.section_title,
                    metadata=r.metadata
                )
                for r in result.results
            ]
            
            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results),
                retrieved_at=result.retrieved_at
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(e)}"
            )
    
    # Ingest endpoint
    @app.post(
        "/ingest",
        response_model=IngestResponse,
        tags=["Ingestion"],
        summary="Ingest documents",
        description="Ingest PDF document(s) into the vector database",
        status_code=status.HTTP_200_OK
    )
    async def ingest(request: IngestRequest):
        """
        Ingest PDF document(s) into the vector database.
        
        Processes PDF files and stores semantic chunks in ChromaDB.
        """
        try:
            logger.info(f"Ingest request: '{request.file_path}' (batch={request.batch})")
            
            file_path = Path(request.file_path)
            
            # Validate path
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File or directory not found: {request.file_path}"
                )
            
            # Initialize pipeline
            pipeline = IngestionPipeline(config=config)
            
            start_time = time.time()
            errors = []
            docs_processed = 0
            chunks_created = 0
            
            # Process
            if request.batch and file_path.is_dir():
                # Batch ingestion
                pdf_files = list(file_path.glob("*.pdf"))
                
                for pdf_file in pdf_files:
                    try:
                        result = pipeline.ingest_pdf(pdf_file)
                        docs_processed += 1
                        chunks_created += result.get('chunks_created', 0)
                    except Exception as e:
                        logger.error(f"Failed to ingest {pdf_file}: {e}")
                        errors.append(f"{pdf_file.name}: {str(e)}")
            else:
                # Single file ingestion
                if not file_path.is_file():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not a file: {request.file_path}"
                    )
                
                result = pipeline.ingest_pdf(file_path)
                docs_processed = 1
                chunks_created = result.get('chunks_created', 0)
            
            processing_time = time.time() - start_time
            
            return IngestResponse(
                status="success" if not errors else "partial_success",
                message=f"Processed {docs_processed} document(s), created {chunks_created} chunks",
                documents_processed=docs_processed,
                chunks_created=chunks_created,
                processing_time=processing_time,
                errors=errors
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ingestion failed: {str(e)}"
            )
    
    # List documents endpoint
    @app.get(
        "/documents",
        response_model=DocumentListResponse,
        tags=["Documents"],
        summary="List documents",
        description="List all ingested documents with metadata",
        status_code=status.HTTP_200_OK
    )
    async def list_documents():
        """
        List all ingested documents.
        
        Returns metadata about each document including chunk count, page count, etc.
        """
        try:
            logger.info("List documents request")
            
            # Get all chunks
            docs_config = config if config else AppConfig.validate()
            db_client = ChromaDBClient(config=docs_config)
            collection = db_client.get_or_create_collection()
            
            # Get all documents metadatas
            all_data = collection.get(include=["metadatas"])
            
            if not all_data or not all_data.get("metadatas"):
                return DocumentListResponse(documents=[], total_count=0)
            
            # Group by document_id
            doc_map = {}
            for metadata in all_data["metadatas"]:
                doc_id = metadata.get("document_id")
                if not doc_id:
                    continue
                
                if doc_id not in doc_map:
                    doc_map[doc_id] = {
                        "document_id": doc_id,
                        "filename": metadata.get("source_filename", "unknown"),
                        "chunk_count": 0,
                        "total_tokens": 0,
                        "pages": set(),
                        "ingested_at": metadata.get("timestamp", "unknown")
                    }
                
                doc_map[doc_id]["chunk_count"] += 1
                doc_map[doc_id]["total_tokens"] += metadata.get("token_count", 0)
                if metadata.get("page_number"):
                    doc_map[doc_id]["pages"].add(metadata["page_number"])
            
            # Convert to response format
            from app.api.models import DocumentInfo
            documents = [
                DocumentInfo(
                    document_id=doc["document_id"],
                    filename=doc["filename"],
                    chunk_count=doc["chunk_count"],
                    total_tokens=doc["total_tokens"],
                    page_count=len(doc["pages"]),
                    ingested_at=doc["ingested_at"]
                )
                for doc in doc_map.values()
            ]
            
            return DocumentListResponse(
                documents=documents,
                total_count=len(documents)
            )
            
        except Exception as e:
            logger.error(f"List documents failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list documents: {str(e)}"
            )
    
    # Get document chunks endpoint
    @app.get(
        "/documents/{document_id}/chunks",
        response_model=ChunksResponse,
        tags=["Documents"],
        summary="Get document chunks",
        description="Get all chunks for a specific document",
        status_code=status.HTTP_200_OK
    )
    async def get_document_chunks(document_id: str):
        """
        Get all chunks for a specific document.
        
        Returns all chunks with their content and metadata.
        """
        try:
            logger.info(f"Get chunks request for document: {document_id}")
            
            # Initialize retriever if not available (for testing)
            chunks_retriever = retriever if retriever else Retriever(config=config)
            
            # Get chunks for document
            chunks = chunks_retriever.get_document_chunks(document_id=document_id)
            
            # Handle both list and RetrievalResult return types
            if isinstance(chunks, list):
                result_list = chunks
            else:
                result_list = chunks.results if hasattr(chunks, 'results') else []
            
            if not result_list:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document not found: {document_id}"
                )
            
            # Convert to API response
            chunks = [
                ChunkInfo(
                    chunk_id=r.chunk_id,
                    text=r.text,
                    page_number=r.page_number or 0,
                    section_title=r.section_title,
                    token_count=r.metadata.get("token_count", 0)
                )
                for r in result_list
            ]
            
            return ChunksResponse(
                document_id=document_id,
                chunks=chunks,
                total_count=len(chunks)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get chunks failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get chunks: {str(e)}"
            )
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
