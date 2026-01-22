"""
Comprehensive Test Suite Runner

Orchestrates all test types and generates comprehensive reports:
- Unit tests
- Integration tests
- Performance benchmarks
- Accuracy evaluation
- Retrieval metrics
- Load tests
- Memory profiling
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Orchestrates comprehensive test suite execution."""
    
    def __init__(self):
        """Initialize test runner."""
        self.results: Dict[str, Dict] = {}
        self.start_time = None
        self.end_time = None
    
    def run_test_suite(
        self,
        suite_name: str,
        test_path: str,
        description: str,
        args: List[str] = None
    ) -> Dict:
        """
        Run a test suite and capture results.
        
        Args:
            suite_name: Name of the test suite
            test_path: Path to test file or directory
            description: Description of what's being tested
            args: Additional pytest arguments
        
        Returns:
            Dictionary with test results
        """
        print(f"\n{'='*80}")
        print(f"Running: {suite_name}")
        print(f"Description: {description}")
        print(f"{'='*80}")
        
        # Build command
        cmd = ["python", "-m", "pytest", test_path, "-v"]
        if args:
            cmd.extend(args)
        
        # Run tests
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            duration = time.time() - start
            
            # Parse output
            output = result.stdout + result.stderr
            
            # Try to extract test counts
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            skipped = output.count(" SKIPPED")
            errors = output.count(" ERROR")
            
            success = result.returncode == 0
            
            result_dict = {
                "suite_name": suite_name,
                "description": description,
                "success": success,
                "duration": duration,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "errors": errors,
                "return_code": result.returncode,
                "output_snippet": output[-500:] if len(output) > 500 else output
            }
            
            self.results[suite_name] = result_dict
            
            # Print summary
            status = "✓ PASSED" if success else "✗ FAILED"
            print(f"\nStatus: {status}")
            print(f"Duration: {duration:.2f}s")
            print(f"Tests: {passed} passed, {failed} failed, {skipped} skipped, {errors} errors")
            
            return result_dict
        
        except Exception as e:
            print(f"✗ ERROR: {e}")
            error_dict = {
                "suite_name": suite_name,
                "description": description,
                "success": False,
                "error": str(e),
                "duration": time.time() - start
            }
            self.results[suite_name] = error_dict
            return error_dict
    
    def run_all_tests(self, quick_mode: bool = False):
        """
        Run all test suites.
        
        Args:
            quick_mode: If True, skip slow tests
        """
        self.start_time = datetime.now()
        
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST SUITE")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {'Quick' if quick_mode else 'Full'}")
        print("="*80)
        
        # 1. Unit Tests
        self.run_test_suite(
            "Unit Tests - Chunker",
            "tests/unit/test_chunker.py",
            "Test semantic chunking functionality",
            ["-q"] if quick_mode else []
        )
        
        self.run_test_suite(
            "Unit Tests - Retriever",
            "tests/unit/test_retriever.py",
            "Test retrieval interface",
            ["-q"] if quick_mode else []
        )
        
        self.run_test_suite(
            "Unit Tests - RAG Pipeline",
            "tests/unit/test_rag.py",
            "Test RAG pipeline with mock LLM",
            ["-q"] if quick_mode else []
        )
        
        # 2. Integration Tests
        self.run_test_suite(
            "Integration Tests - API",
            "tests/integration/test_api.py",
            "Test REST API endpoints",
            ["-q"] if quick_mode else []
        )
        
        # 3. Performance Benchmarks
        if not quick_mode:
            self.run_test_suite(
                "Performance Benchmarks",
                "tests/performance/test_benchmarks.py",
                "Measure response times and throughput",
                ["-s"]  # Show print output
            )
        
        # 4. Accuracy Evaluation
        if not quick_mode:
            self.run_test_suite(
                "Accuracy Evaluation",
                "tests/evaluation/test_accuracy.py",
                "Evaluate answer quality and citations",
                ["-s"]
            )
        
        # 5. Retrieval Metrics
        if not quick_mode:
            self.run_test_suite(
                "Retrieval Metrics",
                "tests/evaluation/test_retrieval.py",
                "Measure precision, recall, and NDCG",
                ["-s"]
            )
        
        # 6. Load Tests
        if not quick_mode:
            self.run_test_suite(
                "Load Tests",
                "tests/load/test_concurrent.py",
                "Test concurrent request handling",
                ["-s", "-k", "test_concurrent"]  # Run only concurrent tests
            )
        
        self.end_time = datetime.now()
    
    def generate_report(self) -> str:
        """
        Generate comprehensive test report.
        
        Returns:
            Formatted report string
        """
        if not self.results:
            return "No test results available."
        
        duration = (self.end_time - self.start_time).total_seconds()
        
        # Count results
        total_suites = len(self.results)
        passed_suites = sum(1 for r in self.results.values() if r.get("success", False))
        failed_suites = total_suites - passed_suites
        
        total_tests = sum(r.get("passed", 0) + r.get("failed", 0) + r.get("skipped", 0) 
                         for r in self.results.values())
        total_passed = sum(r.get("passed", 0) for r in self.results.values())
        total_failed = sum(r.get("failed", 0) for r in self.results.values())
        total_skipped = sum(r.get("skipped", 0) for r in self.results.values())
        
        # Build report
        report = []
        report.append("\n" + "="*80)
        report.append("COMPREHENSIVE TEST REPORT")
        report.append("="*80)
        report.append(f"Started:  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Finished: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Duration: {duration:.2f} seconds")
        report.append("")
        report.append("SUMMARY:")
        report.append(f"  Test Suites: {passed_suites}/{total_suites} passed")
        report.append(f"  Total Tests: {total_tests}")
        report.append(f"  Passed: {total_passed}")
        report.append(f"  Failed: {total_failed}")
        report.append(f"  Skipped: {total_skipped}")
        report.append(f"  Success Rate: {total_passed/total_tests*100:.1f}%" if total_tests > 0 else "  Success Rate: N/A")
        report.append("")
        report.append("SUITE RESULTS:")
        
        for suite_name, result in self.results.items():
            status = "✓" if result.get("success", False) else "✗"
            duration_str = f"{result.get('duration', 0):.2f}s"
            
            passed = result.get("passed", 0)
            failed = result.get("failed", 0)
            skipped = result.get("skipped", 0)
            
            report.append(f"\n  {status} {suite_name} ({duration_str})")
            report.append(f"    {result.get('description', '')}")
            if passed + failed + skipped > 0:
                report.append(f"    Tests: {passed} passed, {failed} failed, {skipped} skipped")
            if "error" in result:
                report.append(f"    Error: {result['error']}")
        
        report.append("\n" + "="*80)
        
        if failed_suites == 0:
            report.append("✓ ALL TEST SUITES PASSED")
        else:
            report.append(f"✗ {failed_suites} TEST SUITE(S) FAILED")
        
        report.append("="*80 + "\n")
        
        return "\n".join(report)
    
    def save_report(self, filename: str = "test_report.txt"):
        """
        Save report to file.
        
        Args:
            filename: Output filename
        """
        report = self.generate_report()
        
        report_path = project_root / filename
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_path}")
    
    def save_json_results(self, filename: str = "test_results.json"):
        """
        Save results as JSON.
        
        Args:
            filename: Output filename
        """
        data = {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "results": self.results
        }
        
        json_path = project_root / filename
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"JSON results saved to: {json_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run comprehensive test suite")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (skip performance, accuracy, load tests)"
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save report to file"
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save results as JSON"
    )
    
    args = parser.parse_args()
    
    # Run tests
    runner = TestRunner()
    runner.run_all_tests(quick_mode=args.quick)
    
    # Print report
    print(runner.generate_report())
    
    # Save if requested
    if args.save_report:
        runner.save_report()
    
    if args.save_json:
        runner.save_json_results()
    
    # Exit with appropriate code
    failed_suites = sum(1 for r in runner.results.values() if not r.get("success", False))
    sys.exit(0 if failed_suites == 0 else 1)


if __name__ == "__main__":
    main()
