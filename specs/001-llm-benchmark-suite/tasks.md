# Tasks: LLM Benchmark Test Suite

**Input**: Design documents from `/specs/001-llm-benchmark-suite/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: NOT included - Feature specification does not request TDD approach

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

**Constitution Alignment**: Reproducible principle - ensure single-command setup

- [X] T001 Create benchmark directory structure tests/benchmark/ with subdirectories validators/, reporters/, models/
- [X] T002 Update requirements.txt with benchmark dependencies: PyYAML, python-Levenshtein, requests, numpy, python-dotenv
- [X] T003 [P] Create tests/benchmark/__init__.py as empty module marker
- [X] T004 [P] Create tests/benchmark/config.py with environment variable loading (BENCHMARK_API_URL, BENCHMARK_TIMEOUT, BENCHMARK_THRESHOLD)
- [X] T005 [P] Create scripts/benchmark.sh wrapper script for single-command execution

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**Constitution Alignment**: Self-Contained + Reproducible principles

- [X] T006 [P] Create tests/benchmark/validators/__init__.py with empty __all__ list
- [X] T007 [P] Create tests/benchmark/reporters/__init__.py with empty __all__ list
- [X] T008 [P] Create tests/benchmark/models/__init__.py with empty __all__ list
- [X] T009 [P] Create AccuracyStatus and CitationStatus enums in tests/benchmark/models/enums.py
- [X] T010 Create ground_truth.yaml template with metadata (version, created, description) and sample question structure in tests/benchmark/ground_truth.yaml
- [X] T011 [P] Create results/ directory at repository root and add .gitkeep file
- [X] T012 [P] Update .gitignore to exclude results/*.json but keep results/.gitkeep

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Core Accuracy Benchmark (Priority: P1) 🎯 MVP

**Goal**: Validate that the RAG-enabled LLM provides accurate, citation-backed answers using 20+ ground-truth Q&A pairs with fuzzy matching

**Independent Test**: Run benchmark.py against localhost:8080 API and verify report shows accuracy percentage, citation coverage, and per-question pass/fail status

**Constitution Impact**: 
- **Accuracy Over Speed**: Validates correctness via fuzzy matching (Levenshtein ≥0.8 OR keyword overlap ≥70%)
- **Transparency**: Ensures 100% citation coverage reporting
- **Reproducible**: Single-command execution after setup

### Implementation for User Story 1

- [X] T013 [P] [US1] Create BenchmarkQuestion dataclass in tests/benchmark/models/question.py with fields: id, category, question, expected_answer, variations, citation_required, tags
- [X] T014 [P] [US1] Create TestResult dataclass in tests/benchmark/models/result.py with fields: question_id, question_text, llm_response, citations_found, accuracy_status, accuracy_score, citation_status, latency_ms, error_message, timestamp
- [X] T015 [P] [US1] Create GroundTruthDataset dataclass in tests/benchmark/models/dataset.py with from_yaml() classmethod to load and validate ground_truth.yaml
- [X] T016 [P] [US1] Implement fuzzy_match() function in tests/benchmark/validators/fuzzy_match.py using python-Levenshtein ratio and keyword overlap logic per research.md
- [X] T017 [P] [US1] Implement validate_citations() function in tests/benchmark/validators/citation_check.py to verify citations array structure and presence
- [X] T018 [US1] Create BenchmarkReport dataclass in tests/benchmark/models/report.py with summary statistics (accuracy_pct, citation_coverage_pct, performance metrics)
- [X] T019 [US1] Implement CLIReporter class in tests/benchmark/reporters/cli_reporter.py with generate_report() method for human-readable text output
- [X] T020 [US1] Implement JSONReporter class in tests/benchmark/reporters/json_reporter.py with save_report() method for timestamped JSON export
- [X] T021 [US1] Create main benchmark runner in tests/benchmark/benchmark.py with CLI argument parsing (--api-url, --timeout, --threshold, --ground-truth)
- [X] T022 [US1] Add HTTP request logic to benchmark.py using requests library with 5-second timeout and single retry on connection errors
- [X] T023 [US1] Add accuracy validation in benchmark.py by comparing llm_response to expected_answer using fuzzy_match()
- [X] T024 [US1] Add citation validation in benchmark.py by checking citations array using validate_citations()
- [X] T025 [US1] Add latency measurement in benchmark.py by recording time from request start to response receipt
- [X] T026 [US1] Integrate CLIReporter to print human-readable summary after benchmark run completes
- [X] T027 [US1] Integrate JSONReporter to save timestamped results file to results/ directory
- [X] T028 [US1] Add error handling for API failures (timeout, connection errors, 4xx/5xx responses) with ERROR status in TestResult
- [X] T029 [US1] Populate ground_truth.yaml with 20+ real HR policy Q&A pairs covering vacation, expenses, time-off, remote work policies

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - benchmark suite can validate accuracy, citation coverage, and basic performance

---

## Phase 4: User Story 2 - Performance Benchmark (Priority: P1)

**Goal**: Measure response time to ensure system meets <10 second p95 latency requirement with p50/p95/p99 tracking

**Independent Test**: Run benchmark.py and verify report includes p50, p95, p99 latency metrics with flagged failures if p95 >10 seconds

**Constitution Impact**:
- **Accuracy Over Speed**: Proves accuracy doesn't come at cost of unusable performance (<10s p95)
- **Reproducible**: Performance metrics are deterministic for same hardware/API setup

### Implementation for User Story 2

- [X] T030 [P] [US2] Implement calculate_percentiles() function in tests/benchmark/reporters/performance.py using numpy.percentile() per research.md
- [X] T031 [US2] Update BenchmarkReport dataclass in tests/benchmark/models/report.py to include p50/p95/p99 fields in performance metrics dict
- [X] T032 [US2] Update benchmark.py main runner to collect all latency_ms values from TestResults
- [X] T033 [US2] Update benchmark.py to call calculate_percentiles() on collected latencies after all questions complete
- [X] T034 [US2] Update CLIReporter.generate_report() to display performance section with p50/p95/p99 metrics
- [X] T035 [US2] Update JSONReporter.save_report() to include performance metrics in JSON output
- [X] T036 [US2] Add p95 latency validation in benchmark.py to flag as warning if p95 >10 seconds (constitution requirement)
- [X] T037 [US2] Update CLI report to identify and list specific questions that exceeded 10s response time

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - benchmark suite provides accuracy + performance validation

---

## Phase 5: User Story 3 - Reproducible Test Execution (Priority: P1)

**Goal**: Enable single-command execution with consistent, comparable results across different environments

**Independent Test**: Fresh developer runs `pip install -r requirements.txt && python tests/benchmark/benchmark.py --api-url <URL>` and gets results within 5 minutes without manual configuration

**Constitution Impact**:
- **Reproducible**: Single-command execution with <10 minute setup time
- **Self-Contained**: No external dependencies beyond local API endpoint

### Implementation for User Story 3

- [X] T038 [P] [US3] Create .env.example template file at repository root with BENCHMARK_API_URL, BENCHMARK_TIMEOUT, BENCHMARK_THRESHOLD defaults
- [X] T039 [P] [US3] Update tests/benchmark/config.py to load configuration from .env file using python-dotenv
- [X] T040 [US3] Update benchmark.py CLI argument parsing to use environment variables as defaults (fallback to .env values)
- [X] T041 [US3] Add validation in benchmark.py to fail fast if API endpoint URL is not provided (no default for URL)
- [X] T042 [US3] Implement scripts/benchmark.sh wrapper with usage instructions and automatic virtual environment setup
- [X] T043 [US3] Update scripts/benchmark.sh to export APP_PORT=8080 before running benchmark if not already set
- [X] T044 [US3] Add --version flag to benchmark.py to display benchmark suite version from ground_truth.yaml metadata
- [X] T045 [US3] Update quickstart.md with verified single-command setup instructions and expected output examples

**Checkpoint**: All P1 user stories should now be independently functional - MVP is complete and ready for deployment

---

## Phase 6: User Story 4 - Citation Quality Validation (Priority: P2)

**Goal**: Verify that citations point to valid source documents and sections (not just present, but correct)

**Independent Test**: Create knowledge_base_manifest.yaml with valid documents/sections, run benchmark, and verify invalid citations are flagged as "hallucinated citation" errors

**Constitution Impact**:
- **Transparency**: Enhanced citation validation ensures citations aren't hallucinated
- **Accuracy**: Catches false citations that undermine user trust

### Implementation for User Story 4

- [ ] T046 [P] [US4] Create CitationReference dataclass in tests/benchmark/models/citation.py with fields: document, section, relevance_score
- [ ] T047 [P] [US4] Create KnowledgeBaseManifest dataclass in tests/benchmark/models/manifest.py with from_yaml() classmethod
- [ ] T048 [US4] Create knowledge_base_manifest.yaml template in tests/benchmark/ with valid_documents list and sections per document
- [ ] T049 [US4] Implement validate_citation_quality() function in tests/benchmark/validators/citation_check.py to check citations against manifest
- [ ] T050 [US4] Update tests/benchmark/config.py to add BENCHMARK_MANIFEST_PATH configuration parameter
- [ ] T051 [US4] Update benchmark.py to optionally load KnowledgeBaseManifest if manifest path is provided
- [ ] T052 [US4] Update benchmark.py citation validation to call validate_citation_quality() when manifest is available
- [ ] T053 [US4] Update TestResult dataclass to add hallucinated_citations field (list of invalid citation references)
- [ ] T054 [US4] Update CLIReporter.generate_report() to display hallucinated citation warnings in failed questions section
- [ ] T055 [US4] Update JSONReporter.save_report() to include hallucinated_citations in per-question results

**Checkpoint**: At this point, User Stories 1, 2, 3, AND 4 should all work independently - citation validation is now enhanced with quality checks

---

## Phase 7: User Story 5 - Ground Truth Management (Priority: P2)

**Goal**: Enable easy addition, updating, and version control of benchmark Q&A pairs in human-readable format

**Independent Test**: Manually edit ground_truth.yaml to add new question-answer pair, re-run benchmark, verify new question is included in report

**Constitution Impact**:
- **Reproducible**: Ground truth changes are tracked in version control with commit history
- **Transparency**: Non-technical stakeholders can update test cases

### Implementation for User Story 5

- [ ] T056 [US5] Add validation in GroundTruthDataset.from_yaml() to check for duplicate question IDs
- [ ] T057 [US5] Add validation in GroundTruthDataset.from_yaml() to verify semantic versioning format for version field
- [ ] T058 [US5] Update ground_truth.yaml with inline YAML comments documenting question intent and expected citation sources
- [ ] T059 [US5] Create tests/benchmark/ground_truth_schema.yaml documenting YAML schema with field descriptions and examples
- [ ] T060 [US5] Add --validate-only flag to benchmark.py to check ground truth syntax without running benchmark
- [ ] T061 [US5] Implement ground truth version comparison in benchmark.py to warn if dataset version changed since last run
- [ ] T062 [US5] Update CLIReporter to display dataset version and creation date in report header

**Checkpoint**: At this point, User Stories 1-5 should all work independently - ground truth is now easily maintainable by non-developers

---

## Phase 8: User Story 6 - Regression Detection (Priority: P3)

**Goal**: Detect when LLM accuracy degrades over time by saving historical results and highlighting regressions

**Independent Test**: Run benchmark twice, manually change ground truth to fail second run, verify report shows regression with diff of expected vs actual answers

**Constitution Impact**:
- **Accuracy**: Enables proactive detection of model drift or configuration changes
- **Reproducible**: Historical results provide verifiable accuracy trends over time

### Implementation for User Story 6

- [ ] T063 [P] [US6] Create BenchmarkHistory dataclass in tests/benchmark/models/history.py to track past run results
- [ ] T064 [P] [US6] Implement load_baseline() function in tests/benchmark/reporters/regression.py to read most recent results JSON
- [ ] T065 [US6] Implement compare_results() function in tests/benchmark/reporters/regression.py to identify regressed questions (previously PASS, now FAIL)
- [ ] T066 [US6] Update benchmark.py to optionally load baseline results if --compare-baseline flag is provided
- [ ] T067 [US6] Update BenchmarkReport dataclass to include regressions list with question_id, previous_status, current_status, diff
- [ ] T068 [US6] Update CLIReporter.generate_report() to add regression section showing questions that now fail with expected vs actual diff
- [ ] T069 [US6] Update JSONReporter.save_report() to include regressions array in JSON output
- [ ] T070 [US6] Implement get_accuracy_trend() function in tests/benchmark/reporters/regression.py to calculate accuracy percentage over last N runs
- [ ] T071 [US6] Add --trend flag to benchmark.py to display accuracy trend summary from last 10 runs (if available)

**Checkpoint**: All user stories should now be independently functional - regression detection enables continuous quality monitoring

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T072 [P] Add docstrings to all public functions and classes following Google Python style guide
- [ ] T073 [P] Add type hints to all function signatures in validators/, reporters/, models/
- [ ] T074 Update quickstart.md with troubleshooting section for common errors (API unreachable, ground truth malformed, timeout issues)
- [ ] T075 Create docs/benchmark_architecture.md documenting system design, data flow, and extension points
- [ ] T076 [P] Add logging throughout benchmark.py using Python logging module for debug visibility
- [ ] T077 Run quickstart.md validation by following all setup steps on clean environment
- [ ] T078 [P] Create Makefile target `make benchmark` that runs scripts/benchmark.sh with default configuration
- [ ] T079 Update main README.md with benchmark suite section linking to quickstart.md
- [ ] T080 Add --verbose flag to benchmark.py to enable detailed per-question debug output during execution

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1, US2, US3 for MVP → US4, US5 → US6)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ MVP Core
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Extends US1 report with performance metrics ✅ MVP Core
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Enhances US1 execution with config management ✅ MVP Core
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Enhances US1 citation validation (optional for MVP)
- **User Story 5 (P2)**: Can start after Foundational (Phase 2) - Enhances US1 ground truth management (optional for MVP)
- **User Story 6 (P3)**: Depends on US1 complete (needs baseline results) - Can start after US1 checkpoint

### Within Each User Story

- Models before services/validators
- Validators before main benchmark runner integration
- Core implementation before reporting integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003, T004, T005)
- All Foundational tasks marked [P] can run in parallel (T006-T009, T011-T012)
- Once Foundational phase completes, US1, US2, US3, US4, US5 can start in parallel (if team capacity allows)
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all models for User Story 1 together:
Task T013: "Create BenchmarkQuestion dataclass in tests/benchmark/models/question.py"
Task T014: "Create TestResult dataclass in tests/benchmark/models/result.py"
Task T015: "Create GroundTruthDataset dataclass in tests/benchmark/models/dataset.py"

# Launch validators together (after models):
Task T016: "Implement fuzzy_match() in tests/benchmark/validators/fuzzy_match.py"
Task T017: "Implement validate_citations() in tests/benchmark/validators/citation_check.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3 - All P1)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T012) - CRITICAL
3. Complete Phase 3: User Story 1 (T013-T029)
4. Complete Phase 4: User Story 2 (T030-T037)
5. Complete Phase 5: User Story 3 (T038-T045)
6. **STOP and VALIDATE**: Run full benchmark against localhost:8080
7. Deploy/demo MVP (core accuracy + performance + reproducible execution)

**MVP Deliverables**:
- ✅ Single-command benchmark execution
- ✅ Accuracy validation with fuzzy matching (≥80% threshold)
- ✅ Citation coverage reporting (100% requirement)
- ✅ Performance metrics (p50/p95/p99 with <10s p95 validation)
- ✅ Dual-format reporting (CLI text + timestamped JSON)
- ✅ 20+ ground truth Q&A pairs

### Incremental Delivery (Post-MVP)

1. Add User Story 4 (T046-T055) → Test independently → Deploy/Demo (enhanced citation validation)
2. Add User Story 5 (T056-T062) → Test independently → Deploy/Demo (improved ground truth management)
3. Add User Story 6 (T063-T071) → Test independently → Deploy/Demo (regression detection)
4. Complete Phase 9: Polish (T072-T080) → Final release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T013-T029) - Core accuracy benchmark
   - **Developer B**: User Story 2 (T030-T037) - Performance metrics (needs US1 BenchmarkReport)
   - **Developer C**: User Story 3 (T038-T045) - Config management
3. After MVP (US1+US2+US3) complete:
   - **Developer A**: User Story 4 (T046-T055) - Citation quality
   - **Developer B**: User Story 5 (T056-T062) - Ground truth management
   - **Developer C**: User Story 6 (T063-T071) - Regression detection

---

## Notes

- **[P] tasks** = different files, no dependencies
- **[Story] label** maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Constitution checkpoints**: After US1 (Accuracy + Transparency), US2 (Performance), US3 (Reproducible)
- **MVP scope**: Phases 1-5 (Setup → Foundational → US1, US2, US3) = ~29 tasks
- **Post-MVP scope**: Phases 6-8 (US4, US5, US6) = ~26 tasks
- **Polish**: Phase 9 = ~9 tasks
- **Total**: 80 tasks organized by user story priority
