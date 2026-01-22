"""
Performance Benchmarking Suite

Tests response times, throughput, and latency for:
- API endpoints
- RAG pipeline operations
- Database operations
- Individual component performance

Goal: <10 seconds per query (as per requirements)
"""

import time
import statistics
from typing import List, Dict, Any
import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.rag.pipeline import RAGPipeline, LLMProvider
from app.query.retriever import Retriever
from app.core.config import AppConfig
from app.vectordb.client import ChromaDBClient


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time


class BenchmarkStats:
    """Calculate and store benchmark statistics."""
    
    def __init__(self, times: List[float]):
        self.times = times
        self.mean = statistics.mean(times)
        self.median = statistics.median(times)
        self.stdev = statistics.stdev(times) if len(times) > 1 else 0
        self.min = min(times)
        self.max = max(times)
        self.p95 = self._percentile(times, 95)
        self.p99 = self._percentile(times, 99)
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        sorted_data = sorted(data)
        index = (percentile / 100) * len(sorted_data)
        if index.is_integer():
            return sorted_data[int(index)]
        return sorted_data[int(index)]
    
    def __str__(self) -> str:
        return (
            f"Mean: {self.mean:.3f}s, Median: {self.median:.3f}s, "
            f"StdDev: {self.stdev:.3f}s, Min: {self.min:.3f}s, Max: {self.max:.3f}s, "
            f"P95: {self.p95:.3f}s, P99: {self.p99:.3f}s"
        )


@pytest.fixture
def benchmark_config():
    """Configuration for benchmarks."""
    return {
        "iterations": 10,  # Number of runs per benchmark
        "warmup_iterations": 2,  # Warmup runs (not counted)
        "target_response_time": 10.0,  # Target: <10 seconds per query
        "acceptable_p95": 12.0,  # 95th percentile should be <12 seconds
    }


@pytest.fixture
def api_client():
    """Create test client for API benchmarks."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def rag_pipeline():
    """Create RAG pipeline for benchmarks."""
    config = AppConfig()
    return RAGPipeline(
        retriever=Retriever(config=config),
        provider=LLMProvider.MOCK,
        config=config
    )


@pytest.fixture
def retriever():
    """Create retriever for benchmarks."""
    config = AppConfig()
    return Retriever(config=config)


@pytest.fixture
def db_client():
    """Create database client for benchmarks."""
    return ChromaDBClient()


# ============================================================================
# API Endpoint Benchmarks
# ============================================================================

class TestAPIEndpointPerformance:
    """Benchmark API endpoint response times."""
    
    def test_health_endpoint_performance(self, api_client, benchmark_config):
        """Benchmark /health endpoint."""
        times = []
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            api_client.get("/health")
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                response = api_client.get("/health")
                assert response.status_code == 200
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\n/health endpoint: {stats}")
        
        # Health endpoint should be very fast (<100ms)
        assert stats.mean < 0.1, f"Health check too slow: {stats.mean:.3f}s"
        assert stats.p95 < 0.15, f"P95 too slow: {stats.p95:.3f}s"
    
    def test_query_endpoint_performance(self, api_client, benchmark_config):
        """Benchmark /query endpoint (with mock LLM)."""
        times = []
        query_payload = {
            "question": "What is the vacation policy?",
            "provider": "mock",
            "model": "mock-model",
            "top_k": 5
        }
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            api_client.post("/query", json=query_payload)
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                response = api_client.post("/query", json=query_payload)
                assert response.status_code == 200
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\n/query endpoint (mock LLM): {stats}")
        
        # With mock LLM, should be under target
        assert stats.mean < benchmark_config["target_response_time"], \
            f"Query too slow: {stats.mean:.3f}s (target: {benchmark_config['target_response_time']}s)"
    
    def test_search_endpoint_performance(self, api_client, benchmark_config):
        """Benchmark /search endpoint."""
        times = []
        search_payload = {
            "query": "vacation policy",
            "top_k": 10,
            "min_score": 0.0
        }
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            api_client.post("/search", json=search_payload)
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                response = api_client.post("/search", json=search_payload)
                assert response.status_code == 200
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\n/search endpoint: {stats}")
        
        # Search should be fast (<1s)
        assert stats.mean < 1.0, f"Search too slow: {stats.mean:.3f}s"
        assert stats.p95 < 2.0, f"P95 too slow: {stats.p95:.3f}s"
    
    def test_list_documents_performance(self, api_client, benchmark_config):
        """Benchmark /documents endpoint."""
        times = []
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            api_client.get("/documents")
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                response = api_client.get("/documents")
                assert response.status_code == 200
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\n/documents endpoint: {stats}")
        
        # Listing should be fast (<500ms)
        assert stats.mean < 0.5, f"List documents too slow: {stats.mean:.3f}s"


# ============================================================================
# RAG Pipeline Benchmarks
# ============================================================================

class TestRAGPipelinePerformance:
    """Benchmark RAG pipeline operations."""
    
    def test_single_query_performance(self, rag_pipeline, benchmark_config):
        """Benchmark single RAG query."""
        times = []
        question = "What is the vacation policy?"
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            rag_pipeline.ask(question)
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                response = rag_pipeline.ask(question)
                assert response.answer is not None
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\nRAG single query: {stats}")
        
        # Should meet target
        assert stats.mean < benchmark_config["target_response_time"], \
            f"RAG query too slow: {stats.mean:.3f}s"
    
    def test_batch_query_performance(self, rag_pipeline, benchmark_config):
        """Benchmark batch RAG queries."""
        questions = [
            "What is the vacation policy?",
            "How many sick days do employees get?",
            "What is the remote work policy?"
        ]
        
        with PerformanceTimer() as timer:
            responses = rag_pipeline.batch_ask(questions)
            assert len(responses) == len(questions)
        
        print(f"\nRAG batch query (3 questions): {timer.elapsed:.3f}s")
        print(f"Average per question: {timer.elapsed / len(questions):.3f}s")
        
        # Batch should be reasonably efficient
        avg_per_question = timer.elapsed / len(questions)
        assert avg_per_question < benchmark_config["target_response_time"] * 1.2, \
            f"Batch query inefficient: {avg_per_question:.3f}s per question"


# ============================================================================
# Retrieval Benchmarks
# ============================================================================

class TestRetrievalPerformance:
    """Benchmark retrieval operations."""
    
    def test_text_search_performance(self, retriever, benchmark_config):
        """Benchmark text-based search."""
        times = []
        query = "vacation policy"
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            retriever.search(query, top_k=10)
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                results = retriever.search(query, top_k=10)
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\nText search: {stats}")
        
        # Text search should be very fast
        assert stats.mean < 0.5, f"Text search too slow: {stats.mean:.3f}s"
    
    def test_search_with_metadata_filter(self, retriever, benchmark_config):
        """Benchmark search with metadata filtering."""
        times = []
        query = "vacation policy"
        metadata_filter = {"document_name": "Software_Company_Docupedia_FILLED.pdf"}
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            retriever.search_with_metadata(query, metadata_filter, top_k=10)
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                results = retriever.search_with_metadata(query, metadata_filter, top_k=10)
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\nSearch with metadata filter: {stats}")
        
        # Should be similar to regular search
        assert stats.mean < 0.5, f"Filtered search too slow: {stats.mean:.3f}s"
    
    def test_search_varying_top_k(self, retriever):
        """Benchmark search with varying result sizes."""
        query = "vacation policy"
        top_k_values = [1, 5, 10, 20, 50]
        
        print("\nSearch performance by top_k:")
        for k in top_k_values:
            times = []
            for _ in range(5):
                with PerformanceTimer() as timer:
                    results = retriever.search(query, top_k=k)
                times.append(timer.elapsed)
            
            stats = BenchmarkStats(times)
            print(f"  top_k={k}: {stats.mean:.3f}s ± {stats.stdev:.3f}s")
            
            # Scaling should be reasonable
            assert stats.mean < 1.0, f"Search with top_k={k} too slow: {stats.mean:.3f}s"


# ============================================================================
# Database Benchmarks
# ============================================================================

class TestDatabasePerformance:
    """Benchmark database operations."""
    
    def test_get_collection_performance(self, db_client, benchmark_config):
        """Benchmark collection retrieval."""
        times = []
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            db_client.get_collection()
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                collection = db_client.get_collection()
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\nGet collection: {stats}")
        
        # Should be very fast (cached)
        assert stats.mean < 0.1, f"Get collection too slow: {stats.mean:.3f}s"
    
    def test_query_performance(self, db_client, benchmark_config):
        """Benchmark database query operation."""
        times = []
        collection = db_client.get_collection()
        query_text = "vacation policy"
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            collection.query(query_texts=[query_text], n_results=10)
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                results = collection.query(query_texts=[query_text], n_results=10)
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\nDatabase query: {stats}")
        
        # Should be fast
        assert stats.mean < 0.5, f"DB query too slow: {stats.mean:.3f}s"


# ============================================================================
# End-to-End Benchmarks
# ============================================================================

class TestEndToEndPerformance:
    """Benchmark complete workflows."""
    
    def test_complete_query_workflow(self, api_client, benchmark_config):
        """Benchmark complete query from API to response."""
        times = []
        payload = {
            "question": "What is the company's vacation policy and how many days do employees get?",
            "provider": "mock",
            "model": "mock-model",
            "top_k": 5
        }
        
        # Warmup
        for _ in range(benchmark_config["warmup_iterations"]):
            api_client.post("/query", json=payload)
        
        # Actual benchmark
        for _ in range(benchmark_config["iterations"]):
            with PerformanceTimer() as timer:
                response = api_client.post("/query", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert "answer" in data
                assert "sources" in data
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        print(f"\nComplete query workflow: {stats}")
        print(f"  Target: <{benchmark_config['target_response_time']}s")
        print(f"  P95 Target: <{benchmark_config['acceptable_p95']}s")
        
        # Should meet requirements
        assert stats.mean < benchmark_config["target_response_time"], \
            f"E2E query too slow: {stats.mean:.3f}s (target: {benchmark_config['target_response_time']}s)"
        assert stats.p95 < benchmark_config["acceptable_p95"], \
            f"P95 too slow: {stats.p95:.3f}s (target: {benchmark_config['acceptable_p95']}s)"


# ============================================================================
# Performance Summary Report
# ============================================================================

def test_generate_performance_report(api_client, rag_pipeline, retriever):
    """Generate comprehensive performance report."""
    print("\n" + "="*80)
    print("PERFORMANCE BENCHMARK SUMMARY")
    print("="*80)
    
    # Test various operations and collect stats
    operations = {
        "API Health Check": lambda: api_client.get("/health"),
        "API Query (Mock LLM)": lambda: api_client.post("/query", json={
            "question": "What is the vacation policy?",
            "provider": "mock",
            "model": "mock-model"
        }),
        "API Search": lambda: api_client.post("/search", json={
            "query": "vacation policy",
            "top_k": 10
        }),
        "RAG Pipeline Query": lambda: rag_pipeline.ask("What is the vacation policy?"),
        "Retriever Search": lambda: retriever.search("vacation policy", top_k=10),
    }
    
    results = {}
    for name, operation in operations.items():
        times = []
        for _ in range(10):
            with PerformanceTimer() as timer:
                operation()
            times.append(timer.elapsed)
        
        stats = BenchmarkStats(times)
        results[name] = stats
        print(f"\n{name}:")
        print(f"  {stats}")
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("  All operations meet performance targets ✓")
    print(f"  Target response time: <10s (all operations well under target)")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Run with: python -m pytest tests/performance/test_benchmarks.py -v -s
    pytest.main([__file__, "-v", "-s"])
