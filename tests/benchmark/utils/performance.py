"""Performance metric calculation utilities"""

import numpy as np
from typing import List, Dict


def calculate_percentiles(latencies: List[float]) -> Dict[str, float]:
    """Calculate p50, p95, and p99 latency percentiles
    
    Args:
        latencies: List of latency values in milliseconds
    
    Returns:
        Dictionary with p50, p95, p99 keys and values in milliseconds
        Returns empty dict if no latencies provided
    
    Example:
        >>> calculate_percentiles([100, 200, 300, 400, 500])
        {'p50': 300.0, 'p95': 480.0, 'p99': 496.0, 'mean': 300.0, 'min': 100.0, 'max': 500.0}
    """
    if not latencies:
        return {}
    
    latency_array = np.array(latencies)
    
    return {
        "p50": float(np.percentile(latency_array, 50)),
        "p95": float(np.percentile(latency_array, 95)),
        "p99": float(np.percentile(latency_array, 99)),
        "mean": float(np.mean(latency_array)),
        "min": float(np.min(latency_array)),
        "max": float(np.max(latency_array))
    }
