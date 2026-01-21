"""Configuration management for LLM Benchmark Suite

Loads configuration from environment variables with sensible defaults.
Supports .env file for local development via python-dotenv.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class BenchmarkConfig:
    """Configuration settings for benchmark execution"""
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: Optional[float] = None,
        threshold: Optional[float] = None,
        ground_truth_path: Optional[str] = None,
        results_dir: Optional[str] = None,
        manifest_path: Optional[str] = None
    ):
        """Initialize configuration with environment variables as defaults
        
        Args:
            api_url: LLM API endpoint URL (required, no default)
            timeout: Request timeout in seconds (default: 5.0)
            threshold: Fuzzy matching threshold (default: 0.8)
            ground_truth_path: Path to ground truth YAML file
            results_dir: Directory for storing benchmark results
            manifest_path: Optional path to knowledge base manifest
        """
        self.api_url = api_url or os.getenv("BENCHMARK_API_URL")
        self.timeout = timeout or float(os.getenv("BENCHMARK_TIMEOUT", "5.0"))
        self.threshold = threshold or float(os.getenv("BENCHMARK_THRESHOLD", "0.8"))
        self.ground_truth_path = ground_truth_path or os.getenv(
            "BENCHMARK_GROUND_TRUTH",
            "tests/benchmark/ground_truth.yaml"
        )
        self.results_dir = results_dir or os.getenv(
            "BENCHMARK_RESULTS_DIR",
            "results"
        )
        self.manifest_path = manifest_path or os.getenv("BENCHMARK_MANIFEST_PATH")
    
    def validate(self) -> None:
        """Validate configuration settings
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not self.api_url:
            raise ValueError(
                "API URL is required. Set BENCHMARK_API_URL environment variable "
                "or provide --api-url argument."
            )
        
        if self.timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout}")
        
        if not (0.0 <= self.threshold <= 1.0):
            raise ValueError(
                f"Threshold must be between 0.0 and 1.0, got {self.threshold}"
            )
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"BenchmarkConfig(api_url={self.api_url!r}, "
            f"timeout={self.timeout}, threshold={self.threshold}, "
            f"ground_truth_path={self.ground_truth_path!r})"
        )


def load_config(**kwargs) -> BenchmarkConfig:
    """Load and validate configuration
    
    Args:
        **kwargs: Override values for configuration parameters
    
    Returns:
        Validated BenchmarkConfig instance
    
    Raises:
        ValueError: If configuration is invalid
    """
    config = BenchmarkConfig(**kwargs)
    config.validate()
    return config
