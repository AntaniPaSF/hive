"""BenchmarkReport data model

Aggregates test results with summary statistics and performance metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

from .result import TestResult
from .enums import AccuracyStatus, CitationStatus


@dataclass
class BenchmarkReport:
    """Aggregated benchmark results with metrics
    
    Attributes:
        timestamp: ISO 8601 timestamp of benchmark run
        api_url: LLM API endpoint that was tested
        total_questions: Total number of questions tested
        passed_questions: Number of questions that passed
        failed_questions: Number of questions that failed
        error_questions: Number of questions with API errors
        accuracy_percentage: Overall accuracy (0-100)
        citation_coverage_percentage: Citation coverage (0-100)
        performance_metrics: Dict with p50/p95/p99 latency metrics
        results: List of individual test results
        dataset_version: Ground truth dataset version
        config: Configuration used for benchmark run
    """
    
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    api_url: str = ""
    total_questions: int = 0
    passed_questions: int = 0
    failed_questions: int = 0
    error_questions: int = 0
    accuracy_percentage: float = 0.0
    citation_coverage_percentage: float = 0.0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    results: List[TestResult] = field(default_factory=list)
    dataset_version: str = ""
    config: Optional[Dict[str, any]] = None
    
    def __post_init__(self):
        """Calculate metrics from results if provided"""
        if self.results:
            self._calculate_metrics()
    
    def _calculate_metrics(self):
        """Calculate summary metrics from individual results"""
        self.total_questions = len(self.results)
        
        if self.total_questions == 0:
            return
        
        # Count statuses
        self.passed_questions = sum(
            1 for r in self.results
            if r.accuracy_status == AccuracyStatus.PASS
        )
        self.failed_questions = sum(
            1 for r in self.results
            if r.accuracy_status == AccuracyStatus.FAIL
        )
        self.error_questions = sum(
            1 for r in self.results
            if r.accuracy_status == AccuracyStatus.ERROR
        )
        
        # Calculate percentages
        self.accuracy_percentage = (self.passed_questions / self.total_questions) * 100
        
        # Citation coverage
        citations_present = sum(
            1 for r in self.results
            if r.citation_status == CitationStatus.PRESENT
        )
        self.citation_coverage_percentage = (citations_present / self.total_questions) * 100
    
    def add_result(self, result: TestResult):
        """Add a test result and recalculate metrics
        
        Args:
            result: TestResult to add
        """
        self.results.append(result)
        self._calculate_metrics()
    
    def get_failed_results(self) -> List[TestResult]:
        """Get list of failed test results
        
        Returns:
            List of TestResults with FAIL or ERROR status
        """
        return [
            r for r in self.results
            if r.accuracy_status in (AccuracyStatus.FAIL, AccuracyStatus.ERROR)
        ]
    
    def get_slow_results(self, threshold_ms: float = 10000) -> List[TestResult]:
        """Get results that exceeded latency threshold
        
        Args:
            threshold_ms: Latency threshold in milliseconds (default: 10000 = 10s)
        
        Returns:
            List of TestResults with latency > threshold
        """
        return [r for r in self.results if r.latency_ms > threshold_ms]
    
    def to_dict(self) -> dict:
        """Convert report to dictionary for JSON serialization
        
        Returns:
            Dictionary representation with nested results
        """
        return {
            "timestamp": self.timestamp,
            "api_url": self.api_url,
            "dataset_version": self.dataset_version,
            "config": self.config,
            "summary": {
                "total_questions": self.total_questions,
                "passed_questions": self.passed_questions,
                "failed_questions": self.failed_questions,
                "error_questions": self.error_questions,
                "accuracy_percentage": round(self.accuracy_percentage, 2),
                "citation_coverage_percentage": round(self.citation_coverage_percentage, 2)
            },
            "performance": self.performance_metrics,
            "results": [r.to_dict() for r in self.results]
        }
