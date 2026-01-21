# GitHub Actions CI/CD Plan - Quick Start Guide

## 📋 What Was Created

✅ **Specification** (spec.md) - Requirements for CI/CD pipeline
✅ **Implementation Plan** (plan.md) - Technical architecture with GitHub Actions
✅ **Plan Summary** (PLAN_SUMMARY.md) - Quick reference guide

Branch: `066-cicd-pipeline` | Status: Ready for Phase 0 Research

---

## 🎯 GitHub Actions Workflows to Implement

### 1. **PR Validation Workflow** (`pr-validation.yml`)
**Triggers**: On PR opened/updated/synchronized
**Jobs**:
- Test: Run pytest suite
- Lint: Format check (black) + style (ruff) + types (mypy)
- Build: Create Docker image (don't push)
- Benchmark Gate: Run benchmark suite, enforce 80% accuracy + 100% citations
**Output**: ✅/❌ on PR with detailed results

### 2. **Main Build Workflow** (`main-build.yml`)
**Triggers**: Push to main branch
**Jobs**:
- Build: Create Docker image
- Push Image: Push to ghcr.io with commit SHA tag (e.g., `main-abc1234`)
- Deploy: (Future) Deploy to staging
**Output**: Deployable Docker image in registry

### 3. **Benchmark Workflow** (`benchmark.yml`)
**Triggers**: Manual dispatch (workflow_dispatch)
**Jobs**:
- Run Benchmarks: Execute full test suite
- Regression Detection: Compare to previous results
- Report: Post detailed metrics
**Output**: Benchmark report with regression analysis

### 4. **Security Scan Workflow** (`security-scan.yml`)
**Triggers**: Daily schedule + on PR changes to dependencies
**Jobs**:
- Trivy Scan: Scan Docker image for vulnerabilities
- Pip Audit: Check Python dependencies for CVEs
**Output**: ✅/❌ with vulnerability list

### 5. **Release Workflow** (`release.yml`)
**Triggers**: Git tag push (format: `v*`)
**Jobs**:
- Build & Push: Create image with version tag (e.g., `v1.0.0`)
**Output**: Versioned Docker image in registry

---

## 🏗️ File Structure to Create

```
.github/
├── workflows/
│   ├── pr-validation.yml       (150 lines)
│   ├── main-build.yml          (120 lines)
│   ├── benchmark.yml           (80 lines)
│   ├── security-scan.yml       (60 lines)
│   └── release.yml             (100 lines)
└── scripts/
    ├── run-benchmarks.sh       (50 lines)
    ├── check-coverage.sh       (40 lines)
    └── validate-image.sh       (30 lines)

(Update existing)
├── Makefile                    (add test, lint, build targets)
└── .env.example                (add CI vars)
```

---

## 📊 Constitution Enforcement

| Principle | Gate | Enforcement |
|-----------|------|------------|
| **Accuracy** | 80% minimum | Benchmark fails if accuracy < 80% → merge blocked |
| **Transparency** | 100% citations | Benchmark fails if any answer lacks citations → merge blocked |
| **Performance** | <10s p95 latency | Warning if exceeded, not blocking |
| **Reproducible** | Make targets local | `make test`, `make lint` work identical to CI |
| **Self-Contained** | Free tier | GitHub Actions (free) + ghcr.io (included) |

---

## 🔧 Implementation Phases

| Phase | Focus | Tasks | Duration |
|-------|-------|-------|----------|
| 0 | Research | GitHub Actions patterns, Docker tagging | 1 day |
| 1 | Design | Data models, workflow contracts | 2-3 days |
| 2 | Foundation | Setup `.github/` dirs, GitHub config | 1 day |
| 3 | PR Validation | Test, lint, build jobs | 3-4 days |
| 4 | Main Build | Image versioning, registry push | 2-3 days |
| 5 | Benchmarking | Benchmark gates, reporting | 3-4 days |
| 6 | Polish | Security, notifications, caching | 2-3 days |
| 7 | Testing | Validate workflows end-to-end | 2 days |
| 8 | Docs | Developer guides, troubleshooting | 1-2 days |

**Total**: 3-4 weeks (can parallelize)

---

## 🚀 How to Use This Plan

1. **Phase 0 - Research** (in progress)
   ```bash
   /speckit.research  # Creates research.md with technology decisions
   ```

2. **Phase 1 - Design** (after research)
   ```bash
   /speckit.design    # Creates data-model.md + contracts/
   ```

3. **Phase 2-8 - Implementation** (after design)
   ```bash
   /speckit.tasks     # Creates tasks.md with 80-120 specific tasks
   # Then implement phase by phase
   ```

---

## 🔑 Key GitHub Actions Concepts

- **Workflow**: YAML file defining CI/CD pipeline
- **Trigger**: Event that starts workflow (push, PR, schedule, manual)
- **Job**: Unit of work in workflow (runs on runner)
- **Step**: Individual command/action in a job
- **Action**: Reusable workflow component (e.g., `actions/checkout@v4`)
- **Artifact**: Output from job (passed to other jobs or downloaded)
- **Secret**: Encrypted env var for credentials (registry token, etc.)
- **Runner**: Machine executing jobs (GitHub-hosted ubuntu-latest)

---

## ✅ Constitution Alignment

This CI/CD plan directly enforces and validates all constitution principles:

- ✅ **Accuracy Over Speed**: 80% accuracy gate blocks merges
- ✅ **Transparency**: 100% citation coverage validation required
- ✅ **Self-Contained**: GitHub Actions (free tier) + ghcr.io (included)
- ✅ **Reproducible**: Single `git push` triggers validation
- ✅ **Performance**: <10s p95 latency gate enforced

---

## 📝 Next Steps

1. Review plan.md and PLAN_SUMMARY.md
2. Run Phase 0 research when ready
3. Implement workflows phase by phase
4. Test each workflow with intentional PR/push events
5. Integrate with main branch protection rules

---

**Status**: 066-cicd-pipeline branch ready for Phase 0 research
**Commit**: 04ed651 (plan created)
