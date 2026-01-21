# Implementation Plan: LLM Benchmark Test Suite

**Branch**: `001-llm-benchmark-suite` | **Date**: 2026-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-llm-benchmark-suite/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a standalone LLM benchmark test suite that validates RAG-enabled chatbot accuracy, citation coverage, and performance using 20+ ground-truth Q&A pairs. The suite will use Python 3.11+, YAML for data storage, fuzzy matching for accuracy validation (Levenshtein ≥0.8 or keyword overlap ≥70%), and generate dual-format reports (CLI text + JSON). Results are stored in timestamped files under `results/` directory. The benchmark operates independently via HTTP requests to the LLM API endpoint, requiring no knowledge of RAG internals, and supports single-command execution after minimal setup.

## Technical Context

**Language/Version**: Python 3.11+ (aligns with existing `app/server.py` Python stack)  
**Primary Dependencies**: PyYAML (YAML parsing), python-Levenshtein (fuzzy matching), requests (HTTP client); no external AI/ML libraries  
**Storage**: File-based (YAML for ground truth at `tests/benchmark/ground_truth.yaml`, JSON for results at `results/benchmark_*.json`)  
**Testing**: pytest for unit tests of validators/reporters; benchmark suite itself is the integration test  
**Target Platform**: Linux/macOS (CPU-only, localhost API endpoint)  
**Project Type**: Single project with test infrastructure (extends existing `app/` codebase)  
**Performance Goals**: Complete 20-question benchmark run in <5 minutes excluding LLM inference time; p95 latency measurement accuracy within ±100ms  
**Constraints**: <10s p95 API response time (per constitution); 5-second timeout per request; <5% variance in performance metrics across runs on same hardware  
**Scale/Scope**: 20+ benchmark questions initially; extensible to 100+ questions; supports sequential execution (parallel mode post-MVP)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Accuracy Over Speed**: Benchmark validates that LLM responses prioritize correctness via fuzzy matching (not just speed metrics)
- [x] **Transparency**: Citation coverage validation ensures 100% of responses include source references
- [x] **Self-Contained**: All dependencies are open-source Python libraries; no cloud APIs used
- [x] **Reproducible**: Single-command execution (`python benchmark.py --api-url <URL>`) after `pip install -r requirements.txt`
- [x] **Performance**: Benchmark measures and validates <10s p95 latency requirement on CPU hardware
- [x] **Citation Check**: FR-003 mandates citation presence validation; FR-006 reports coverage percentage

**Status**: ✅ PASS - All gates satisfied. Benchmark suite validates constitution compliance without violating principles itself.

## Project Structure

### Documentation (this feature)

```text
specs/001-llm-benchmark-suite/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── api_contract.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
tests/
├── benchmark/
│   ├── __init__.py
│   ├── benchmark.py          # Main test runner (CLI entry point)
│   ├── ground_truth.yaml     # 20+ Q&A pairs with metadata
│   ├── config.py             # Configuration (API URL, timeouts, thresholds)
│   │
│   ├── validators/           # Accuracy & citation validation
│   │   ├── __init__.py
│   │   ├── fuzzy_match.py    # Levenshtein + keyword overlap logic
│   │   └── citation_check.py # Citation presence/structure validation
│   │
│   ├── reporters/            # Report generation
│   │   ├── __init__.py
│   │   ├── cli_reporter.py   # Human-readable CLI output
│   │   └── json_reporter.py  # Machine-readable JSON export
│   │
│   └── models/               # Data models
│       ├── __init__.py
│       ├── question.py       # BenchmarkQuestion entity
│       ├── result.py         # TestResult entity
│       └── report.py         # BenchmarkReport entity
│
├── unit/                     # Unit tests for benchmark components
│   └── test_validators.py
│
results/                      # Benchmark run results (gitignored)
└── benchmark_YYYY-MM-DD_HH-MM-SS.json

scripts/
└── benchmark.sh              # Wrapper script for `make benchmark`
```

**Structure Decision**: Extends existing single-project structure under `tests/` directory. Keeps benchmark suite separate from application code (`app/`) but integrates with existing Makefile command patterns. The `tests/benchmark/` module is self-contained and can be run independently of the main application.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: ✅ NO VIOLATIONS

All constitution principles are satisfied by the design:
- Self-contained (open-source dependencies only)
- Reproducible (single-command execution)
- Transparent (validates citation coverage)
- Accuracy-focused (fuzzy matching with thresholds)

No complexity justifications needed.

---

## Post-Design Constitution Re-Check

*GATE: Must pass after Phase 1 design. Validates that research and design decisions maintain constitution compliance.*

- [x] **Accuracy Over Speed**: Design validates LLM correctness via fuzzy matching (Levenshtein ≥0.8 or keyword ≥70%); performance is measured but not at expense of accuracy checks
- [x] **Transparency**: Citation validation logic ensures 100% coverage reporting; each TestResult tracks citation presence/structure
- [x] **Self-Contained**: All dependencies are open-source Python libraries (PyYAML, python-Levenshtein, requests, numpy, python-dotenv); no cloud APIs or paid services
- [x] **Reproducible**: Design supports single-command execution (`python benchmark.py --api-url <URL>`); setup takes <10 minutes per quickstart; all configs via env vars/CLI
- [x] **Performance**: Design includes p50/p95/p99 latency measurement; 5-second timeout enforces responsiveness; validates <10s p95 requirement
- [x] **Citation Check**: FR-003 implementation validates citation structure; FR-006 reports citation coverage percentage; API contract mandates citation presence

**Status**: ✅ PASS - Design maintains constitution compliance. No violations introduced during research/design phases.

**Added Value**:
- Benchmark suite provides *verifiable proof* of constitution compliance
- Enables regression detection for constitution violations (e.g., accuracy degradation, missing citations)
- Acts as quality gate for future LLM model changes
