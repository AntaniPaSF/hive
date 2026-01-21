# Research: LLM Benchmark Test Suite

**Feature**: 001-llm-benchmark-suite  
**Date**: 2026-01-21  
**Status**: Completed

## Purpose

Resolve technical unknowns and establish best practices for implementing a Python-based benchmark suite that validates LLM accuracy, citation coverage, and performance using fuzzy matching and dual-format reporting.

---

## 1. Fuzzy Matching Algorithm Selection

### Decision: Use python-Levenshtein for distance ratio + custom keyword overlap

**Rationale**:
- `python-Levenshtein` provides fast C-based implementation of Levenshtein distance
- Ratio function normalizes distance to [0,1] range (directly comparable to 0.8 threshold)
- Keyword overlap complements character-based matching for cases where word order differs
- Both methods are deterministic and reproducible across environments

**Alternatives Considered**:
- **difflib.SequenceMatcher**: Python stdlib, slower than C implementation, good for debugging
- **RapidFuzz**: Faster but adds heavier dependency; overkill for 20-question dataset
- **Sentence transformers/embeddings**: Semantic similarity requires model download (violates Self-Contained principle for MVP)

**Implementation**:
```python
from Levenshtein import ratio as levenshtein_ratio

def fuzzy_match(expected: str, actual: str, threshold=0.8) -> bool:
    # Normalize whitespace and case
    exp_norm = " ".join(expected.lower().split())
    act_norm = " ".join(actual.lower().split())
    
    # Levenshtein ratio
    lev_score = levenshtein_ratio(exp_norm, act_norm)
    if lev_score >= threshold:
        return True
    
    # Keyword overlap fallback
    exp_words = set(exp_norm.split())
    act_words = set(act_norm.split())
    overlap = len(exp_words & act_words) / len(exp_words)
    return overlap >= 0.70
```

**Trade-offs**:
- Pro: Fast, reproducible, no model downloads
- Pro: Handles typos, reordering, paraphrasing to reasonable degree
- Con: Misses semantic equivalence (e.g., "5 business days" vs "one work week")
- Con: Threshold tuning needed based on question types

**Post-MVP Enhancement**: Add semantic similarity using lightweight embeddings (sentence-transformers with CPU-only models) for P2/P3 stories.

---

## 2. YAML Schema for Ground Truth Dataset

### Decision: Use structured YAML with version metadata and multi-variation support

**Rationale**:
- YAML supports comments (QA engineers can document question intent)
- Hierarchical structure enables metadata (version, category, tags)
- Readable diffs in Git for version control
- PyYAML is lightweight and stdlib-compatible

**Schema**:
```yaml
version: "1.0"
created: "2026-01-21"
description: "Benchmark dataset for HR chatbot accuracy validation"

questions:
  - id: "Q001"
    category: "vacation_policy"
    question: "How do I request vacation time?"
    expected_answer: "Submit a vacation request through the employee portal at least 2 weeks in advance."
    variations:
      - "Submit vacation request via employee portal 2 weeks ahead."
      - "Use the portal to request time off with 2-week notice."
    citation_required: true
    tags: ["time-off", "portal", "process"]
  
  - id: "Q002"
    category: "expense_policy"
    question: "What is the maximum daily meal allowance for business travel?"
    expected_answer: "$75 per day for domestic travel, $100 for international."
    variations: []
    citation_required: true
    tags: ["expenses", "travel", "limits"]
```

**Alternatives Considered**:
- **JSON**: More verbose, no comment support, harder for non-developers
- **CSV**: Simpler but can't represent variations/metadata cleanly
- **Python dict in .py file**: Requires code changes to update dataset

**Trade-offs**:
- Pro: Human-editable, version-controllable, extensible
- Pro: Supports optional fields (variations, tags) without breaking parser
- Con: Indentation-sensitive (but QA engineers familiar with YAML from CI/CD)

---

## 3. Performance Metrics Calculation (p50/p95/p99)

### Decision: Use NumPy's percentile function with linear interpolation

**Rationale**:
- NumPy is standard for numerical computing in Python
- `numpy.percentile()` handles edge cases (small datasets, duplicates)
- Linear interpolation provides smooth percentile estimates
- Deterministic results for reproducibility

**Implementation**:
```python
import numpy as np

def calculate_percentiles(latencies_ms: list[float]) -> dict:
    arr = np.array(latencies_ms)
    return {
        "p50": np.percentile(arr, 50),
        "p95": np.percentile(arr, 95),
        "p99": np.percentile(arr, 99),
        "mean": np.mean(arr),
        "median": np.median(arr),
        "std_dev": np.std(arr)
    }
```

**Alternatives Considered**:
- **Python statistics module**: Lacks percentile support before 3.8; less flexible
- **Custom implementation**: Error-prone, less tested
- **Pandas**: Heavier dependency for simple percentile calculation

**Trade-offs**:
- Pro: Industry-standard, well-tested, fast
- Pro: Provides additional metrics (mean, std dev) for diagnostics
- Con: Adds NumPy dependency (but widely used, CPU-only)

---

## 4. Report Generation Strategy

### Decision: Template-based text report + structured JSON export

**Rationale**:
- Text template provides immediate human feedback during development
- JSON export enables CI/CD integration and trend analysis
- Dual format satisfies FR-006 requirement
- Templates are easier to customize than hardcoded formatting logic

**Text Template**:
```
=== LLM Benchmark Report ===
Timestamp: {timestamp}
API Endpoint: {api_url}
Total Questions: {total_questions}

Accuracy: {accuracy_pct}% ({passed}/{total})
Citation Coverage: {citation_pct}%

Performance:
  p50: {p50_ms} ms
  p95: {p95_ms} ms
  p99: {p99_ms} ms

Failed Questions:
  Q003: Expected "X", got "Y" (similarity: 0.65)
  Q007: API_ERROR (timeout after 5s)
```

**JSON Structure**:
```json
{
  "timestamp": "2026-01-21T14:30:15Z",
  "api_url": "http://localhost:8080",
  "summary": {
    "total_questions": 20,
    "passed": 17,
    "accuracy_pct": 85.0,
    "citation_coverage_pct": 100.0
  },
  "performance": {
    "p50_ms": 2340,
    "p95_ms": 4580,
    "p99_ms": 5120
  },
  "results": [
    {
      "id": "Q001",
      "question": "...",
      "status": "PASS",
      "latency_ms": 2100,
      "citations_found": 1
    }
  ]
}
```

**Alternatives Considered**:
- **HTML report**: Nice but requires browser; post-MVP dashboard feature
- **Markdown report**: Git-friendly but harder to parse for automation
- **SQLite database**: Overkill for flat result storage; adds complexity

**Trade-offs**:
- Pro: Dual format satisfies both human and machine consumers
- Pro: JSON schema easily extended (add fields without breaking parsers)
- Con: Duplicate information (but negligible for 20-question dataset)

---

## 5. HTTP Request Handling & Retry Logic

### Decision: Use requests library with exponential backoff for retries

**Rationale**:
- `requests` is Python standard for HTTP clients
- Exponential backoff prevents thundering herd on transient failures
- 5-second timeout per FR-011 clarification
- Single retry keeps test execution fast while handling transient issues

**Implementation**:
```python
import requests
from time import sleep

def send_question(api_url: str, question: str, timeout=5, retries=1) -> dict:
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                f"{api_url}/ask",
                json={"question": question},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < retries:
                sleep(2 ** attempt)  # 0s, 2s backoff
                continue
            return {"error": "API_ERROR", "message": str(e)}
```

**Alternatives Considered**:
- **urllib**: Stdlib but more verbose, no built-in retry logic
- **httpx**: Modern async support but overkill for sequential benchmark
- **Custom socket handling**: Too low-level, error-prone

**Trade-offs**:
- Pro: Simple, reliable, widely used
- Pro: Timeout enforcement prevents hanging on slow API
- Con: Synchronous (but sequential execution is MVP requirement)

---

## 6. Configuration Management

### Decision: Environment variables with .env file support + CLI overrides

**Rationale**:
- Aligns with existing project pattern (see `app/core/config.py`)
- Environment variables work in Docker, CI/CD, and local dev
- CLI arguments provide flexibility for ad-hoc runs
- Defaults for localhost development

**Configuration Hierarchy** (highest priority first):
1. CLI arguments (`--api-url`, `--timeout`, `--threshold`)
2. Environment variables (`BENCHMARK_API_URL`, `BENCHMARK_TIMEOUT`)
3. `.env` file in project root
4. Hardcoded defaults (localhost:8080, 5s timeout, 0.8 threshold)

**Implementation**:
```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class BenchmarkConfig:
    api_url: str
    timeout_seconds: int
    fuzzy_threshold: float
    ground_truth_path: str
    results_dir: str

    @classmethod
    def from_env(cls, cli_overrides: dict = None):
        load_dotenv()
        config = cls(
            api_url=os.getenv("BENCHMARK_API_URL", "http://localhost:8080"),
            timeout_seconds=int(os.getenv("BENCHMARK_TIMEOUT", "5")),
            fuzzy_threshold=float(os.getenv("BENCHMARK_THRESHOLD", "0.8")),
            ground_truth_path=os.getenv("BENCHMARK_GROUND_TRUTH", "tests/benchmark/ground_truth.yaml"),
            results_dir=os.getenv("BENCHMARK_RESULTS_DIR", "results")
        )
        if cli_overrides:
            for key, value in cli_overrides.items():
                if value is not None:
                    setattr(config, key, value)
        return config
```

**Alternatives Considered**:
- **Config file (YAML/JSON)**: Extra file to manage; env vars more flexible
- **Command-line only**: Hard to reproduce across environments
- **Hardcoded constants**: Inflexible, violates Reproducible principle

---

## 7. Citation Validation Strategy

### Decision: Structural validation (presence + schema) + optional manifest check (P2)

**Rationale**:
- P1 MVP: Validate citation presence and structure (document + section fields)
- P2: Cross-reference against knowledge base manifest to detect hallucinations
- Separates validation concerns: schema vs. correctness
- Aligns with User Story 4 (P2) prioritization

**P1 Implementation**:
```python
def validate_citation(citation: dict) -> tuple[bool, str]:
    """Check if citation has required fields."""
    if not isinstance(citation, dict):
        return False, "Citation must be an object"
    if not citation.get("document"):
        return False, "Citation missing 'document' field"
    if not citation.get("section"):
        return False, "Citation missing 'section' field"
    return True, ""

def check_citations(response: dict) -> dict:
    citations = response.get("citations", [])
    if not citations:
        return {"present": False, "count": 0, "valid": False}
    
    valid_citations = []
    for cit in citations:
        is_valid, _ = validate_citation(cit)
        if is_valid:
            valid_citations.append(cit)
    
    return {
        "present": len(citations) > 0,
        "count": len(citations),
        "valid": len(valid_citations) == len(citations),
        "citations": valid_citations
    }
```

**P2 Enhancement** (User Story 4):
```python
def validate_against_manifest(citation: dict, manifest: dict) -> bool:
    """Check if citation references real document and section."""
    doc_name = citation["document"]
    section = citation["section"]
    
    if doc_name not in manifest["documents"]:
        return False
    
    doc_sections = manifest["documents"][doc_name]["sections"]
    return section in doc_sections
```

---

## Summary of Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Fuzzy Matching** | python-Levenshtein + keyword overlap | Fast, deterministic, no model downloads |
| **Data Format** | YAML (PyYAML) | Human-readable, comments, version control |
| **Performance Metrics** | NumPy percentile | Industry standard, handles edge cases |
| **Reporting** | Text template + JSON | Dual format (human + machine) |
| **HTTP Client** | requests with retry | Simple, reliable, exponential backoff |
| **Configuration** | Environment variables + CLI | Flexible, aligns with project patterns |
| **Citation Validation** | Structural check (P1) + manifest (P2) | Phased approach, clear separation |

All dependencies are open-source, CPU-only, and self-contained (no cloud APIs). Total added dependencies: **5** (PyYAML, python-Levenshtein, requests, numpy, python-dotenv).
