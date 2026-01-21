#!/usr/bin/env python3
"""LLM Benchmark Suite - Main Runner

Single-command benchmark execution for validating RAG-enabled chatbot
accuracy, citation coverage, and performance.

Usage:
    python tests/benchmark/benchmark.py --api-url http://localhost:8080
    python tests/benchmark/benchmark.py --help
"""

import argparse
import sys
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.benchmark.config import load_config
from tests.benchmark.models.dataset import GroundTruthDataset
from tests.benchmark.models.result import TestResult
from tests.benchmark.models.report import BenchmarkReport
from tests.benchmark.models.enums import AccuracyStatus, CitationStatus
from tests.benchmark.validators.fuzzy_match import match_against_variations
from tests.benchmark.validators.citation_check import validate_citations
from tests.benchmark.reporters.cli_reporter import CLIReporter
from tests.benchmark.reporters.json_reporter import JSONReporter


def create_http_session(timeout: float) -> requests.Session:
    """Create HTTP session with retry logic
    
    Args:
        timeout: Request timeout in seconds
    
    Returns:
        Configured requests.Session with retry adapter
    """
    session = requests.Session()
    
    # Retry strategy: 1 retry with exponential backoff
    retry_strategy = Retry(
        total=1,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def test_question(
    session: requests.Session,
    api_url: str,
    question: "BenchmarkQuestion",
    config: "BenchmarkConfig"
) -> TestResult:
    """Test a single question against the LLM API
    
    Args:
        session: HTTP session with retry logic
        api_url: LLM API endpoint URL
        question: BenchmarkQuestion to test
        config: BenchmarkConfig with thresholds
    
    Returns:
        TestResult with accuracy, citation, and latency data
    """
    # Prepare request
    endpoint = f"{api_url.rstrip('/')}/ask"
    payload = {"question": question.question}
    
    # Measure latency
    start_time = time.time()
    
    try:
        # Send request with timeout
        response = session.post(
            endpoint,
            json=payload,
            timeout=config.timeout
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Handle HTTP errors
        if response.status_code != 200:
            return TestResult(
                question_id=question.id,
                question_text=question.question,
                llm_response="",
                citations_found=[],
                accuracy_status=AccuracyStatus.ERROR,
                accuracy_score=0.0,
                citation_status=CitationStatus.MISSING,
                latency_ms=latency_ms,
                error_message=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        
        # Parse response
        try:
            response_data = response.json()
        except ValueError as e:
            return TestResult(
                question_id=question.id,
                question_text=question.question,
                llm_response=response.text[:200],
                citations_found=[],
                accuracy_status=AccuracyStatus.ERROR,
                accuracy_score=0.0,
                citation_status=CitationStatus.MISSING,
                latency_ms=latency_ms,
                error_message=f"Invalid JSON response: {e}"
            )
        
        # Extract answer
        llm_response = response_data.get("answer", "")
        if not llm_response:
            return TestResult(
                question_id=question.id,
                question_text=question.question,
                llm_response="",
                citations_found=[],
                accuracy_status=AccuracyStatus.ERROR,
                accuracy_score=0.0,
                citation_status=CitationStatus.MISSING,
                latency_ms=latency_ms,
                error_message="No 'answer' field in response"
            )
        
        # Validate citations
        citations_valid, citations_found = validate_citations(response_data)
        citation_status = CitationStatus.PRESENT if citations_valid else CitationStatus.MISSING
        
        # Validate accuracy using fuzzy matching
        acceptable_answers = question.get_all_acceptable_answers()
        passes, best_score, _ = match_against_variations(
            acceptable_answers,
            llm_response,
            lev_threshold=config.threshold,
            keyword_threshold=0.70
        )
        
        accuracy_status = AccuracyStatus.PASS if passes else AccuracyStatus.FAIL
        
        return TestResult(
            question_id=question.id,
            question_text=question.question,
            llm_response=llm_response,
            citations_found=citations_found,
            accuracy_status=accuracy_status,
            accuracy_score=best_score,
            citation_status=citation_status,
            latency_ms=latency_ms
        )
    
    except requests.Timeout:
        latency_ms = config.timeout * 1000
        return TestResult(
            question_id=question.id,
            question_text=question.question,
            llm_response="",
            citations_found=[],
            accuracy_status=AccuracyStatus.ERROR,
            accuracy_score=0.0,
            citation_status=CitationStatus.MISSING,
            latency_ms=latency_ms,
            error_message=f"Request timeout after {config.timeout}s"
        )
    
    except requests.RequestException as e:
        latency_ms = (time.time() - start_time) * 1000
        return TestResult(
            question_id=question.id,
            question_text=question.question,
            llm_response="",
            citations_found=[],
            accuracy_status=AccuracyStatus.ERROR,
            accuracy_score=0.0,
            citation_status=CitationStatus.MISSING,
            latency_ms=latency_ms,
            error_message=f"Connection error: {str(e)}"
        )


def run_benchmark(config: "BenchmarkConfig") -> BenchmarkReport:
    """Run full benchmark suite
    
    Args:
        config: BenchmarkConfig with API URL, thresholds, paths
    
    Returns:
        BenchmarkReport with aggregated results
    
    Raises:
        FileNotFoundError: If ground truth file not found
        ValueError: If ground truth is invalid
    """
    # Load ground truth dataset
    print(f"Loading ground truth from: {config.ground_truth_path}")
    dataset = GroundTruthDataset.from_yaml(config.ground_truth_path)
    print(f"Loaded {len(dataset)} questions")
    print()
    
    # Create HTTP session
    session = create_http_session(config.timeout)
    
    # Create reporters
    cli_reporter = CLIReporter()
    
    # Test API health
    print(f"Testing API endpoint: {config.api_url}")
    try:
        health_url = f"{config.api_url.rstrip('/')}/health"
        health_response = session.get(health_url, timeout=5)
        if health_response.status_code == 200:
            print("✓ API is reachable")
        else:
            print(f"⚠ API returned status {health_response.status_code}")
    except Exception as e:
        print(f"⚠ API health check failed: {e}")
    
    print()
    print(f"Configuration: timeout={config.timeout}s, fuzzy_threshold={config.threshold}")
    print()
    
    # Run benchmark
    results = []
    total = len(dataset.questions)
    
    for idx, question in enumerate(dataset.questions, 1):
        result = test_question(session, config.api_url, question, config)
        results.append(result)
        
        # Print progress
        cli_reporter.print_progress(
            idx, total,
            question.id,
            result.accuracy_status.value,
            result.latency_ms
        )
    
    print()
    
    # Create report
    report = BenchmarkReport(
        api_url=config.api_url,
        dataset_version=dataset.version,
        results=results,
        config={
            "timeout": config.timeout,
            "threshold": config.threshold,
            "ground_truth": config.ground_truth_path
        }
    )
    
    return report


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LLM Benchmark Suite - Validate accuracy, citations, and performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --api-url http://localhost:8080
  %(prog)s --api-url http://localhost:8080 --timeout 10 --threshold 0.85
  %(prog)s --validate-only
  
Environment Variables:
  BENCHMARK_API_URL       Default API endpoint URL
  BENCHMARK_TIMEOUT       Default request timeout (seconds)
  BENCHMARK_THRESHOLD     Default fuzzy matching threshold (0.0-1.0)
        """
    )
    
    parser.add_argument(
        "--api-url",
        help="LLM API endpoint URL (required if BENCHMARK_API_URL not set)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Request timeout in seconds (default: 5.0)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="Fuzzy matching threshold 0.0-1.0 (default: 0.8)"
    )
    parser.add_argument(
        "--ground-truth",
        help="Path to ground truth YAML file"
    )
    parser.add_argument(
        "--results-dir",
        help="Directory for storing results (default: results/)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate ground truth syntax without running benchmark"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display benchmark suite version"
    )
    
    args = parser.parse_args()
    
    # Handle --version
    if args.version:
        from tests.benchmark import __version__
        print(f"LLM Benchmark Suite v{__version__}")
        return 0
    
    # Handle --validate-only
    if args.validate_only:
        try:
            config = load_config(
                api_url="http://dummy",  # Dummy URL for validation
                ground_truth_path=args.ground_truth
            )
            dataset = GroundTruthDataset.from_yaml(config.ground_truth_path)
            print(f"✓ Ground truth is valid")
            print(f"  Version: {dataset.version}")
            print(f"  Questions: {len(dataset)}")
            print(f"  Categories: {len(set(q.category for q in dataset.questions))}")
            return 0
        except Exception as e:
            print(f"✗ Ground truth validation failed: {e}", file=sys.stderr)
            return 1
    
    # Load configuration
    try:
        config = load_config(
            api_url=args.api_url,
            timeout=args.timeout,
            threshold=args.threshold,
            ground_truth_path=args.ground_truth,
            results_dir=args.results_dir
        )
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        parser.print_help()
        return 1
    
    # Run benchmark
    try:
        report = run_benchmark(config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user", file=sys.stderr)
        return 130
    
    # Generate CLI report
    cli_reporter = CLIReporter()
    cli_report = cli_reporter.generate_report(report)
    print(cli_report)
    
    # Save JSON report
    json_reporter = JSONReporter(config.results_dir)
    json_path = json_reporter.save_report(report)
    print(f"\nReport saved to: {json_path}")
    
    # Exit with failure if accuracy < 80% (constitution requirement)
    if report.accuracy_percentage < 80.0:
        print(f"\n⚠ WARNING: Accuracy ({report.accuracy_percentage:.1f}%) below 80% constitution requirement", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
