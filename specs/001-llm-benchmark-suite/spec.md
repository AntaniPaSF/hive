# Feature Specification: LLM Benchmark Test Suite

**Feature Branch**: `001-llm-benchmark-suite`  
**Created**: 2026-01-21  
**Status**: Draft  
**Input**: User description: "QA engineer creates LLM benchmark test suite (20+ Q&A pairs) for benchmarking local LLMs (Ollama 7B Mistral/Llama) with RAG pipeline. Focus on test framework design and core benchmark principles for simple, slim test suite that can be developed independently before getting API from Backend and RAG engineers."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Core Accuracy Benchmark (Priority: P1)

QA engineers need to validate that the RAG-enabled LLM provides accurate, citation-backed answers to HR policy questions. The benchmark suite must test correctness against a ground-truth dataset of 20+ question-answer pairs covering common employee queries.

**Why this priority**: Directly supports the **Accuracy Over Speed** and **Transparency** constitution principles. Without accurate answers with proper citations, the entire chatbot system fails its core mission. This is the foundation—if accuracy isn't measurable, nothing else matters.

**Independent Test**: Can be fully tested by running the benchmark suite against any LLM API endpoint that returns structured responses (question → answer + citation). Delivers immediate value by establishing whether the RAG pipeline meets the 80%+ accuracy threshold defined in project success metrics.

**Acceptance Scenarios**:

1. **Given** a benchmark dataset of 20+ ground-truth Q&A pairs, **When** the test suite sends each question to the LLM API, **Then** the system validates that at least 80% of answers match expected responses (exact match, semantic similarity, or contains key facts)
2. **Given** an LLM response to a benchmark question, **When** the test suite analyzes the response, **Then** it verifies that a source citation (document name + section) is present in 100% of answers
3. **Given** a test run completion, **When** the suite generates a report, **Then** it shows per-question pass/fail status, overall accuracy percentage, and citation coverage metrics

---

### User Story 2 - Performance Benchmark (Priority: P1)

QA engineers need to measure response time to ensure the system meets the <10 second latency requirement on CPU-only hardware. The benchmark suite must track p50, p95, and p99 response times across all test queries.

**Why this priority**: Supports the **Accuracy Over Speed** principle by providing measurable proof that accuracy doesn't come at the cost of unusable performance. The constitution mandates <10s p95 latency; this story ensures compliance is verifiable.

**Independent Test**: Can be fully tested by instrumenting API calls with timing measurements. Requires only an API endpoint that returns responses—no knowledge of RAG internals needed. Delivers standalone value by identifying performance bottlenecks early.

**Acceptance Scenarios**:

1. **Given** a benchmark run of 20+ questions, **When** the test suite records response times for each query, **Then** it calculates and reports p50, p95, and p99 latency metrics
2. **Given** performance test results, **When** p95 latency exceeds 10 seconds, **Then** the test suite flags this as a failure and identifies which questions caused slowdowns
3. **Given** a test run, **When** results are generated, **Then** the report includes a performance summary showing average response time and distribution histogram

---

### User Story 3 - Reproducible Test Execution (Priority: P1)

QA engineers and developers need to run the benchmark suite locally with a single command, generating consistent, comparable results across different environments. The suite must work without external dependencies beyond the LLM API endpoint.

**Why this priority**: Directly supports the **Reproducible** constitution principle. If the test suite itself isn't reproducible, it can't validate the system's reproducibility. Enables distributed teams to run benchmarks independently without environment debugging.

**Independent Test**: Can be fully tested by providing the suite to a new developer who runs it on their local machine. Success = results generated within 5 minutes with zero manual configuration (beyond specifying API endpoint URL).

**Acceptance Scenarios**:

1. **Given** a fresh checkout of the test suite code, **When** a developer runs a single setup command (e.g., `pip install -r requirements.txt`), **Then** all dependencies are installed without errors
2. **Given** the test suite is installed, **When** a developer runs the benchmark command with an API endpoint URL, **Then** the suite executes all 20+ tests and generates a results report without manual intervention
3. **Given** two developers run the suite against the same LLM API, **When** they compare results, **Then** accuracy and citation metrics are identical (performance metrics may vary slightly due to hardware differences)

---

### User Story 3.1 - CI/CD Pipeline Integration (Priority: P1) **[NEW - Session 2026-01-22]**

The benchmark suite must integrate seamlessly into the CI/CD pipeline to automatically validate LLM responses on every pull request. Tests run against a mock LLM implementation for fast feedback during development, with the option to run against real LLM endpoints for comprehensive benchmarking.

**Why this priority**: Directly enforces constitution principles by ensuring every code change is validated for accuracy and citation coverage before merging. Prevents regressions from reaching production.

**Independent Test**: Can be tested by creating a PR with intentional accuracy/citation failures and verifying CI blocks the merge. Fix the issues and verify CI passes.

**Acceptance Scenarios**:

1. **Given** a PR is created, **When** CI/CD pipeline runs, **Then** the benchmark test suite executes automatically with 13 test cases validating accuracy, citations, consistency, and performance
2. **Given** all tests pass, **When** CI completes, **Then** green checkmark appears and merge is allowed
3. **Given** any test fails, **When** CI completes, **Then** red X appears, PR comments show failure details, and merge is blocked
4. **Given** benchmark tests run in CI context, **When** mock LLM is used, **Then** tests complete in under 1 second with reproducible results

---

### User Story 4 - Citation Quality Validation (Priority: P2)

QA engineers need to verify that citations are not just present, but actually point to valid source documents and sections. The benchmark suite should validate that cited sources exist in the knowledge base and are relevant to the question asked.

**Why this priority**: Enhances the **Transparency** principle by ensuring citations aren't hallucinated. While P1 checks for citation presence, this validates citation correctness—important but can be implemented after basic accuracy checks work.

**Independent Test**: Can be tested by providing the suite with a knowledge base manifest (list of valid documents/sections) and checking if citations reference real sources. Delivers value by catching hallucinated citations that undermine user trust.

**Acceptance Scenarios**:

1. **Given** a knowledge base manifest listing all valid documents and sections, **When** the test suite receives an LLM response with citations, **Then** it verifies that cited document names exist in the manifest
2. **Given** a response with a citation to a specific section, **When** the suite validates the citation, **Then** it checks that the section reference matches a valid section in the cited document
3. **Given** a test run with citation validation enabled, **When** any response contains invalid citations, **Then** the suite flags this as a "hallucinated citation" error in the report

---

### User Story 5 - Ground Truth Management (Priority: P2)

QA engineers need to easily add, update, and version-control the benchmark question-answer pairs. The ground truth dataset should be stored in a human-readable format (JSON, YAML, or CSV) with support for expected answers, acceptable answer variations, and metadata.

**Why this priority**: Supports long-term maintainability and reproducibility. Ground truth must evolve as HR policies change, but this can start with a minimal 20-question dataset and expand later.

**Independent Test**: Can be tested by manually editing the ground truth file, adding a new question-answer pair, and re-running the benchmark to verify the new question is included. Delivers value by enabling non-technical stakeholders to update test cases.

**Acceptance Scenarios**:

1. **Given** a ground truth file in YAML format, **When** a QA engineer adds a new question-answer entry, **Then** the next benchmark run automatically includes the new test case
2. **Given** a question in the ground truth dataset, **When** the entry includes multiple acceptable answer variations, **Then** the test suite passes if the LLM response matches any variation
3. **Given** a ground truth file, **When** it's stored in version control (Git), **Then** changes to the dataset are tracked with commit history showing who modified which questions and when

---

### User Story 6 - Regression Detection (Priority: P3)

QA engineers need to detect when LLM accuracy degrades over time. The benchmark suite should save historical test results and highlight regressions (previously passing questions that now fail).

**Why this priority**: Nice-to-have for continuous quality monitoring. Valuable for catching model drift or configuration changes, but P1/P2 stories provide the core testing capability.

**Independent Test**: Can be tested by running the suite twice, manually changing a ground truth answer to fail the second run, and verifying the suite reports a regression. Delivers value by enabling proactive quality maintenance.

**Acceptance Scenarios**:

1. **Given** a baseline test run with results saved, **When** a new test run is executed, **Then** the suite compares current results to the baseline and identifies questions that previously passed but now fail
2. **Given** a regression detected, **When** the report is generated, **Then** it highlights regressed questions with diff showing expected vs actual answers
3. **Given** historical results, **When** accuracy trends are analyzed, **Then** the suite provides a summary showing accuracy percentage over the last N runs (e.g., last 10 runs)

---

### Edge Cases

- **What happens when the LLM API is unreachable or times out?**  
  Test suite should retry once (with 5-second timeout), then mark the question as "API_ERROR" in results without failing the entire suite. Final report includes API error count.

- **What happens when the LLM returns a response without a citation?**  
  Counted as both an accuracy failure (violates Transparency principle) and a citation coverage failure. Clearly flagged in the report.

- **What happens when the ground truth dataset is empty or malformed?**  
  Suite validates the dataset on startup and fails fast with a descriptive error message (e.g., "Ground truth file invalid: expected list of objects with 'question' and 'expected_answer' fields").

- **What happens when two acceptable answer variations conflict?**  
  Suite treats them as alternatives (OR logic)—LLM response passes if it matches *any* variation. QA engineer resolves conflicts by updating ground truth.

- **What happens when running benchmarks in parallel vs sequential?**  
  Performance metrics should specify execution mode. Default = sequential (for consistent timing). Parallel mode optional for faster iteration but may skew latency measurements.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Test suite MUST load a ground truth dataset from a YAML file containing at least 20 question-answer pairs with support for comments and metadata
- **FR-002**: Test suite MUST send each question to a configurable LLM API endpoint via HTTP request
- **FR-003**: Test suite MUST validate that LLM responses include source citations (document name + section reference)
- **FR-004**: Test suite MUST calculate accuracy by comparing LLM answers to expected answers using threshold-based fuzzy matching (Levenshtein distance ratio ≥ 0.8 or keyword overlap ≥ 70% as configurable thresholds)
- **FR-005**: Test suite MUST measure response time (latency) for each question and calculate p50, p95, and p99 percentiles
- **FR-006**: Test suite MUST generate a structured results report in two formats: human-readable text summary printed to CLI and a JSON file saved to `results/` directory with timestamped filename (e.g., `results/benchmark_2026-01-21_14-30-15.json`), both showing per-question pass/fail, overall accuracy percentage, citation coverage, and performance metrics
- **FR-007**: Test suite MUST fail fast with descriptive errors if the ground truth dataset is missing, empty, or malformed
- **FR-008**: Test suite MUST accept the LLM API endpoint URL as a configuration parameter (environment variable or CLI argument)
- **FR-009**: Test suite MUST run on CPU-only hardware without requiring GPU acceleration
- **FR-010**: Test suite MUST support adding new benchmark questions by editing the ground truth file without code changes
- **FR-011**: Test suite MUST retry failed API requests once with a 5-second timeout per request before marking as error (to handle transient network issues)
- **FR-012**: Test suite MUST allow multiple acceptable answer variations per question (e.g., "5 business days" and "one work week" both valid)
- **FR-013**: Test suite MUST be executable via a single command (e.g., `python benchmark.py --api-url http://localhost:8000`) after initial setup

### Key Entities

- **BenchmarkQuestion**: Represents a single test case with fields: question text, expected answer(s), acceptable answer variations, question category (e.g., "vacation policy", "expense reports"), priority/weight (optional)
- **TestResult**: Captures the outcome of testing one question with fields: question ID, LLM response text, citations found, accuracy status (pass/fail), response time (ms), error message (if API failure)
- **GroundTruthDataset**: Collection of BenchmarkQuestions loaded from file, includes metadata: dataset version, creation date, total question count
- **BenchmarkReport**: Aggregated results with fields: overall accuracy percentage, citation coverage percentage, performance metrics (p50/p95/p99 latency), per-question results list, timestamp
- **CitationReference**: Structured citation extracted from LLM response with fields: document name, section identifier, relevance score (optional for P2 story)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: QA engineers can run the benchmark suite and get results in under 5 minutes for 20 questions (excluding LLM inference time)
- **SC-002**: The test suite correctly identifies when LLM accuracy drops below 80% threshold (validated by intentionally providing incorrect answers)
- **SC-003**: 100% of test runs generate a structured report showing accuracy, citation coverage, and performance metrics in both human-readable (text summary) and machine-readable (JSON) formats
- **SC-004**: New team members can execute the benchmark suite on their local machine within 10 minutes of cloning the repository (including dependency installation)
- **SC-005**: The ground truth dataset can be updated by non-developers (e.g., product managers) by editing a YAML file without touching code
- **SC-006**: The test suite detects missing citations with 100% precision (no false positives where citations are present but not detected)
- **SC-007**: Performance benchmarks are reproducible with <5% variance in p95 latency when run on the same hardware and API endpoint

## Assumptions

- **LLM API Contract**: The Backend Engineer will provide an API that accepts POST requests with a JSON body containing `{"question": "string"}` and returns `{"answer": "string", "citations": [{"document": "string", "section": "string"}]}` or similar structure
- **RAG Pipeline Output**: The RAG Engineer's pipeline will include citation data in the response—the test suite doesn't need to independently verify RAG retrieval correctness, only that citations are present and valid
- **Ground Truth Quality**: The 20+ initial question-answer pairs are provided by domain experts (HR team or product manager) and are considered authoritative
- **Semantic Similarity**: For P1 MVP, accuracy validation uses simple keyword matching or contains-key-facts logic. Advanced semantic similarity (e.g., using embeddings) can be added in P2/P3
- **API Availability**: The LLM API endpoint is assumed to be running locally (e.g., `http://localhost:8000`) or on an accessible network during test execution
- **Single Model Benchmarking**: MVP focuses on benchmarking one model at a time. Comparative benchmarking (Mistral vs Llama) is post-MVP scope
- **No Authentication**: The LLM API endpoint does not require authentication tokens for MVP (can be added later if Backend implements auth)

## Out of Scope

- **RAG Pipeline Testing**: The suite tests the end-to-end LLM+RAG output, not the RAG retrieval mechanism itself (that's the RAG Engineer's responsibility)
- **Knowledge Base Validation**: The suite doesn't verify that the knowledge base contains correct information, only that the LLM references it via citations
- **Multi-Model Comparison**: Running benchmarks across multiple models (Mistral, Llama, etc.) simultaneously is post-MVP
- **Adversarial Testing**: Intentionally malicious or prompt-injection attacks are out of scope for this simple benchmark suite
- **UI/Dashboard**: Results are presented via CLI output and files (JSON/text). A web-based dashboard for visualizing trends is post-MVP
- **Automated Retraining**: The suite detects accuracy regressions but doesn't trigger model retraining or alerts—that's a CI/CD integration concern for later

## Clarifications

### Session 2026-01-21

- Q: How should accuracy validation work (FR-004) - exact matching, fuzzy matching, key fact extraction, or hybrid? → A: Threshold-based fuzzy matching (e.g., Levenshtein distance ratio ≥ 0.8 or keyword overlap ≥ 70%)
- Q: What file format should the ground truth dataset use (FR-001)? → A: YAML format (more human-readable, supports comments)
- Q: What output format should the benchmark report use (FR-006)? → A: Both human-readable text summary (for CLI output) and JSON file (for automation/CI)
- Q: Where should benchmark results be stored? → A: Store in `results/` directory with timestamped filenames (e.g., `results/benchmark_2026-01-21_14-30-15.json`)
- Q: What timeout should be used for API requests (FR-011)? → A: 5 seconds per request

### Session 2026-01-22 - CI/CD Integration Implementation

**Status**: Implemented as part of 066-cicd-pipeline branch

**Changes Made**:
1. Created `tests/test_llm_benchmark.py` with 13 pytest test cases (282 lines)
2. Integrated LLM benchmark tests into `.github/workflows/pr-validation.yml`
3. Tests run automatically on every PR with full coverage reporting
4. Mock LLM implementation for fast CI/CD execution (<1 second)

**Test Suite Breakdown**:
- **TestLLMBenchmarkAccuracy** (3 tests): Validates answers against 3 benchmark questions (Q001-Q003)
- **TestLLMBenchmarkCitations** (3 tests): Ensures citations are present and non-empty
- **TestLLMBenchmarkConsistency** (2 tests): Validates answer consistency and required fields
- **TestLLMBenchmarkPerformance** (2 tests): Measures response time (<1.0s) and batch processing
- **TestBenchmarkSuiteIntegration** (3 tests): End-to-end validation and coverage checks

**CI/CD Workflow**:
```
PR Created → tests job:
  ├── Run pytest tests/ (includes 17 total tests: 4 basic + 13 LLM benchmark)
  ├── Generate coverage reports (pytest-cov)
  ├── Upload to Codecov
  └── Fail if any test fails → Block merge
  
  → build job (only if tests pass):
  ├── Build Docker image
  └── Verify build succeeds
```

**Implementation Notes**:
- MVP uses mock LLM for fast CI/CD (0.03s execution time)
- Full benchmarking with real LLM API available via `tests/benchmark/benchmark.py`
- Ground truth exists at `tests/benchmark/ground_truth.yaml` (20+ questions)
- Tests auto-scale: add questions to YAML, expand MockLLMImplementation responses
- Can switch to real API by updating MockLLMImplementation or environment config

**Next Steps (Post-MVP)**:
- Expand test coverage from 3 to 20+ questions
- Add citation validation against knowledge base manifest (User Story 4)
- Implement regression detection with baseline storage (User Story 6)
- Add support for different LLM models/endpoints for comparative benchmarking
