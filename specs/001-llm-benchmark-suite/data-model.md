# Data Model: LLM Benchmark Test Suite

**Feature**: 001-llm-benchmark-suite  
**Date**: 2026-01-21

## Overview

This document defines the data entities used by the benchmark suite for loading ground truth questions, capturing test results, and generating reports. All entities are Python dataclasses with clear validation rules and serialization support.

---

## Core Entities

### 1. BenchmarkQuestion

Represents a single test case loaded from `ground_truth.yaml`.

**Fields**:
- `id` (str): Unique identifier (e.g., "Q001", "Q002")
- `category` (str): Question domain (e.g., "vacation_policy", "expense_policy")
- `question` (str): The question text to send to the LLM API
- `expected_answer` (str): Primary expected answer for accuracy validation
- `variations` (list[str]): Alternative acceptable answer formulations (optional, default=[])
- `citation_required` (bool): Whether citation is mandatory for this question (default=True)
- `tags` (list[str]): Metadata tags for filtering/grouping (optional, default=[])

**Validation Rules**:
- `id` must be non-empty and unique within dataset
- `question` and `expected_answer` must be non-empty strings
- `category` must be non-empty (for reporting/filtering)

**Serialization**:
```python
@dataclass
class BenchmarkQuestion:
    id: str
    category: str
    question: str
    expected_answer: str
    variations: list[str] = field(default_factory=list)
    citation_required: bool = True
    tags: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id or not self.question or not self.expected_answer:
            raise ValueError("id, question, and expected_answer are required")
        if not self.category:
            raise ValueError("category is required")
```

**Example**:
```python
question = BenchmarkQuestion(
    id="Q001",
    category="vacation_policy",
    question="How do I request vacation time?",
    expected_answer="Submit a vacation request through the employee portal at least 2 weeks in advance.",
    variations=[
        "Submit vacation request via employee portal 2 weeks ahead.",
        "Use the portal to request time off with 2-week notice."
    ],
    citation_required=True,
    tags=["time-off", "portal", "process"]
)
```

---

### 2. TestResult

Captures the outcome of testing one benchmark question against the LLM API.

**Fields**:
- `question_id` (str): References BenchmarkQuestion.id
- `question_text` (str): The question that was asked (for report readability)
- `llm_response` (str): The answer text returned by the LLM
- `citations_found` (list[dict]): Citations extracted from response (format: `{"document": str, "section": str}`)
- `accuracy_status` (str): Enum: "PASS", "FAIL", "ERROR"
- `accuracy_score` (float): Fuzzy match score (0.0-1.0)
- `citation_status` (str): Enum: "PRESENT", "MISSING", "INVALID"
- `latency_ms` (float): Response time in milliseconds
- `error_message` (str | None): Error details if status="ERROR"
- `timestamp` (str): ISO 8601 timestamp of test execution

**Validation Rules**:
- `accuracy_status` must be one of: "PASS", "FAIL", "ERROR"
- `citation_status` must be one of: "PRESENT", "MISSING", "INVALID"
- `latency_ms` must be non-negative
- `accuracy_score` must be in range [0.0, 1.0]

**Serialization**:
```python
from enum import Enum
from datetime import datetime

class AccuracyStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"

class CitationStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    INVALID = "INVALID"

@dataclass
class TestResult:
    question_id: str
    question_text: str
    llm_response: str
    citations_found: list[dict]
    accuracy_status: AccuracyStatus
    accuracy_score: float
    citation_status: CitationStatus
    latency_ms: float
    error_message: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self):
        if not (0.0 <= self.accuracy_score <= 1.0):
            raise ValueError("accuracy_score must be in [0.0, 1.0]")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
    
    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "llm_response": self.llm_response,
            "citations_found": self.citations_found,
            "accuracy_status": self.accuracy_status.value,
            "accuracy_score": self.accuracy_score,
            "citation_status": self.citation_status.value,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }
```

**Example**:
```python
result = TestResult(
    question_id="Q001",
    question_text="How do I request vacation time?",
    llm_response="You can submit a vacation request via the employee portal with 2 weeks notice.",
    citations_found=[{"document": "HR_Policy_2026.md", "section": "Time Off"}],
    accuracy_status=AccuracyStatus.PASS,
    accuracy_score=0.87,
    citation_status=CitationStatus.PRESENT,
    latency_ms=2340.5
)
```

---

### 3. GroundTruthDataset

Collection of BenchmarkQuestions loaded from YAML file with metadata.

**Fields**:
- `version` (str): Dataset version (e.g., "1.0", "1.1")
- `created` (str): Creation date (ISO 8601)
- `description` (str): Dataset purpose/scope description
- `questions` (list[BenchmarkQuestion]): List of benchmark questions

**Validation Rules**:
- `questions` list must not be empty
- All `question.id` values must be unique
- `version` must follow semantic versioning (major.minor or major.minor.patch)

**Serialization**:
```python
@dataclass
class GroundTruthDataset:
    version: str
    created: str
    description: str
    questions: list[BenchmarkQuestion]
    
    def __post_init__(self):
        if not self.questions:
            raise ValueError("Dataset must contain at least one question")
        
        # Check for duplicate IDs
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate question IDs found in dataset")
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "GroundTruthDataset":
        import yaml
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        
        questions = [
            BenchmarkQuestion(**q) for q in data["questions"]
        ]
        
        return cls(
            version=data["version"],
            created=data["created"],
            description=data["description"],
            questions=questions
        )
```

**Example YAML**:
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
    citation_required: true
    tags: ["time-off", "portal"]
```

---

### 4. BenchmarkReport

Aggregated results from a complete benchmark run with summary statistics.

**Fields**:
- `timestamp` (str): When the benchmark run started (ISO 8601)
- `api_url` (str): The LLM API endpoint that was tested
- `total_questions` (int): Number of questions in the dataset
- `passed_questions` (int): Number of questions that passed accuracy check
- `accuracy_percentage` (float): (passed / total) * 100
- `citation_coverage_percentage` (float): Percentage of responses with valid citations
- `performance_metrics` (dict): Contains p50, p95, p99, mean, median latency in ms
- `results` (list[TestResult]): Individual test results for each question
- `config` (dict): Configuration used for this run (thresholds, timeouts, etc.)

**Validation Rules**:
- `total_questions` must equal `len(results)`
- `passed_questions` must be <= `total_questions`
- All percentages must be in range [0.0, 100.0]

**Serialization**:
```python
@dataclass
class BenchmarkReport:
    timestamp: str
    api_url: str
    total_questions: int
    passed_questions: int
    accuracy_percentage: float
    citation_coverage_percentage: float
    performance_metrics: dict  # {p50, p95, p99, mean, median, std_dev}
    results: list[TestResult]
    config: dict
    
    def __post_init__(self):
        if self.total_questions != len(self.results):
            raise ValueError("total_questions must match len(results)")
        if not (0.0 <= self.accuracy_percentage <= 100.0):
            raise ValueError("accuracy_percentage must be in [0, 100]")
    
    def to_json(self, filepath: str):
        import json
        data = {
            "timestamp": self.timestamp,
            "api_url": self.api_url,
            "summary": {
                "total_questions": self.total_questions,
                "passed_questions": self.passed_questions,
                "accuracy_percentage": self.accuracy_percentage,
                "citation_coverage_percentage": self.citation_coverage_percentage
            },
            "performance": self.performance_metrics,
            "results": [r.to_dict() for r in self.results],
            "config": self.config
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
```

**Example**:
```python
report = BenchmarkReport(
    timestamp="2026-01-21T14:30:15Z",
    api_url="http://localhost:8080",
    total_questions=20,
    passed_questions=17,
    accuracy_percentage=85.0,
    citation_coverage_percentage=100.0,
    performance_metrics={
        "p50": 2340.5,
        "p95": 4580.2,
        "p99": 5120.8,
        "mean": 2650.3,
        "median": 2340.5,
        "std_dev": 890.1
    },
    results=[...],  # List of TestResult objects
    config={"fuzzy_threshold": 0.8, "timeout": 5, "retries": 1}
)
```

---

### 5. CitationReference

Structured citation extracted from LLM response.

**Fields**:
- `document` (str): Document name/identifier (e.g., "HR_Policy_2026.md")
- `section` (str): Section within document (e.g., "Time Off", "Section 3.2")
- `relevance_score` (float | None): Optional relevance score from RAG pipeline (P2 feature)

**Validation Rules**:
- `document` and `section` must be non-empty strings
- `relevance_score` if present must be in range [0.0, 1.0]

**Serialization**:
```python
@dataclass
class CitationReference:
    document: str
    section: str
    relevance_score: float | None = None
    
    def __post_init__(self):
        if not self.document or not self.section:
            raise ValueError("document and section are required")
        if self.relevance_score is not None:
            if not (0.0 <= self.relevance_score <= 1.0):
                raise ValueError("relevance_score must be in [0.0, 1.0]")
    
    def to_dict(self) -> dict:
        result = {"document": self.document, "section": self.section}
        if self.relevance_score is not None:
            result["relevance_score"] = self.relevance_score
        return result
```

---

## Relationships

```
GroundTruthDataset
  └─ questions: list[BenchmarkQuestion]

BenchmarkReport
  ├─ results: list[TestResult]
  │   └─ citations_found: list[CitationReference]
  └─ performance_metrics: dict
```

**Lifecycle**:
1. **Load**: `GroundTruthDataset.from_yaml()` reads questions from disk
2. **Execute**: For each `BenchmarkQuestion`, send to API and create `TestResult`
3. **Aggregate**: Collect all `TestResult` objects into `BenchmarkReport`
4. **Export**: `BenchmarkReport.to_json()` saves to `results/` directory

---

## File Formats

### Ground Truth (YAML)

**Location**: `tests/benchmark/ground_truth.yaml`

**Schema** (defined above in GroundTruthDataset)

### Results (JSON)

**Location**: `results/benchmark_YYYY-MM-DD_HH-MM-SS.json`

**Schema** (defined above in BenchmarkReport.to_json)

---

## Validation Summary

| Entity | Key Validations |
|--------|----------------|
| **BenchmarkQuestion** | Non-empty id/question/expected_answer/category; unique IDs |
| **TestResult** | Valid enum statuses; score in [0,1]; non-negative latency |
| **GroundTruthDataset** | Non-empty questions list; unique question IDs; valid version |
| **BenchmarkReport** | total == len(results); percentages in [0,100] |
| **CitationReference** | Non-empty document/section; relevance_score in [0,1] if present |

All entities use Python dataclasses with `__post_init__` validation to fail fast on invalid data.
