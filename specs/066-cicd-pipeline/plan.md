# Implementation Plan: CI/CD Pipeline

**Branch**: `066-cicd-pipeline` | **Date**: 2026-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/066-cicd-pipeline/spec.md`

## Summary

Implement comprehensive GitHub Actions CI/CD pipeline for the Corporate Digital Assistant that automatically validates PRs, runs benchmarks enforcing constitution thresholds (80% accuracy, 100% citations, <10s p95), builds and publishes versioned Docker images to GitHub Container Registry, and provides code quality gates with clear feedback. The pipeline ensures every change to main branch produces a deployable artifact while preventing regressions through continuous benchmark execution.

## Technical Context

**Language/Version**: Python 3.11+ (application code), YAML (GitHub Actions workflows)  
**Primary Dependencies**: GitHub Actions, Docker, GitHub Container Registry (ghcr.io), pytest, black, ruff, mypy, bandit, pip-audit, Trivy  
**Storage**: GitHub Container Registry (images), GitHub Actions logs (build artifacts)  
**Testing**: pytest for unit tests, `tests/benchmark/benchmark.py` for integration/benchmark testing  
**Target Platform**: Linux (GitHub-hosted runners: ubuntu-latest), Docker containers  
**Project Type**: Single monolithic project (app/ + tests/)  
**Performance Goals**: PR validation <10 minutes, Docker build <5 minutes, cache hit rate >80%  
**Constraints**: <10s p95 latency (enforced), 80% accuracy gate (enforced), 100% citation coverage (enforced), no external API calls in CI (localhost only)  
**Scale/Scope**: Single repository, multiple workflows (lint, test, build, benchmark, deploy), ~25 GitHub Actions jobs total

## Constitution Check

*GATE: Must pass before implementation. Re-check after design completion.*

- [x] **Accuracy Over Speed**: Benchmark gates enforce 80% accuracy threshold - slow but accurate answers pass, fast but inaccurate fail
- [x] **Transparency**: Benchmark validates 100% citation coverage - all responses must include citations
- [x] **Self-Contained**: GitHub Actions is free for public repos, ghcr.io included with account, no external CI services required
- [x] **Reproducible**: Single `git push` triggers all validation - developers see same results locally (via make targets) and in CI
- [x] **Performance**: Benchmark validates <10s p95 latency - constitution requirement is automated, not aspirational
- [x] **Citation Check**: FR-006-008 explicitly validate citations and reject on failures

**Status**: ✅ PASS - CI/CD pipeline directly enforces constitution principles

## Project Structure

### Documentation (this feature)

```text
specs/066-cicd-pipeline/
├── plan.md              # This file (implementation details)
├── research.md          # Phase 0 (technology choices, GitHub Actions patterns)
├── data-model.md        # Phase 1 (workflow entities, job structures)
├── quickstart.md        # Phase 1 (developer guide for CI/CD)
├── contracts/           # Phase 1 (workflow input/output specs)
│   ├── pr-validation.yaml
│   ├── main-build.yaml
│   └── benchmark-gates.yaml
└── tasks.md             # Phase 2 (80-120 tasks across 6 phases)
```

### Source Code (repository root)

```text
.github/
├── workflows/           # GitHub Actions workflows (CREATED)
│   ├── pr-validation.yml       # PR checks: test, lint, build, benchmark
│   ├── main-build.yml          # Main branch: build, push image, deploy
│   ├── benchmark.yml           # Standalone benchmark workflow
│   ├── security-scan.yml       # Trivy + pip-audit
│   └── release.yml             # Semantic versioning on git tags
├── actions/             # Custom actions (if needed, post-MVP)
└── scripts/             # CI helper scripts (CREATED)
    ├── run-benchmarks.sh        # Wrapper for benchmark execution
    ├── check-coverage.sh        # Test coverage report
    └── validate-image.sh        # Post-build Docker image checks

.env.example            # UPDATED: Add CI-specific vars
Dockerfile              # EXISTING: No changes needed
Makefile                # UPDATED: Add CI targets (make test, make lint, etc.)
docker-compose.yml      # EXISTING: Used for local testing
requirements.txt        # EXISTING: Dependencies
tests/
├── benchmark/
│   ├── benchmark.py    # EXISTING: Used in CI
│   └── ground_truth.yaml
└── unit/              # FUTURE: pytest unit tests
```

**Structure Decision**: Single project with centralized `.github/workflows/` for all CI/CD definitions. Helper scripts in `.github/scripts/` for complex logic (benchmarking, coverage checks). Workflows are simple orchestrators that call make targets or scripts, keeping logic portable between local and CI environments.

## Complexity Tracking

**Violation Check**: No constitution violations. CI/CD pipeline directly enables and enforces constitution principles.

**Risk Assessment**:
- **Flaky benchmark tests**: Benchmark may fail intermittently if API is slow. Mitigation: Retry logic + clear failure messages
- **GitHub Actions quota**: Free tier has limits (~2000 minutes/month). Mitigation: Smart caching, skip rules for docs-only changes
- **Docker registry rate limits**: ghcr.io is included with GitHub, no external rate limits. Low risk.
- **Security vulnerabilities in dependencies**: Addressed via bandit + pip-audit. Moderate risk, well-mitigated.

**Complexity Justification**: 25 functional requirements require comprehensive workflow design, but most are standard CI patterns (test, lint, build, push). Benchmark integration adds complexity but is critical for constitution enforcement.

## Implementation Phases

### Phase 0: Research & Planning (Not a code phase)
- GitHub Actions workflow syntax and best practices
- Docker image tagging strategies (commit SHA vs semantic versioning)
- Benchmark suite integration patterns
- Secret management in GitHub Actions
- Container registry authentication
- **Deliverable**: research.md with technology decisions

### Phase 1: Design & Contracts
- Data models for CI workflow entities (Pipeline, Build, Artifact, QualityCheck)
- API contracts for workflow inputs/outputs
- Detailed workflow diagrams (PR validation flow, main build flow)
- Error handling strategy
- **Deliverable**: data-model.md, contracts/*.yaml, quickstart.md

### Phase 2-6: Implementation
- **Phase 2**: Foundation - Set up `.github/workflows/` directory, basic workflow skeleton
- **Phase 3**: PR Validation - pr-validation.yml with tests, linting, Docker build
- **Phase 4**: Main Build - main-build.yml with image push and versioning
- **Phase 5**: Benchmarking - Integrate benchmark suite execution and gates
- **Phase 6**: Polish - Security scanning, logging, notifications, documentation

### Phase 7: Integration Testing
- Create test PRs with intentional failures to verify CI catches them
- Verify benchmark regression detection works
- Test image push and tagging

### Phase 8: Documentation & Handoff
- Developer guide for troubleshooting CI failures
- Operations guide for managing secrets and runners
- Architecture documentation
- **Deliverable**: docs/ci-cd-guide.md, troubleshooting.md


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
