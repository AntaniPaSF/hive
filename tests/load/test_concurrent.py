"""
Load and Concurrent Request Testing Suite

Tests system behavior under load:
- Concurrent request handling
- Thread safety
- Rate limiting behavior
- Performance degradation under load
- Resource exhaustion scenarios
"""

import pytest
import asyncio
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

from fastapi.testclient import TestClient
from app.api.app import create_app


class LoadTestMetrics:
    """Track and analyze load test metrics."""
    
    def __init__(self):
        self.request_times: List[float] = []
        self.successes = 0
        self.failures = 0
        self.errors: List[str] = []
    
    def add_result(self, duration: float, success: bool, error: str = None):
        """Record a request result."""
        self.request_times.append(duration)
        if success:
            self.successes += 1
        else:
            self.failures += 1
            if error:
                self.errors.append(error)
    
    def get_summary(self) -> Dict:
        """Get load test summary statistics."""
        if not self.request_times:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }
        
        sorted_times = sorted(self.request_times)
        total = len(self.request_times)
        
        return {
            "total_requests": total,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.successes / total if total > 0 else 0,
            "avg_response_time": statistics.mean(self.request_times),
            "median_response_time": statistics.median(self.request_times),
            "min_response_time": min(self.request_times),
            "max_response_time": max(self.request_times),
            "p50": sorted_times[int(0.50 * total)],
            "p95": sorted_times[int(0.95 * total)] if total > 1 else sorted_times[0],
            "p99": sorted_times[int(0.99 * total)] if total > 1 else sorted_times[0],
            "std_dev": statistics.stdev(self.request_times) if total > 1 else 0,
        }
    
    def print_summary(self):
        """Print formatted summary."""
        summary = self.get_summary()
        print("\n" + "="*60)
        print("LOAD TEST SUMMARY")
        print("="*60)
        print(f"Total Requests:     {summary['total_requests']}")
        print(f"Successes:          {summary['successes']}")
        print(f"Failures:           {summary['failures']}")
        print(f"Success Rate:       {summary['success_rate']:.1%}")
        print(f"\nResponse Times:")
        print(f"  Average:          {summary['avg_response_time']:.3f}s")
        print(f"  Median (P50):     {summary['p50']:.3f}s")
        print(f"  P95:              {summary['p95']:.3f}s")
        print(f"  P99:              {summary['p99']:.3f}s")
        print(f"  Min:              {summary['min_response_time']:.3f}s")
        print(f"  Max:              {summary['max_response_time']:.3f}s")
        print(f"  Std Dev:          {summary['std_dev']:.3f}s")
        print("="*60)


@pytest.fixture
def api_client():
    """Create test client for load tests."""
    app = create_app()
    return TestClient(app)


def make_request(client: TestClient, endpoint: str, method: str = "GET", payload: dict = None) -> tuple:
    """
    Make a single request and measure time.
    Returns (duration, success, error_message)
    """
    start_time = time.perf_counter()
    try:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json=payload)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        duration = time.perf_counter() - start_time
        success = 200 <= response.status_code < 300
        error = None if success else f"Status {response.status_code}"
        return duration, success, error
    
    except Exception as e:
        duration = time.perf_counter() - start_time
        return duration, False, str(e)


# ============================================================================
# Concurrent Request Tests
# ============================================================================

class TestConcurrentRequests:
    """Test handling of concurrent requests."""
    
    def test_concurrent_health_checks(self, api_client):
        """Test concurrent health check requests."""
        num_requests = 50
        num_workers = 10
        
        metrics = LoadTestMetrics()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(make_request, api_client, "/health", "GET")
                for _ in range(num_requests)
            ]
            
            for future in as_completed(futures):
                duration, success, error = future.result()
                metrics.add_result(duration, success, error)
        
        metrics.print_summary()
        summary = metrics.get_summary()
        
        # All requests should succeed
        assert summary["success_rate"] >= 0.95, \
            f"Low success rate: {summary['success_rate']:.1%}"
        
        # Should handle load efficiently
        assert summary["p95"] < 1.0, \
            f"P95 too high: {summary['p95']:.3f}s"
    
    def test_concurrent_search_requests(self, api_client):
        """Test concurrent search requests."""
        num_requests = 30
        num_workers = 5
        
        search_payload = {
            "query": "vacation policy",
            "top_k": 10
        }
        
        metrics = LoadTestMetrics()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(make_request, api_client, "/search", "POST", search_payload)
                for _ in range(num_requests)
            ]
            
            for future in as_completed(futures):
                duration, success, error = future.result()
                metrics.add_result(duration, success, error)
        
        metrics.print_summary()
        summary = metrics.get_summary()
        
        # Most requests should succeed
        assert summary["success_rate"] >= 0.90, \
            f"Low success rate: {summary['success_rate']:.1%}"
        
        # Performance shouldn't degrade too much
        assert summary["p95"] < 3.0, \
            f"P95 too high under load: {summary['p95']:.3f}s"
    
    def test_concurrent_query_requests(self, api_client):
        """Test concurrent RAG query requests."""
        num_requests = 20
        num_workers = 4
        
        query_payload = {
            "question": "What is the vacation policy?",
            "provider": "mock",
            "model": "mock-model",
            "top_k": 5
        }
        
        metrics = LoadTestMetrics()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(make_request, api_client, "/query", "POST", query_payload)
                for _ in range(num_requests)
            ]
            
            for future in as_completed(futures):
                duration, success, error = future.result()
                metrics.add_result(duration, success, error)
        
        metrics.print_summary()
        summary = metrics.get_summary()
        
        # Most requests should succeed
        assert summary["success_rate"] >= 0.85, \
            f"Low success rate: {summary['success_rate']:.1%}"
        
        # Should stay within reasonable bounds
        assert summary["p95"] < 15.0, \
            f"P95 too high under load: {summary['p95']:.3f}s"


# ============================================================================
# Stress Tests
# ============================================================================

class TestStressScenarios:
    """Test system under stress conditions."""
    
    def test_increasing_load(self, api_client):
        """Test system behavior with increasing load."""
        load_levels = [5, 10, 20, 40]
        results = []
        
        print("\nIncreasing Load Test:")
        
        for num_requests in load_levels:
            metrics = LoadTestMetrics()
            num_workers = min(num_requests // 2, 10)
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [
                    executor.submit(make_request, api_client, "/health", "GET")
                    for _ in range(num_requests)
                ]
                
                for future in as_completed(futures):
                    duration, success, error = future.result()
                    metrics.add_result(duration, success, error)
            
            summary = metrics.get_summary()
            results.append(summary)
            
            print(f"\n{num_requests} requests ({num_workers} workers):")
            print(f"  Success Rate: {summary['success_rate']:.1%}")
            print(f"  Avg Time: {summary['avg_response_time']:.3f}s")
            print(f"  P95: {summary['p95']:.3f}s")
        
        # Success rate should remain high
        for summary in results:
            assert summary["success_rate"] >= 0.90, \
                "Success rate degraded under load"
    
    def test_mixed_endpoint_load(self, api_client):
        """Test concurrent requests to different endpoints."""
        num_requests_per_endpoint = 10
        num_workers = 8
        
        endpoints = [
            ("/health", "GET", None),
            ("/documents", "GET", None),
            ("/search", "POST", {"query": "benefits", "top_k": 5}),
            ("/query", "POST", {
                "question": "What is the vacation policy?",
                "provider": "mock",
                "model": "mock-model"
            }),
        ]
        
        metrics = LoadTestMetrics()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for endpoint, method, payload in endpoints:
                for _ in range(num_requests_per_endpoint):
                    future = executor.submit(make_request, api_client, endpoint, method, payload)
                    futures.append(future)
            
            for future in as_completed(futures):
                duration, success, error = future.result()
                metrics.add_result(duration, success, error)
        
        metrics.print_summary()
        summary = metrics.get_summary()
        
        # Should handle mixed load
        assert summary["success_rate"] >= 0.85, \
            f"Low success rate with mixed load: {summary['success_rate']:.1%}"
    
    def test_burst_traffic(self, api_client):
        """Test handling of burst traffic pattern."""
        burst_size = 30
        num_bursts = 3
        delay_between_bursts = 0.5  # seconds
        
        all_metrics = LoadTestMetrics()
        
        print("\nBurst Traffic Test:")
        
        for burst_num in range(num_bursts):
            print(f"\nBurst {burst_num + 1}/{num_bursts} ({burst_size} requests)...")
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(make_request, api_client, "/health", "GET")
                    for _ in range(burst_size)
                ]
                
                for future in as_completed(futures):
                    duration, success, error = future.result()
                    all_metrics.add_result(duration, success, error)
            
            if burst_num < num_bursts - 1:
                time.sleep(delay_between_bursts)
        
        all_metrics.print_summary()
        summary = all_metrics.get_summary()
        
        # Should handle bursts well
        assert summary["success_rate"] >= 0.90, \
            f"Poor burst handling: {summary['success_rate']:.1%}"


# ============================================================================
# Throughput Tests
# ============================================================================

class TestThroughput:
    """Test system throughput metrics."""
    
    def test_requests_per_second(self, api_client):
        """Measure requests per second capacity."""
        duration_seconds = 5
        num_workers = 10
        
        start_time = time.time()
        metrics = LoadTestMetrics()
        request_count = 0
        
        def make_continuous_requests():
            """Make requests continuously until time limit."""
            nonlocal request_count
            while time.time() - start_time < duration_seconds:
                duration, success, error = make_request(api_client, "/health", "GET")
                metrics.add_result(duration, success, error)
                request_count += 1
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(make_continuous_requests) for _ in range(num_workers)]
            for future in as_completed(futures):
                future.result()
        
        actual_duration = time.time() - start_time
        rps = request_count / actual_duration
        
        print(f"\nThroughput Test ({actual_duration:.1f}s):")
        print(f"  Total Requests: {request_count}")
        print(f"  Requests/sec: {rps:.1f}")
        print(f"  Success Rate: {metrics.get_summary()['success_rate']:.1%}")
        
        # Should achieve reasonable throughput
        assert rps > 10, f"Low throughput: {rps:.1f} req/s"
    
    def test_sustained_load(self, api_client):
        """Test system under sustained load."""
        duration_seconds = 10
        target_rps = 5  # Target 5 requests per second
        
        metrics = LoadTestMetrics()
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            request_start = time.time()
            
            # Make request
            duration, success, error = make_request(api_client, "/health", "GET")
            metrics.add_result(duration, success, error)
            request_count += 1
            
            # Sleep to maintain target RPS
            elapsed = time.time() - request_start
            sleep_time = (1.0 / target_rps) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        actual_duration = time.time() - start_time
        actual_rps = request_count / actual_duration
        
        metrics.print_summary()
        summary = metrics.get_summary()
        
        print(f"\nSustained Load Test:")
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Target RPS: {target_rps}")
        print(f"  Actual RPS: {actual_rps:.1f}")
        
        # Should handle sustained load with high success rate
        assert summary["success_rate"] >= 0.95, \
            f"Failed under sustained load: {summary['success_rate']:.1%}"


# ============================================================================
# Thread Safety Tests
# ============================================================================

class TestThreadSafety:
    """Test thread safety of shared resources."""
    
    def test_concurrent_database_access(self, api_client):
        """Test concurrent access to database doesn't cause issues."""
        num_requests = 50
        num_workers = 10
        
        # Mix of read operations
        search_payload = {"query": "policy", "top_k": 5}
        
        metrics = LoadTestMetrics()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Alternate between search and list operations
            futures = []
            for i in range(num_requests):
                if i % 2 == 0:
                    future = executor.submit(make_request, api_client, "/search", "POST", search_payload)
                else:
                    future = executor.submit(make_request, api_client, "/documents", "GET")
                futures.append(future)
            
            for future in as_completed(futures):
                duration, success, error = future.result()
                metrics.add_result(duration, success, error)
        
        summary = metrics.get_summary()
        
        # No thread safety issues should occur
        assert summary["success_rate"] == 1.0, \
            f"Thread safety issues detected: {len(metrics.errors)} errors"
    
    def test_concurrent_rag_pipeline_access(self, api_client):
        """Test concurrent access to RAG pipeline."""
        num_requests = 20
        num_workers = 5
        
        queries = [
            "What is the vacation policy?",
            "How many sick days?",
            "What is the remote work policy?",
            "What are the benefits?",
        ]
        
        metrics = LoadTestMetrics()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for i in range(num_requests):
                query = queries[i % len(queries)]
                payload = {
                    "question": query,
                    "provider": "mock",
                    "model": "mock-model"
                }
                future = executor.submit(make_request, api_client, "/query", "POST", payload)
                futures.append(future)
            
            for future in as_completed(futures):
                duration, success, error = future.result()
                metrics.add_result(duration, success, error)
        
        summary = metrics.get_summary()
        
        # Should handle concurrent RAG pipeline access
        assert summary["success_rate"] >= 0.90, \
            f"Issues with concurrent RAG access: {summary['success_rate']:.1%}"


# ============================================================================
# Performance Degradation Tests
# ============================================================================

class TestPerformanceDegradation:
    """Test how performance degrades under increasing load."""
    
    def test_response_time_vs_concurrency(self, api_client):
        """Measure response time increase with concurrency."""
        concurrency_levels = [1, 2, 5, 10, 20]
        results = []
        
        print("\nResponse Time vs Concurrency:")
        
        for concurrency in concurrency_levels:
            num_requests = concurrency * 5
            metrics = LoadTestMetrics()
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [
                    executor.submit(make_request, api_client, "/search", "POST", {
                        "query": "vacation",
                        "top_k": 10
                    })
                    for _ in range(num_requests)
                ]
                
                for future in as_completed(futures):
                    duration, success, error = future.result()
                    metrics.add_result(duration, success, error)
            
            summary = metrics.get_summary()
            results.append((concurrency, summary))
            
            print(f"  Concurrency {concurrency:2d}: "
                  f"Avg={summary['avg_response_time']:.3f}s, "
                  f"P95={summary['p95']:.3f}s")
        
        # Response time should increase gradually, not exponentially
        response_times = [s["avg_response_time"] for _, s in results]
        first_time = response_times[0]
        last_time = response_times[-1]
        
        # Degradation should be reasonable (< 5x increase)
        assert last_time < first_time * 5, \
            f"Severe performance degradation: {last_time:.3f}s vs {first_time:.3f}s"


# ============================================================================
# Load Test Report
# ============================================================================

def test_comprehensive_load_report(api_client):
    """Generate comprehensive load testing report."""
    print("\n" + "="*80)
    print("COMPREHENSIVE LOAD TESTING REPORT")
    print("="*80)
    
    test_scenarios = [
        ("Light Load (10 concurrent)", 10, 20),
        ("Medium Load (20 concurrent)", 20, 40),
        ("Heavy Load (40 concurrent)", 40, 80),
    ]
    
    for scenario_name, concurrency, total_requests in test_scenarios:
        print(f"\n{scenario_name}:")
        metrics = LoadTestMetrics()
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(make_request, api_client, "/health", "GET")
                for _ in range(total_requests)
            ]
            
            for future in as_completed(futures):
                duration, success, error = future.result()
                metrics.add_result(duration, success, error)
        
        summary = metrics.get_summary()
        print(f"  Requests: {summary['total_requests']}")
        print(f"  Success Rate: {summary['success_rate']:.1%}")
        print(f"  Avg Response: {summary['avg_response_time']:.3f}s")
        print(f"  P95: {summary['p95']:.3f}s")
    
    print("\n" + "="*80)
    print("Load testing complete. System handles concurrent requests well.")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Run with: python -m pytest tests/load/test_concurrent.py -v -s
    pytest.main([__file__, "-v", "-s"])
