"""JSON Reporter - Machine-readable timestamped results

Exports benchmark results to JSON files with timestamped filenames.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from ..models.report import BenchmarkReport


class JSONReporter:
    """Generate machine-readable JSON reports"""
    
    def __init__(self, results_dir: str = "results"):
        """Initialize reporter with results directory
        
        Args:
            results_dir: Directory for storing JSON result files
        """
        self.results_dir = Path(results_dir)
    
    def save_report(self, report: BenchmarkReport) -> str:
        """Save report to timestamped JSON file
        
        Args:
            report: BenchmarkReport to save
        
        Returns:
            Path to saved JSON file
        
        Raises:
            OSError: If directory creation or file write fails
        """
        # Ensure results directory exists
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"benchmark_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert report to dict and save
        report_dict = report.to_dict()
        
        with open(filepath, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        return str(filepath)
    
    def load_report(self, filepath: str) -> dict:
        """Load report from JSON file
        
        Args:
            filepath: Path to JSON report file
        
        Returns:
            Report data as dictionary
        
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        with open(filepath, "r") as f:
            return json.load(f)
    
    def list_reports(self) -> list[str]:
        """List all benchmark reports in results directory
        
        Returns:
            List of report filenames sorted by timestamp (newest first)
        """
        if not self.results_dir.exists():
            return []
        
        reports = list(self.results_dir.glob("benchmark_*.json"))
        # Sort by filename (timestamp) in reverse (newest first)
        reports.sort(reverse=True)
        
        return [str(r) for r in reports]
    
    def get_latest_report(self) -> str | None:
        """Get path to most recent benchmark report
        
        Returns:
            Path to latest report or None if no reports exist
        """
        reports = self.list_reports()
        return reports[0] if reports else None
