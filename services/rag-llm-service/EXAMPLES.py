"""
RAG LLM Service - Code Examples

This file demonstrates how to use the RAG service programmatically,
both as a standalone module and integrated with FastAPI.
"""

# ============================================================================
# Example 1: Using RAGService Directly
# ============================================================================

"""
Scenario: You want to use the RAG service as a Python module in your own application,
without the FastAPI wrapper.
"""

import asyncio
from src.rag_service import RAGService
from src.core.retrieval import VectorStoreClient
from src.core.ollama_client import OllamaClient
from src.core.embedding_client import EmbeddingAPIClient
from src.config import get_settings


async def example_direct_rag_service():
    """Use RAG service directly without FastAPI."""

    # 1. Load configuration
    settings = get_settings()

    # 2. Initialize clients
    retrieval_client = VectorStoreClient(
        vector_store_url=settings.VECTOR_STORE_URL,
        collection_name=settings.VECTOR_STORE_COLLECTION,
    )

    ollama_client = OllamaClient(
        api_url=settings.OLLAMA_HOST, model=settings.OLLAMA_MODEL
    )

    embedding_client = EmbeddingAPIClient(
        api_url=settings.EMBEDDING_API_URL, model=settings.EMBEDDING_MODEL
    )

    # 3. Create RAG service
    rag_service = RAGService(
        retrieval_client=retrieval_client,
        ollama_client=ollama_client,
        embedding_client=embedding_client,
        min_confidence_threshold=settings.MIN_CONFIDENCE_THRESHOLD,
    )

    # 4. Ask a question
    question = "What is the vacation policy?"
    filters = {"max_results": 5}

    answer = await rag_service.query(question=question, filters=filters)

    # 5. Handle response
    if answer.answer:
        print(f"Answer: {answer.answer}")
        print(f"Confidence: {answer.confidence}")
        print(f"\nCitations ({len(answer.citations)}):")
        for citation in answer.citations:
            print(f"  - {citation.document_name}, {citation.section}")
    else:
        print(f"Message: {answer.message}")

    print(f"\nProcessing time: {answer.processing_time_ms}ms")
    print(f"Request ID: {answer.request_id}")


# ============================================================================
# Example 2: Custom Question with Filters
# ============================================================================


async def example_filtered_query():
    """Query with source filter and custom max_results."""

    settings = get_settings()

    # Initialize (same as Example 1)
    retrieval_client = VectorStoreClient(
        vector_store_url=settings.VECTOR_STORE_URL,
        collection_name=settings.VECTOR_STORE_COLLECTION,
    )
    ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
    embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

    rag_service = RAGService(
        retrieval_client=retrieval_client,
        ollama_client=ollama_client,
        embedding_client=embedding_client,
    )

    # Query with filters
    answer = await rag_service.query(
        question="What are the safety protocols for handling chemicals?",
        filters={
            "source": "safety_manual.pdf",  # Only search in this document
            "max_results": 3,  # Limit to top 3 chunks
        },
    )

    return answer


# ============================================================================
# Example 3: Batch Processing Multiple Questions
# ============================================================================


async def example_batch_queries():
    """Process multiple questions in parallel."""

    settings = get_settings()

    # Initialize service (reuse for all queries)
    retrieval_client = VectorStoreClient(
        vector_store_url=settings.VECTOR_STORE_URL,
        collection_name=settings.VECTOR_STORE_COLLECTION,
    )
    ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
    embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

    rag_service = RAGService(
        retrieval_client=retrieval_client,
        ollama_client=ollama_client,
        embedding_client=embedding_client,
    )

    # List of questions
    questions = [
        "What is the vacation policy?",
        "How do I request parental leave?",
        "What are the remote work guidelines?",
        "What health insurance benefits are available?",
    ]

    # Process in parallel
    tasks = [
        rag_service.query(question=q, filters={"max_results": 5}) for q in questions
    ]
    answers = await asyncio.gather(*tasks)

    # Display results
    for question, answer in zip(questions, answers):
        print(f"\nQ: {question}")
        if answer.answer:
            print(f"A: {answer.answer[:100]}...")  # First 100 chars
            print(f"Confidence: {answer.confidence}")
        else:
            print(f"A: {answer.message}")


# ============================================================================
# Example 4: Error Handling
# ============================================================================


async def example_error_handling():
    """Handle errors gracefully."""

    from src.utils.errors import VectorStoreUnavailable, OllamaUnavailable, InvalidQuery

    settings = get_settings()

    # Initialize service
    retrieval_client = VectorStoreClient(
        vector_store_url=settings.VECTOR_STORE_URL,
        collection_name=settings.VECTOR_STORE_COLLECTION,
    )
    ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
    embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

    rag_service = RAGService(
        retrieval_client=retrieval_client,
        ollama_client=ollama_client,
        embedding_client=embedding_client,
    )

    try:
        # This might fail if question is too short
        answer = await rag_service.query(question="Hi", filters={})
    except InvalidQuery as e:
        print(f"Invalid question: {e.message}")
        print(f"Field: {e.field}")
    except VectorStoreUnavailable as e:
        print(f"Vector store error: {e}")
        # Retry logic or fallback
    except OllamaUnavailable as e:
        print(f"LLM error: {e}")
        # Retry or degrade gracefully
    except Exception as e:
        print(f"Unexpected error: {e}")


# ============================================================================
# Example 5: Health Check
# ============================================================================


async def example_health_check():
    """Check health status of all dependencies."""

    settings = get_settings()

    # Initialize service
    retrieval_client = VectorStoreClient(
        vector_store_url=settings.VECTOR_STORE_URL,
        collection_name=settings.VECTOR_STORE_COLLECTION,
    )
    ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
    embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

    rag_service = RAGService(
        retrieval_client=retrieval_client,
        ollama_client=ollama_client,
        embedding_client=embedding_client,
    )

    # Check health
    health_status = await rag_service.health_check()

    print("Health Status:")
    print(f"  Overall: {health_status['status']}")
    print(f"  Ollama: {health_status['ollama']}")
    print(f"  Vector Store: {health_status['vector_store']}")
    print(f"  Embedding API: {health_status['embedding_api']}")

    # Conditional logic based on health
    if health_status["status"] == "healthy":
        print("All systems operational!")
    elif health_status["status"] == "degraded":
        print("Warning: Some services are unavailable")
    else:
        print("Critical: Service is down")


# ============================================================================
# Example 6: Using FastAPI Client (HTTP Requests)
# ============================================================================

"""
Scenario: You want to call the RAG service via HTTP API from another application.
"""

import httpx


async def example_fastapi_http_client():
    """Call RAG service via HTTP API."""

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # 1. Health check
        health_response = await client.get(f"{base_url}/health")
        print(f"Health: {health_response.json()}")

        # 2. Query endpoint
        query_data = {
            "question": "What is the vacation policy?",
            "filters": {"max_results": 5},
        }

        headers = {"X-Request-ID": "my-custom-request-id"}

        query_response = await client.post(
            f"{base_url}/query", json=query_data, headers=headers, timeout=30.0
        )

        if query_response.status_code == 200:
            result = query_response.json()
            print(f"\nAnswer: {result['answer']}")
            print(f"Confidence: {result['confidence']}")
            print(f"Citations: {len(result['citations'])}")
        else:
            print(f"Error: {query_response.status_code}")
            print(f"Detail: {query_response.json()}")


# ============================================================================
# Example 7: Synchronous Wrapper (for non-async code)
# ============================================================================

"""
Scenario: You have existing synchronous code and need to call the RAG service.
"""


def example_sync_wrapper():
    """Synchronous wrapper for RAG service."""

    async def _async_query():
        settings = get_settings()

        retrieval_client = VectorStoreClient(
            vector_store_url=settings.VECTOR_STORE_URL,
            collection_name=settings.VECTOR_STORE_COLLECTION,
        )
        ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
        embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

        rag_service = RAGService(
            retrieval_client=retrieval_client,
            ollama_client=ollama_client,
            embedding_client=embedding_client,
        )

        return await rag_service.query(
            question="What is the vacation policy?", filters={}
        )

    # Run async code from sync context
    answer = asyncio.run(_async_query())

    print(f"Answer: {answer.answer}")
    return answer


# ============================================================================
# Example 8: Custom Confidence Threshold
# ============================================================================


async def example_custom_confidence():
    """Use custom confidence threshold for stricter filtering."""

    settings = get_settings()

    # Initialize with higher confidence threshold
    retrieval_client = VectorStoreClient(
        vector_store_url=settings.VECTOR_STORE_URL,
        collection_name=settings.VECTOR_STORE_COLLECTION,
    )
    ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
    embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

    # Stricter threshold: require 70% confidence
    rag_service = RAGService(
        retrieval_client=retrieval_client,
        ollama_client=ollama_client,
        embedding_client=embedding_client,
        min_confidence_threshold=0.7,  # Default is 0.5
    )

    answer = await rag_service.query(
        question="What is the vacation policy?", filters={}
    )

    if answer.answer:
        print(f"High-confidence answer: {answer.answer}")
    else:
        print("Answer did not meet confidence threshold")


# ============================================================================
# Example 9: Logging and Debugging
# ============================================================================


async def example_with_logging():
    """Enable detailed logging for debugging."""

    import logging
    from src.utils.logger import setup_logging

    # Configure DEBUG logging
    setup_logging(log_level="DEBUG", log_format="json")

    logger = logging.getLogger(__name__)
    logger.info("Starting RAG query with DEBUG logging")

    settings = get_settings()

    retrieval_client = VectorStoreClient(
        vector_store_url=settings.VECTOR_STORE_URL,
        collection_name=settings.VECTOR_STORE_COLLECTION,
    )
    ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
    embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

    rag_service = RAGService(
        retrieval_client=retrieval_client,
        ollama_client=ollama_client,
        embedding_client=embedding_client,
    )

    # This will log:
    # - Embedding generation
    # - Retrieval results (similarity scores)
    # - LLM generation time
    # - Citation extraction
    answer = await rag_service.query(
        question="What is the vacation policy?", filters={}
    )

    logger.info(
        "Query completed",
        extra={
            "request_id": answer.request_id,
            "confidence": answer.confidence,
            "processing_time_ms": answer.processing_time_ms,
        },
    )


# ============================================================================
# Example 10: Integration with FastAPI Dependency Injection
# ============================================================================

"""
Scenario: You're building a FastAPI application and want to reuse RAG service instances.
"""

from fastapi import Depends, FastAPI
from typing import Annotated


# Create FastAPI app
app = FastAPI()

# Dependency for RAG service (singleton pattern)
_rag_service_instance = None


async def get_rag_service() -> RAGService:
    """Dependency injection for RAG service."""
    global _rag_service_instance

    if _rag_service_instance is None:
        settings = get_settings()

        retrieval_client = VectorStoreClient(
            vector_store_url=settings.VECTOR_STORE_URL,
            collection_name=settings.VECTOR_STORE_COLLECTION,
        )
        ollama_client = OllamaClient(api_url=settings.OLLAMA_HOST)
        embedding_client = EmbeddingAPIClient(api_url=settings.EMBEDDING_API_URL)

        _rag_service_instance = RAGService(
            retrieval_client=retrieval_client,
            ollama_client=ollama_client,
            embedding_client=embedding_client,
        )

    return _rag_service_instance


@app.post("/custom-query")
async def custom_query_endpoint(
    question: str, rag_service: Annotated[RAGService, Depends(get_rag_service)]
):
    """Custom endpoint using RAG service dependency."""
    answer = await rag_service.query(question=question, filters={})
    return {"answer": answer.answer, "confidence": answer.confidence}


# ============================================================================
# Running the Examples
# ============================================================================

if __name__ == "__main__":
    print("RAG LLM Service - Examples\n")

    # Uncomment to run specific examples:

    # Example 1: Direct RAG service usage
    # asyncio.run(example_direct_rag_service())

    # Example 2: Filtered query
    # asyncio.run(example_filtered_query())

    # Example 3: Batch processing
    # asyncio.run(example_batch_queries())

    # Example 4: Error handling
    # asyncio.run(example_error_handling())

    # Example 5: Health check
    # asyncio.run(example_health_check())

    # Example 6: HTTP client
    # asyncio.run(example_fastapi_http_client())

    # Example 7: Synchronous wrapper
    # example_sync_wrapper()

    # Example 8: Custom confidence threshold
    # asyncio.run(example_custom_confidence())

    # Example 9: Debug logging
    # asyncio.run(example_with_logging())

    print("\nTo run examples, uncomment the desired function call above.")
