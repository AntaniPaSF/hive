"""
Memory Profiling Utilities

Tools for tracking memory usage, detecting leaks, and monitoring resources:
- Memory snapshots
- Memory usage tracking
- Leak detection
- Resource monitoring
"""

import psutil
import tracemalloc
import gc
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time."""
    
    timestamp: datetime
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory usage as percentage
    python_allocated_mb: float  # Python-allocated memory
    python_peak_mb: float  # Peak Python memory
    num_objects: int  # Number of tracked objects


class MemoryProfiler:
    """Monitor and profile memory usage."""
    
    def __init__(self, enable_tracemalloc: bool = True):
        """
        Initialize memory profiler.
        
        Args:
            enable_tracemalloc: Whether to enable detailed Python memory tracking
        """
        self.process = psutil.Process(os.getpid())
        self.snapshots: List[MemorySnapshot] = []
        self.tracemalloc_enabled = enable_tracemalloc
        
        if self.tracemalloc_enabled and not tracemalloc.is_tracing():
            tracemalloc.start()
            logger.info("Tracemalloc enabled for detailed memory profiling")
    
    def take_snapshot(self) -> MemorySnapshot:
        """
        Take a snapshot of current memory usage.
        
        Returns:
            MemorySnapshot with current memory statistics
        """
        # Get process memory info
        mem_info = self.process.memory_info()
        mem_percent = self.process.memory_percent()
        
        # Get Python-specific memory info
        if self.tracemalloc_enabled and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            python_allocated_mb = current / 1024 / 1024
            python_peak_mb = peak / 1024 / 1024
        else:
            python_allocated_mb = 0.0
            python_peak_mb = 0.0
        
        # Count tracked objects
        num_objects = len(gc.get_objects())
        
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=mem_info.rss / 1024 / 1024,
            vms_mb=mem_info.vms / 1024 / 1024,
            percent=mem_percent,
            python_allocated_mb=python_allocated_mb,
            python_peak_mb=python_peak_mb,
            num_objects=num_objects
        )
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def get_current_memory(self) -> Dict[str, float]:
        """
        Get current memory usage without storing snapshot.
        
        Returns:
            Dictionary with memory metrics
        """
        mem_info = self.process.memory_info()
        
        result = {
            "rss_mb": mem_info.rss / 1024 / 1024,
            "vms_mb": mem_info.vms / 1024 / 1024,
            "percent": self.process.memory_percent(),
        }
        
        if self.tracemalloc_enabled and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            result["python_mb"] = current / 1024 / 1024
            result["python_peak_mb"] = peak / 1024 / 1024
        
        return result
    
    def detect_leak(self, threshold_mb: float = 10.0) -> Optional[Dict]:
        """
        Detect potential memory leaks by comparing snapshots.
        
        Args:
            threshold_mb: Memory increase threshold to consider as leak
        
        Returns:
            Dictionary with leak information if detected, None otherwise
        """
        if len(self.snapshots) < 2:
            return None
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        
        rss_increase = last.rss_mb - first.rss_mb
        python_increase = last.python_allocated_mb - first.python_allocated_mb
        objects_increase = last.num_objects - first.num_objects
        
        if rss_increase > threshold_mb:
            return {
                "detected": True,
                "rss_increase_mb": rss_increase,
                "python_increase_mb": python_increase,
                "objects_increase": objects_increase,
                "duration_seconds": (last.timestamp - first.timestamp).total_seconds(),
                "first_snapshot": first,
                "last_snapshot": last,
            }
        
        return None
    
    def get_top_memory_allocations(self, limit: int = 10) -> List[Tuple]:
        """
        Get top memory allocations tracked by tracemalloc.
        
        Args:
            limit: Number of top allocations to return
        
        Returns:
            List of (filename, lineno, size_mb, count) tuples
        """
        if not self.tracemalloc_enabled or not tracemalloc.is_tracing():
            logger.warning("Tracemalloc not enabled")
            return []
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        result = []
        for stat in top_stats[:limit]:
            result.append((
                stat.filename,
                stat.lineno,
                stat.size / 1024 / 1024,  # Convert to MB
                stat.count
            ))
        
        return result
    
    def compare_snapshots(
        self,
        snapshot1: MemorySnapshot,
        snapshot2: MemorySnapshot
    ) -> Dict[str, float]:
        """
        Compare two memory snapshots.
        
        Args:
            snapshot1: First snapshot
            snapshot2: Second snapshot
        
        Returns:
            Dictionary with differences
        """
        return {
            "rss_diff_mb": snapshot2.rss_mb - snapshot1.rss_mb,
            "vms_diff_mb": snapshot2.vms_mb - snapshot1.vms_mb,
            "percent_diff": snapshot2.percent - snapshot1.percent,
            "python_diff_mb": snapshot2.python_allocated_mb - snapshot1.python_allocated_mb,
            "objects_diff": snapshot2.num_objects - snapshot1.num_objects,
            "duration_seconds": (snapshot2.timestamp - snapshot1.timestamp).total_seconds(),
        }
    
    def print_snapshot(self, snapshot: MemorySnapshot):
        """Print formatted snapshot information."""
        print(f"\nMemory Snapshot ({snapshot.timestamp.strftime('%H:%M:%S')}):")
        print(f"  RSS: {snapshot.rss_mb:.2f} MB")
        print(f"  VMS: {snapshot.vms_mb:.2f} MB")
        print(f"  Memory %: {snapshot.percent:.1f}%")
        if self.tracemalloc_enabled:
            print(f"  Python Allocated: {snapshot.python_allocated_mb:.2f} MB")
            print(f"  Python Peak: {snapshot.python_peak_mb:.2f} MB")
        print(f"  Tracked Objects: {snapshot.num_objects:,}")
    
    def print_summary(self):
        """Print summary of all snapshots."""
        if not self.snapshots:
            print("No snapshots taken")
            return
        
        print("\n" + "="*60)
        print("MEMORY PROFILING SUMMARY")
        print("="*60)
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        
        print(f"Duration: {(last.timestamp - first.timestamp).total_seconds():.1f}s")
        print(f"Snapshots: {len(self.snapshots)}")
        
        print(f"\nInitial Memory:")
        print(f"  RSS: {first.rss_mb:.2f} MB")
        print(f"  Python: {first.python_allocated_mb:.2f} MB")
        
        print(f"\nFinal Memory:")
        print(f"  RSS: {last.rss_mb:.2f} MB")
        print(f"  Python: {last.python_allocated_mb:.2f} MB")
        
        print(f"\nChange:")
        print(f"  RSS: {last.rss_mb - first.rss_mb:+.2f} MB")
        print(f"  Python: {last.python_allocated_mb - first.python_allocated_mb:+.2f} MB")
        print(f"  Objects: {last.num_objects - first.num_objects:+,}")
        
        # Check for leaks
        leak_info = self.detect_leak(threshold_mb=10.0)
        if leak_info:
            print(f"\n⚠️  POTENTIAL MEMORY LEAK DETECTED:")
            print(f"  Increase: {leak_info['rss_increase_mb']:.2f} MB")
        else:
            print(f"\n✓ No significant memory leaks detected")
        
        print("="*60)
    
    def reset(self):
        """Reset profiler and clear snapshots."""
        self.snapshots.clear()
        if self.tracemalloc_enabled and tracemalloc.is_tracing():
            tracemalloc.clear_traces()
        gc.collect()
    
    def stop(self):
        """Stop memory profiling."""
        if self.tracemalloc_enabled and tracemalloc.is_tracing():
            tracemalloc.stop()
        logger.info("Memory profiling stopped")


class ResourceMonitor:
    """Monitor system resources (CPU, memory, disk)."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.process = psutil.Process(os.getpid())
    
    def get_cpu_usage(self) -> Dict[str, float]:
        """
        Get CPU usage information.
        
        Returns:
            Dictionary with CPU metrics
        """
        return {
            "process_percent": self.process.cpu_percent(interval=0.1),
            "system_percent": psutil.cpu_percent(interval=0.1),
            "num_cpus": psutil.cpu_count(),
        }
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get memory usage information.
        
        Returns:
            Dictionary with memory metrics
        """
        mem_info = self.process.memory_info()
        sys_mem = psutil.virtual_memory()
        
        return {
            "process_rss_mb": mem_info.rss / 1024 / 1024,
            "process_vms_mb": mem_info.vms / 1024 / 1024,
            "process_percent": self.process.memory_percent(),
            "system_total_mb": sys_mem.total / 1024 / 1024,
            "system_available_mb": sys_mem.available / 1024 / 1024,
            "system_used_percent": sys_mem.percent,
        }
    
    def get_disk_usage(self) -> Dict[str, float]:
        """
        Get disk usage information.
        
        Returns:
            Dictionary with disk metrics
        """
        disk = psutil.disk_usage('/')
        
        return {
            "total_gb": disk.total / 1024 / 1024 / 1024,
            "used_gb": disk.used / 1024 / 1024 / 1024,
            "free_gb": disk.free / 1024 / 1024 / 1024,
            "percent": disk.percent,
        }
    
    def get_all_metrics(self) -> Dict:
        """
        Get all resource metrics.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            "cpu": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "timestamp": datetime.now().isoformat(),
        }
    
    def print_metrics(self):
        """Print formatted resource metrics."""
        metrics = self.get_all_metrics()
        
        print("\n" + "="*60)
        print("RESOURCE METRICS")
        print("="*60)
        
        print("\nCPU:")
        print(f"  Process: {metrics['cpu']['process_percent']:.1f}%")
        print(f"  System: {metrics['cpu']['system_percent']:.1f}%")
        print(f"  CPUs: {metrics['cpu']['num_cpus']}")
        
        print("\nMemory:")
        print(f"  Process RSS: {metrics['memory']['process_rss_mb']:.2f} MB")
        print(f"  Process %: {metrics['memory']['process_percent']:.1f}%")
        print(f"  System Available: {metrics['memory']['system_available_mb']:.2f} MB")
        print(f"  System Used: {metrics['memory']['system_used_percent']:.1f}%")
        
        print("\nDisk:")
        print(f"  Used: {metrics['disk']['used_gb']:.2f} GB / {metrics['disk']['total_gb']:.2f} GB")
        print(f"  Free: {metrics['disk']['free_gb']:.2f} GB")
        print(f"  Used %: {metrics['disk']['percent']:.1f}%")
        
        print("="*60)


# Convenience functions
def profile_memory(func):
    """
    Decorator to profile memory usage of a function.
    
    Usage:
        @profile_memory
        def my_function():
            # function code
    """
    def wrapper(*args, **kwargs):
        profiler = MemoryProfiler()
        
        # Take before snapshot
        before = profiler.take_snapshot()
        
        # Run function
        result = func(*args, **kwargs)
        
        # Take after snapshot
        after = profiler.take_snapshot()
        
        # Print comparison
        diff = profiler.compare_snapshots(before, after)
        print(f"\nMemory usage for {func.__name__}:")
        print(f"  RSS change: {diff['rss_diff_mb']:+.2f} MB")
        print(f"  Python change: {diff['python_diff_mb']:+.2f} MB")
        print(f"  Duration: {diff['duration_seconds']:.3f}s")
        
        return result
    
    return wrapper


if __name__ == "__main__":
    # Example usage
    profiler = MemoryProfiler()
    monitor = ResourceMonitor()
    
    print("Taking initial snapshot...")
    profiler.take_snapshot()
    
    # Simulate some work
    data = [i for i in range(1000000)]
    
    print("Taking second snapshot...")
    profiler.take_snapshot()
    
    # Clear data
    del data
    gc.collect()
    
    print("Taking final snapshot...")
    profiler.take_snapshot()
    
    profiler.print_summary()
    monitor.print_metrics()
