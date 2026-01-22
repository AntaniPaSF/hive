"""Basic tests to validate project setup."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that basic imports work."""
    from app import server
    assert server is not None


def test_benchmark_imports():
    """Test that benchmark module imports work."""
    from tests.benchmark import benchmark
    assert benchmark is not None


def test_project_structure():
    """Test that project structure is correct."""
    project_root = Path(__file__).parent.parent
    assert (project_root / "app").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "requirements.txt").exists()


def test_simple_math():
    """Simple test that always passes."""
    assert 1 + 1 == 2
    assert True
