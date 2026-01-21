"""
FastAPI server for RAG LLM Service.

Provides REST API endpoints for querying the RAG service and checking health status.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from src.rag_service import RAGService
from src.schemas.query import Query, Answer
from src.core.embedding_client import EmbeddingAPIClient
from src.core.retrieval import VectorStoreClient
from src.core.ollama_client import OllamaClient
from src.config import get_settings
from src.utils.logger import get_logger
from src.utils.errors import (
    VectorStoreUnavailable,
    OllamaUnavailable,
    EmbeddingAPIUnavailable,
)

# Load settings
settings = get_settings()

logger = get_logger(__name__)

# Global RAG service instance
rag_service: Optional[RAGService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup RAG service."""
    global rag_service

    logger.info("Initializing RAG service...", extra={"component": "server"})

    try:
        # Initialize clients
        embedding_client = EmbeddingAPIClient(
            api_url=settings.embedding_api_url, timeout=settings.embedding_api_timeout
        )

        vector_store_client = VectorStoreClient(
            chroma_url=settings.vector_store_url,
            collection_name=settings.vector_store_collection,
            timeout=settings.vector_store_timeout,
        )

        ollama_client = OllamaClient(
            host=settings.ollama_host,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
        )

        # Initialize RAG service
        rag_service = RAGService(
            embedding_client=embedding_client,
            vector_store_client=vector_store_client,
            ollama_client=ollama_client,
            min_confidence=settings.min_confidence_threshold,
        )

        logger.info(
            "RAG service initialized successfully", extra={"component": "server"}
        )

    except Exception as e:
        logger.error(
            f"Failed to initialize RAG service: {str(e)}",
            extra={"component": "server", "error": str(e)},
        )
        raise

    yield

    logger.info("Shutting down RAG service...", extra={"component": "server"})


# Create FastAPI app
app = FastAPI(
    title="RAG LLM Service",
    description="Intelligent Knowledge Retrieval Service with Citation-Backed Answers",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class QueryRequest(BaseModel):
    """Request model for /query endpoint."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="User's natural language question",
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters for document retrieval (source, max_results)",
    )
    request_id: Optional[str] = Field(
        default=None, description="Optional request ID for tracing"
    )

    @validator("question")
    def validate_question(cls, v):
        """Validate question is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace")
        return v.strip()

    @validator("filters")
    def validate_filters(cls, v):
        """Validate filters structure."""
        if v is None:
            return v

        # Validate max_results if provided
        if "max_results" in v:
            max_results = v["max_results"]
            if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
                raise ValueError("max_results must be an integer between 1 and 10")

        return v


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error_type: str = Field(
        ...,
        description="Type of error (e.g., 'service_unavailable', 'validation_error')",
    )
    error_details: str = Field(..., description="Human-readable error description")
    request_id: Optional[str] = Field(None, description="Request ID if available")
    timestamp: str = Field(..., description="ISO 8601 timestamp of error")


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with structured data."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")

    # Log incoming request
    logger.info(
        f"Incoming request: {request.method} {request.url.path}",
        extra={
            "component": "http",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
        },
    )

    # Process request
    try:
        response = await call_next(request)
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "component": "http",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "processing_time_ms": processing_time_ms,
            },
        )

        # Add processing time header
        response.headers["X-Processing-Time-Ms"] = str(processing_time_ms)
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(
            f"Request failed: {request.method} {request.url.path}",
            extra={
                "component": "http",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "processing_time_ms": processing_time_ms,
            },
        )
        raise


# Exception handlers
@app.exception_handler(VectorStoreUnavailable)
async def vector_store_unavailable_handler(
    request: Request, exc: VectorStoreUnavailable
):
    """Handle vector store unavailability."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            error_type="vector_store_unavailable",
            error_details=str(exc),
            request_id=request.headers.get("X-Request-ID"),
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


@app.exception_handler(OllamaUnavailable)
async def ollama_unavailable_handler(request: Request, exc: OllamaUnavailable):
    """Handle Ollama unavailability."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            error_type="ollama_unavailable",
            error_details=str(exc),
            request_id=request.headers.get("X-Request-ID"),
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


@app.exception_handler(EmbeddingAPIUnavailable)
async def embedding_api_unavailable_handler(
    request: Request, exc: EmbeddingAPIUnavailable
):
    """Handle embedding API unavailability."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            error_type="embedding_api_unavailable",
            error_details=str(exc),
            request_id=request.headers.get("X-Request-ID"),
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error_type="validation_error",
            error_details=str(exc),
            request_id=request.headers.get("X-Request-ID"),
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={"component": "server", "error": str(exc), "path": request.url.path},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_type="internal_server_error",
            error_details="An unexpected error occurred",
            request_id=request.headers.get("X-Request-ID"),
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


# API Endpoints
@app.post("/query", response_model=Answer, status_code=status.HTTP_200_OK)
async def query_endpoint(query_request: QueryRequest, request: Request):
    """
    Query the RAG service with a natural language question.

    Returns an answer with citations from the knowledge base.
    If confidence is too low, returns "I don't know" response.
    """
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service not initialized",
        )

    # Get request ID from header or use provided one
    request_id = request.headers.get("X-Request-ID") or query_request.request_id

    logger.info(
        f"Processing query: {query_request.question[:50]}...",
        extra={
            "component": "api",
            "request_id": request_id,
            "question_length": len(query_request.question),
        },
    )

    try:
        # Execute query
        answer = rag_service.query(
            question=query_request.question,
            filters=query_request.filters,
            request_id=request_id,
        )

        logger.info(
            f"Query completed successfully",
            extra={
                "component": "api",
                "request_id": request_id,
                "confidence": answer.confidence,
                "citations_count": len(answer.citations),
                "processing_time_ms": answer.processing_time_ms,
            },
        )

        return answer

    except (VectorStoreUnavailable, OllamaUnavailable, EmbeddingAPIUnavailable) as e:
        # These will be caught by exception handlers
        raise
    except Exception as e:
        logger.error(
            f"Query failed: {str(e)}",
            extra={"component": "api", "request_id": request_id, "error": str(e)},
        )
        raise


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_endpoint():
    """
    Check health status of RAG service and all dependencies.

    Returns:
    - status: "healthy" (all services up), "degraded" (some services down), "unhealthy" (critical failure)
    - components: Health status of each service component
    - timestamp: ISO 8601 timestamp
    """
    if rag_service is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": "RAG service not initialized",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )

    try:
        health_status = rag_service.health_check()

        # Determine HTTP status code based on health
        if health_status["status"] == "healthy":
            status_code = status.HTTP_200_OK
        elif health_status["status"] == "degraded":
            status_code = status.HTTP_200_OK  # Still operational
        else:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(status_code=status_code, content=health_status)

    except Exception as e:
        logger.error(
            f"Health check failed: {str(e)}",
            extra={"component": "health", "error": str(e)},
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint with API information."""
    return {
        "service": "RAG LLM Service",
        "version": "1.0.0",
        "description": "Intelligent Knowledge Retrieval Service with Citation-Backed Answers",
        "endpoints": {
            "POST /query": "Submit a question and receive an answer with citations",
            "GET /health": "Check service health status",
            "GET /": "This information page",
        },
    }
