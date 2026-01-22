# Phase 1: CI/CD Data Models

> Document created: 2025 | Status: APPROVED | Part of: 066-cicd-pipeline

This document defines the core entities and data structures that flow through the CI/CD pipeline, ensuring consistent contract semantics across GitHub Actions workflows.

---

## 1. Core Entity Definitions

### Pipeline

**Definition**: A complete CI/CD execution for a commit or tag.

```yaml
Pipeline:
  id: str                          # SHA-256 hash of commit
  trigger_type: enum               # PR, push (main), tag, manual
  commit_sha: str(40)              # Git commit hash
  branch: str                       # Branch name (main, develop, feature/*)
  author: str                       # Git author email
  timestamp: ISO8601               # When workflow started
  status: enum                      # queued, in_progress, success, failure, cancelled
  
  # Nested entities
  build: Build                      # Container image build results
  tests: TestRun                    # Unit and integration test results
  benchmarks: BenchmarkRun          # Performance/accuracy benchmark results
  quality: QualityCheck             # Code quality gate results
  artifacts: List[Artifact]         # Generated files (images, reports, logs)
```

**Validation Rules**:
- `commit_sha` must be exactly 40 hex characters
- `branch` must match `^[a-zA-Z0-9/_-]+$`
- `trigger_type` in PR mode cannot merge to main
- Must have at least one test result before benchmark execution
- Status transitions: queued → in_progress → {success, failure, cancelled}

**State Transitions**:
```
Initial: queued
  ↓ (workflow starts)
in_progress
  ↓ (jobs complete)
success (all required jobs ✓)
  ↓ (manual approval in main)
released (tag pushed)

Alternative: failure (any required job ✗)
Alternative: cancelled (user abort or timeout)
```

---

### Build

**Definition**: Container image build metadata and registry push status.

```yaml
Build:
  image_name: str                   # ghcr.io/org/hive-core:tag
  base_image: str                   # python:3.11-slim
  
  # Tagging strategy
  tags:
    - commit_sha: str               # main-abc1234567890
    - semantic_version: str         # v1.0.0 (only on tag triggers)
    - latest: bool                  # true only on main branch
  
  # Build metadata
  size_bytes: int                   # Final image size (target <200MB)
  layers: int                       # Docker layer count
  build_time_seconds: float         # How long build took
  
  # Registry interaction
  registry: str                     # ghcr.io
  push_status: enum                 # pending, pushed, failed, skipped
  digest: str(71)                   # sha256:abc123...
  scan_status: enum                 # not_scanned, clean, vulnerabilities, failed
  
  # Cache statistics
  cache_hit_rate: float             # 0.0-1.0 (target >0.8)
  layer_cache_hits: int
  layer_cache_misses: int
```

**Validation Rules**:
- `image_name` must start with `ghcr.io/`
- `size_bytes` must be < 300MB (warning > 250MB)
- `build_time_seconds` must be < 180 (soft limit, logs warning if exceeded)
- Exactly one semantic_version tag per tag trigger
- On main branch: latest tag = true
- On other branches: latest tag = false

**Success Criteria**:
- Image builds without layer errors
- Size < 200MB (target), < 300MB (hard fail)
- Build time < 120s with caching, < 180s without
- Digest must be consistent (same code = same digest)
- Trivy scan passes (no critical/high CVEs in dependencies)

---

### TestRun

**Definition**: Comprehensive test execution capturing coverage, timing, and failure details.

```yaml
TestRun:
  id: str                           # UUID
  framework: str                    # pytest (only one supported)
  
  # Execution metadata
  total_tests: int                  # Sum of all test results
  passed: int
  failed: int
  skipped: int
  error: int                        # Syntax errors, import errors
  duration_seconds: float           # Total wall-clock time
  
  # Coverage tracking
  coverage:
    lines: float                    # 0-100% target >= 80%
    branches: float
    functions: float
  
  # Failure details (if any)
  failures: List[TestFailure]
  
  # Performance tracking
  slowest_tests:                    # Top 5 slow tests
    - name: str
      duration_seconds: float
    
  # Artifacts
  coverage_report: str              # Path to HTML report (if generated)
  junit_xml: str                    # JUnit XML report for GitHub
```

**TestFailure Structure**:
```yaml
TestFailure:
  test_name: str                    # tests/core/test_parser.py::test_parse_valid
  error_type: str                   # AssertionError, TypeError, etc.
  error_message: str                # Full error message
  traceback: str                    # Stack trace for debugging
  flakiness_score: float            # 0.0-1.0 (has this failed before?)
```

**Validation Rules**:
- `passed + failed + skipped + error = total_tests`
- Coverage metrics must be 0-100
- `duration_seconds` > 0
- Each failure must have non-empty test_name, error_type, error_message
- `flakiness_score` = (fail_count_last_10_runs / 10)

**Success Criteria**:
- `failed + error = 0` (all tests pass)
- `coverage.lines >= 80%` (hard requirement for PR merge)
- `duration_seconds < 90` (target)
- Slowest test < 5 seconds (suggests test isolation issues)

---

### BenchmarkRun

**Definition**: Performance and accuracy benchmark execution for LLM operations.

```yaml
BenchmarkRun:
  id: str                           # UUID
  suite_name: str                   # "full" or "smoke"
  
  # Execution environment
  api_host: str                     # localhost:8000 during CI
  startup_time_seconds: float       # Time to reach /health ok
  
  # Test statistics
  total_tests: int
  passed: int                       # Accuracy >= 80%
  failed: int                       # Accuracy < 80%
  
  # Accuracy metrics
  accuracy: float                   # 0-100%, target >= 80%
  citations_accuracy: float         # % questions with 100% citations, target 100%
  
  # Performance metrics (p50, p95, p99)
  latency:
    p50_ms: float                   # Median response time
    p95_ms: float                   # 95th percentile, target < 1000ms
    p99_ms: float                   # 99th percentile
    max_ms: float
  
  # Regression detection
  baseline_accuracy: float          # Previous main branch accuracy
  regression_detected: bool         # accuracy < baseline * 0.95
  regression_details: str
  
  # Question-level details (sample)
  questions: List[Question]         # Sample of 5-10 for debugging
  
  # Artifacts
  full_report: str                  # Path to detailed JSON report
```

**Question Structure**:
```yaml
Question:
  id: str                           # Unique ID from benchmark suite
  text: str                         # Question asked to system
  
  expected_answer: str              # Ground truth
  system_answer: str                # What system returned
  match: bool                       # Exact string match
  
  accuracy: float                   # 0.0-1.0 (semantic similarity)
  citations:
    expected: int                   # Expected citation count
    found: int                      # Actually cited sources
    accuracy: float                 # found/expected
```

**Validation Rules**:
- `total_tests = passed + failed`
- `accuracy` ranges 0-100%
- `citations_accuracy` must be 0-100%
- `latency.p99_ms >= latency.p95_ms >= latency.p50_ms`
- If regression detected, must have non-empty regression_details
- Questions list should be 5-10 items for debugging

**Success Criteria**:
- `accuracy >= 80%` (hard requirement for PR merge)
- `citations_accuracy >= 100%` (hard requirement, 0 tolerance)
- `latency.p95_ms < 1000` (soft, logs warning if exceeded)
- `regression_detected = false` (blocks merge if true)
- All questions must have citations if they reference sources

**Gate Enforcement**:
```yaml
PR_Merge_Blocked_If:
  - accuracy < 80%
  - citations_accuracy < 100%
  - regression_detected = true
  
Information_Only_If:
  - latency.p95_ms >= 1000  (warning in PR comment)
  - any_question has citations_accuracy < 100%  (list in report)
```

---

### QualityCheck

**Definition**: Static analysis and code quality gate results.

```yaml
QualityCheck:
  timestamp: ISO8601
  
  # Format check
  formatting:
    tool: str                       # "black"
    compliant: bool                 # true = no changes needed
    files_needing_format: List[str] # if compliant=false
    
  # Linting
  linting:
    tool: str                       # "ruff"
    violations: int                 # Total violations found
    by_severity:
      error: int
      warning: int
      info: int
    violations_detail: List[LintViolation]
    
  # Type checking
  type_checking:
    tool: str                       # "mypy"
    errors: int
    files_with_errors: List[str]
    type_errors_detail: List[TypeError]
    
  # Security scanning
  security:
    bandit_issues: int              # Severity: CRITICAL, HIGH, MEDIUM, LOW
    by_severity:
      critical: int
      high: int
      medium: int
      low: int
    issues_detail: List[SecurityIssue]
    
  # Dependency scanning
  dependencies:
    tool: str                       # "pip-audit"
    vulnerabilities: int
    critical_vuln: int              # CVEs with CVSS >= 9.0
    detail: List[Vulnerability]
```

**LintViolation Structure**:
```yaml
LintViolation:
  file: str                         # Path relative to repo root
  line: int
  column: int
  rule_id: str                      # E501, W291, etc.
  message: str
  severity: str                     # error, warning, info
```

**SecurityIssue & Vulnerability** (similar structure):
```yaml
SecurityIssue:
  file: str
  line: int
  issue_type: str                   # e.g., "hardcoded-sql-string"
  severity: str                     # CRITICAL, HIGH, MEDIUM, LOW
  description: str
  remediation: str
  
Vulnerability:
  package: str                      # e.g., "requests"
  version: str
  vulnerability_id: str             # e.g., "PYSEC-2023-1234"
  severity: str                     # CRITICAL, HIGH, MEDIUM, LOW
  fix_version: str
```

**Validation Rules**:
- All violation/issue/vulnerability lists must be non-empty if respective counts > 0
- Severity enums must be exact (no variations)
- File paths must be relative to repo root

**Success Criteria**:
- `formatting.compliant = true` (hard requirement)
- `linting.violations = 0` (hard requirement)
- `type_checking.errors = 0` (hard requirement)
- `security.critical = 0` (hard requirement for bandit)
- `security.high <= 5` (warning if exceeded, review required)
- `dependencies.critical_vuln = 0` (hard requirement)

---

### Artifact

**Definition**: Generated outputs (images, reports, logs) with retention metadata.

```yaml
Artifact:
  id: str                           # UUID
  name: str                         # "coverage-report", "benchmark-results"
  type: enum                        # image, report, log, file
  mime_type: str                    # image/x-docker, application/json, text/plain
  
  # Storage location
  path: str                         # In workflow artifact storage
  size_bytes: int
  
  # Availability
  retention_days: int               # How long GitHub keeps it
  available_until: ISO8601
  downloadable: bool
  
  # For images specifically
  digest: str(71)                   # sha256:abc123...
  repository: str                   # ghcr.io/org/hive-core
```

**Validation Rules**:
- `mime_type` must be valid IANA type
- `retention_days` > 0 (GitHub minimum 1)
- `available_until >= now + retention_days`

---

## 2. Data Flow Diagram

```
Commit Push to GitHub
    ↓
[Trigger Event] (GitHub Webhooks)
    ↓
Pipeline Created (id = commit SHA)
    ├─→ [Setup Job]
    │   ├─→ Checkout code
    │   └─→ Setup Python + Docker
    │
    ├─→ [Test Job] (parallel with Lint/Build)
    │   └─→ TestRun entity created
    │       └─→ Fails? → Pipeline.status = failure
    │
    ├─→ [Lint Job] (parallel with Test/Build)
    │   └─→ QualityCheck entity created
    │       └─→ Violations? → Pipeline.status = failure
    │
    ├─→ [Build Job] (after Lint + Test pass)
    │   └─→ Build entity created
    │       ├─→ Push to ghcr.io
    │       └─→ Trivy scan
    │           └─→ Vulnerabilities? → Pipeline.status = failure
    │
    └─→ [Benchmark Job] (after Build succeeds)
        └─→ BenchmarkRun entity created
            ├─→ Accuracy < 80%? → Pipeline.status = failure
            ├─→ Citations < 100%? → Pipeline.status = failure
            └─→ Regression detected? → Pipeline.status = failure
                
If all succeed → Pipeline.status = success
If any fail → PR gets comment with failures
If manual tag → Release workflow triggered
```

---

## 3. Validation Gates

### Merge Gate (PR to Main)

**Required for Merge**:
```
TestRun.failed = 0
TestRun.coverage.lines >= 80%
BenchmarkRun.accuracy >= 80%
BenchmarkRun.citations_accuracy = 100%
BenchmarkRun.regression_detected = false
QualityCheck.formatting.compliant = true
QualityCheck.linting.violations = 0
QualityCheck.type_checking.errors = 0
QualityCheck.security.critical = 0
QualityCheck.dependencies.critical_vuln = 0
Build.scan_status != "vulnerabilities"
```

**Blocks Merge If Any Fails**.

### Release Gate (Tag to Release)

**Required for Release**:
```
Identical to Merge Gate, plus:
Build.digest is deterministic (same commit = same digest)
Build.tags includes semantic version (vX.Y.Z)
Build.push_status = "pushed"
```

### Information Gates (Warning, Not Blocking)

```
If TestRun.duration_seconds > 90 → Comment: "Tests slow, consider parallelization"
If Build.size_bytes > 250MB → Comment: "Image large, optimization recommended"
If BenchmarkRun.latency.p95_ms > 1000 → Comment: "P95 latency elevated"
If QualityCheck.security.high > 0 → Comment: "Review high-severity findings"
```

---

## 4. Example Pipeline Execution

**Scenario**: Developer pushes PR with improved accuracy from 78% to 85%

```yaml
# Pipeline Created
Pipeline:
  id: "abc123def456"
  trigger_type: "PR"
  commit_sha: "abc123def456789..."
  branch: "feature/improve-accuracy"
  author: "dev@corp.com"
  timestamp: "2025-01-15T10:30:00Z"
  status: "queued"

# After TestRun completes
Pipeline.tests:
  - total_tests: 145
    passed: 145
    failed: 0
    coverage.lines: 82.5%
    duration_seconds: 68.5

# After QualityCheck completes
Pipeline.quality:
  - formatting.compliant: true
  - linting.violations: 0
  - type_checking.errors: 0
  - security.critical: 0
  - dependencies.critical_vuln: 0

# After Build completes
Pipeline.build:
  - image_name: "ghcr.io/corp/hive-core:feature-abc123d"
  - size_bytes: 215000000  # 215 MB
  - build_time_seconds: 95.2
  - cache_hit_rate: 0.85
  - push_status: "pushed"
  - scan_status: "clean"

# After BenchmarkRun completes
Pipeline.benchmarks:
  - accuracy: 85.2%
  - citations_accuracy: 100%
  - baseline_accuracy: 78.0%
  - regression_detected: false
  - latency.p95_ms: 487.3
  - duration_seconds: 142.8

# Final status
Pipeline.status: "success"

# PR gets automatic comment:
✅ All checks passed!
- Tests: 145/145 (82.5% coverage)
- Quality: All gates passed
- Image: 215MB, pushed to ghcr.io
- Accuracy: 85.2% (↑ 7.2% from baseline 78%)
- Citations: 100% ✅
- P95 Latency: 487ms ✅
Ready to merge!
```

---

## 5. Related Contracts

- See [contracts/workflow-pr-validation.yaml](contracts/workflow-pr-validation.yaml) for input/output specs
- See [contracts/workflow-main-build.yaml](contracts/workflow-main-build.yaml) for main branch workflow
- See [contracts/benchmark-schema.yaml](contracts/benchmark-schema.yaml) for benchmark detail schema
