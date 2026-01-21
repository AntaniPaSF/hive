"""CLI Reporter - Human-readable text output

Generates formatted text summaries of benchmark results for CLI display.
"""

from typing import List
from ..models.report import BenchmarkReport
from ..models.result import TestResult
from ..models.enums import AccuracyStatus


class CLIReporter:
    """Generate human-readable CLI reports"""
    
    def generate_report(self, report: BenchmarkReport) -> str:
        """Generate formatted text report
        
        Args:
            report: BenchmarkReport with results and metrics
        
        Returns:
            Formatted text report string ready for print()
        """
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("LLM BENCHMARK REPORT")
        lines.append("=" * 70)
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append(f"API Endpoint: {report.api_url}")
        lines.append(f"Dataset Version: {report.dataset_version}")
        lines.append(f"Total Questions: {report.total_questions}")
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Accuracy: {report.accuracy_percentage:.1f}% ({report.passed_questions}/{report.total_questions} passed)")
        lines.append(f"Citation Coverage: {report.citation_coverage_percentage:.1f}% ({sum(1 for r in report.results if r.citations_found)}/{report.total_questions} responses)")
        
        if report.error_questions > 0:
            lines.append(f"API Errors: {report.error_questions} questions failed due to API errors")
        
        lines.append("")
        
        # Performance metrics
        if report.performance_metrics:
            lines.append("PERFORMANCE")
            lines.append("-" * 70)
            lines.append(f"  p50 (median): {report.performance_metrics.get('p50', 0):.0f} ms")
            lines.append(f"  p95:          {report.performance_metrics.get('p95', 0):.0f} ms")
            lines.append(f"  p99:          {report.performance_metrics.get('p99', 0):.0f} ms")
            lines.append(f"  Mean:         {report.performance_metrics.get('mean', 0):.0f} ms")
            
            # Warn if p95 exceeds constitution requirement
            p95 = report.performance_metrics.get('p95', 0)
            if p95 > 10000:
                lines.append(f"  ⚠ WARNING: p95 latency ({p95:.0f}ms) exceeds 10s constitution requirement!")
            
            lines.append("")
        
        # Failed questions
        failed = report.get_failed_results()
        if failed:
            lines.append("FAILED QUESTIONS")
            lines.append("-" * 70)
            for result in failed:
                lines.append(f"  {result.question_id}: {result.question_text}")
                
                if result.accuracy_status == AccuracyStatus.ERROR:
                    lines.append(f"    Status: API_ERROR")
                    lines.append(f"    Error: {result.error_message}")
                else:
                    lines.append(f"    Status: FAIL")
                    lines.append(f"    Expected: {result.question_text[:60]}...")
                    lines.append(f"    Got: {result.llm_response[:60]}...")
                    lines.append(f"    Similarity: {result.accuracy_score:.2f}")
                
                if not result.citations_found:
                    lines.append(f"    ⚠ No citations provided")
                
                lines.append("")
        
        # Slow questions (>10s)
        slow = report.get_slow_results(threshold_ms=10000)
        if slow:
            lines.append("SLOW RESPONSES (>10s)")
            lines.append("-" * 70)
            for result in slow:
                lines.append(f"  {result.question_id}: {result.latency_ms:.0f}ms - {result.question_text[:50]}...")
            lines.append("")
        
        # Footer
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def print_progress(self, current: int, total: int, question_id: str, status: str, latency_ms: float):
        """Print progress during benchmark execution
        
        Args:
            current: Current question number (1-indexed)
            total: Total number of questions
            question_id: Question identifier
            status: Status string (PASS/FAIL/ERROR)
            latency_ms: Response latency in milliseconds
        """
        status_symbol = "✓" if status == "PASS" else "✗"
        print(f"[{current}/{total}] {question_id}: {status_symbol} {status} ({latency_ms:.0f}ms)")
