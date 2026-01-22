# Phase 0: Research & Technology Decisions

**Feature**: CI/CD Pipeline (066-cicd-pipeline)  
**Date**: 2026-01-21  
**Status**: Research Phase Output  
**Objective**: Document technology choices, GitHub Actions patterns, and integration strategies

---

## 1. GitHub Actions Platform Analysis

### Why GitHub Actions?

**Decision**: Use GitHub Actions as primary CI/CD platform

**Rationale**:
- ✅ **Self-Contained Principle**: Free tier for public repos, included with GitHub account
- ✅ **Cost**: No external service subscriptions needed (aligns with constitution)
- ✅ **Integration**: Native GitHub integration (PR checks, branch protection, secrets)
- ✅ **Documentation**: Extensive marketplace with 10,000+ pre-built actions
- ✅ **Linux Support**: ubuntu-latest runner includes Docker, Python 3.11+, and common tools
- ⚠️ **Quota**: Free tier = 2,000 minutes/month (sufficient for small team, optimize with caching)

**Alternatives Considered**:
- GitLab CI: Would require migrating repository
- CircleCI: External service, breaks self-contained principle
- Jenkins: Requires infrastructure management
- Travis CI: Legacy platform, declining support

**Decision**: ✅ GitHub Actions (APPROVED)

### Runner Strategy

**Decision**: Use GitHub-hosted ubuntu-latest runners for MVP

**Configuration**:
```yaml
runs-on: ubuntu-latest  # Latest Ubuntu LTS with Docker, Python 3.11+, git

# Alternative: Self-hosted runners (Phase 3+)
# For high-volume teams, set up self-hosted runner to avoid minute quotas
# runners-on: [self-hosted, linux, x64]
```

**Build Environment Includes**:
- Python 3.11+ (pre-installed)
- Docker + Docker Compose (pre-installed)
- git (pre-installed)
- Node.js + npm (not needed for this project)

**Performance Impact**: ~30-60s setup time per job (pulling runner, starting)

---

## 2. Docker Image Strategy

### Multi-Stage Build (for future optimization)

**Decision**: Single-stage build for MVP, plan multi-stage for Phase 6

**Current Dockerfile Analysis**:
```dockerfile
FROM python:3.11-slim          # ~120MB base image
COPY app /workspace/app        # Only app/, no tests
EXPOSE 8000
CMD ["python", "-u", "app/server.py", "0.0.0.0", "8000"]
```

**Production-Ready Strategy (Phase 6)**:
```dockerfile
# Stage 1: Build (includes test dependencies)
FROM python:3.11-slim as builder
RUN pip install -r requirements.txt

# Stage 2: Runtime (only runtime dependencies)
FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app /workspace/app
CMD ["python", "-u", "app/server.py", "0.0.0.0", "8000"]
```

**Build Time**: ~1-2 minutes (python:3.11-slim base + pip install)
**Image Size**: ~200-250MB final image

### Image Tagging Strategy

**Decision**: Commit SHA (short) + semantic versioning

**Tagging Scheme**:

```yaml
# On main branch: tag with commit SHA
docker tag hive-assistant:latest ghcr.io/org/hive-assistant:main-abc1234
# abc1234 = first 7 chars of commit SHA

# On Git tags (v*): tag with version + latest
docker tag hive-assistant:latest ghcr.io/org/hive-assistant:v1.0.0
docker tag hive-assistant:latest ghcr.io/org/hive-assistant:latest
```

**Rationale**:
- ✅ Deterministic: Same code = same SHA, reproducible
- ✅ Traceable: Can find exact commit from image tag
- ✅ Semantic: Version tags for stable releases
- ✅ Rollback: Easy to deploy previous SHA if needed

**Example Tags**:
- `ghcr.io/org/hive-assistant:main-abc1234` (PR merged, main branch)
- `ghcr.io/org/hive-assistant:main-def5678` (next commit)
- `ghcr.io/org/hive-assistant:v1.0.0` (Git tag, release)
- `ghcr.io/org/hive-assistant:latest` (latest release tag)

### Container Registry Choice

**Decision**: GitHub Container Registry (ghcr.io)

**Why ghcr.io**:
- ✅ Included with GitHub account (no external service)
- ✅ Free for public repos, generous quota
- ✅ Native GitHub integration (push credentials via GITHUB_TOKEN)
- ✅ Same authentication as GitHub
- ⚠️ No rate limits (unlike Docker Hub)

**Authentication in CI**:
```yaml
- uses: docker/login-action@v2
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}  # Auto-provided by GitHub
```

**Image Naming Convention**:
```
ghcr.io/{owner}/{repo}:{tag}
ghcr.io/antanipasf/hive-assistant:main-abc1234
```

---

## 3. Benchmark Suite Integration

### Benchmark Execution in CI

**Decision**: Run full benchmark suite in `pr-validation.yml` as quality gate

**Current Benchmark Implementation** (from 001-llm-benchmark-suite):
```python
tests/benchmark/benchmark.py --api-url http://localhost:8080

# Returns:
# - Accuracy % (PASS if ≥80%)
# - Citation Coverage % (PASS if 100%)
# - p50/p95/p99 latency (WARN if p95 >10s)
# - JSON report saved to results/benchmark_TIMESTAMP.json
```

### CI Benchmark Strategy

**Workflow Steps**:

1. **Build Docker image** (in PR validation job)
2. **Start container** with API running
3. **Wait for health check** (http://localhost:8080/health)
4. **Run benchmark suite** with `--api-url http://localhost:8080`
5. **Parse results** and fail if accuracy <80% or citations <100%
6. **Post results** as PR comment

**Implementation Pattern**:
```yaml
- name: Start API server in background
  run: docker run -d -p 8080:8000 hive-assistant:build

- name: Wait for API health
  run: |
    for i in {1..30}; do
      curl -s http://localhost:8080/health && break
      sleep 1
    done

- name: Run benchmarks
  run: python tests/benchmark/benchmark.py --api-url http://localhost:8080

- name: Check benchmark results
  if: always()
  run: |
    # Parse JSON results and fail if accuracy < 80%
    python scripts/check-benchmark-gates.py results/benchmark_*.json
```

### Benchmark Regression Detection

**Decision**: Compare current run to previous baseline

**Baseline Storage**:
- Store `results/benchmark_baseline.json` in repo
- On each main branch build, update baseline
- On PR, compare to baseline
- Flag questions that regressed (were PASS, now FAIL)

**Implementation**:
```python
# scripts/compare-benchmarks.py
import json

def detect_regressions(current_file, baseline_file):
    current = json.load(open(current_file))
    baseline = json.load(open(baseline_file))
    
    regressions = []
    for q_id, result in current['results'].items():
        if q_id in baseline['results']:
            prev = baseline['results'][q_id]
            if prev['status'] == 'PASS' and result['status'] == 'FAIL':
                regressions.append({
                    'question': q_id,
                    'prev_score': prev.get('accuracy_score'),
                    'curr_score': result.get('accuracy_score')
                })
    
    return regressions
```

### Benchmark Caching

**Decision**: Skip benchmarks if only documentation changed

**Implementation**:
```yaml
- name: Check if benchmark needed
  id: should_benchmark
  run: |
    # Get list of changed files
    if git diff --name-only origin/main | grep -qvE '\.md$|docs/'; then
      echo "benchmark_needed=true" >> $GITHUB_OUTPUT
    else
      echo "benchmark_needed=false" >> $GITHUB_OUTPUT
    fi

- name: Run benchmarks (conditional)
  if: steps.should_benchmark.outputs.benchmark_needed == 'true'
  run: python tests/benchmark/benchmark.py --api-url http://localhost:8080
```

---

## 4. Code Quality Gates Strategy

### Linting & Formatting Tools

**Decision**: black + ruff + mypy for Python code quality

**Tool Selection**:

| Tool | Purpose | Configuration |
|------|---------|---|
| **black** | Code formatter | Line length: 100, Python 3.11+ |
| **ruff** | Linter | Check: E, W, F, I (imports), B (bugbear) |
| **mypy** | Type checker | Strict mode, check_untyped_defs=true |
| **bandit** | Security | Check for hardcoded secrets, SQL injection |
| **pip-audit** | Dependency CVE | Fail on CRITICAL only |

**Local Development** (Makefile targets):
```makefile
.PHONY: fmt lint type-check security-check test

fmt:
	black tests/ app/
	ruff check --fix tests/ app/

lint:
	black --check tests/ app/
	ruff check tests/ app/

type-check:
	mypy tests/ app/

security-check:
	bandit -r app/
	pip-audit

test:
	pytest tests/
```

**CI Implementation**:
```yaml
- name: Format check
  run: black --check tests/ app/

- name: Lint
  run: ruff check tests/ app/

- name: Type check
  run: mypy tests/ app/

- name: Security scan
  run: bandit -r app/
```

### Test Coverage

**Decision**: Generate coverage reports, track trends

**Tool**: pytest + pytest-cov

```yaml
- name: Run tests with coverage
  run: pytest tests/ --cov=app --cov=tests/benchmark --cov-report=json --cov-report=term

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.json
```

**Coverage Goals**:
- Target: ≥80% code coverage
- Warn if drops below target
- Fail if drops >5% from previous run

---

## 5. Secret Management

### GitHub Secrets Strategy

**Decision**: Use GitHub Secrets for sensitive credentials

**Secrets to Store**:
- Container registry credentials (auto-provided via GITHUB_TOKEN)
- API keys (if any)
- Deployment credentials (post-MVP)

**Access Control**:
- Only available to workflows in main branch + PRs from branch owners
- Secrets not accessible to PRs from forks (security)
- Can be restricted to specific environments

**Implementation Pattern**:
```yaml
- uses: docker/login-action@v2
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}  # Auto-provided

# For custom secrets (if needed):
env:
  CUSTOM_API_KEY: ${{ secrets.CUSTOM_API_KEY }}
```

### Secrets Scanning in Code

**Decision**: Use bandit + git-secrets to prevent credential leakage

**Bandit checks**:
- Hardcoded passwords/tokens
- SQL injection vulnerabilities
- Unsafe random number generation

**GitHub native**: Enable "Secret scanning" in repo settings
- Auto-scans commits for common secret patterns
- Alerts if secrets detected

---

## 6. Workflow Orchestration Patterns

### Job Dependencies

**Decision**: Use explicit job dependencies for parallelization

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps: [ ... ]
    
  lint:
    runs-on: ubuntu-latest
    steps: [ ... ]
    
  build:
    needs: [test, lint]  # Runs after test + lint pass
    runs-on: ubuntu-latest
    steps: [ ... ]
    
  benchmark:
    needs: build
    runs-on: ubuntu-latest
    steps: [ ... ]
```

**Benefits**:
- Parallelization: test + lint run simultaneously
- Fail-fast: If test fails, skip lint + build
- Clear dependencies: Visible in GitHub UI

### Caching Strategy

**Decision**: Multi-level caching for dependency optimization

**Level 1: Pip Cache** (Python dependencies)
```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # Caches ~/.cache/pip
```

**Level 2: Docker Layer Cache**
```yaml
- uses: docker/build-push-action@v4
  with:
    cache-from: type=gha  # GitHub Actions cache
    cache-to: type=gha,mode=max
```

**Expected Cache Hit Rate**: >80% (from Docker layer + pip cache)

### Conditional Workflow Runs

**Decision**: Skip expensive jobs for documentation-only changes

```yaml
jobs:
  test:
    if: |
      !contains(github.event.head_commit.message, '[skip ci]') &&
      (github.event_name != 'pull_request' || 
       contains(github.event.pull_request.title, '[run tests]'))
    steps: [ ... ]

  benchmark:
    if: |
      github.event_name == 'push' ||
      (github.event.pull_request.draft == false &&
       !startsWith(github.head_ref, 'docs/'))
    steps: [ ... ]
```

---

## 7. Error Handling & Notifications

### Failure Handling

**Decision**: Explicit failure steps for clear error messages

```yaml
- name: Run benchmarks
  id: benchmark
  run: python tests/benchmark/benchmark.py --api-url http://localhost:8080
  continue-on-error: true

- name: Process benchmark results
  if: steps.benchmark.outcome == 'failure'
  run: |
    echo "❌ Benchmarks failed - accuracy or citations below threshold"
    echo "Rerun with: python tests/benchmark/benchmark.py --api-url http://localhost:8080"
    exit 1
```

### GitHub Status Checks

**Decision**: Require status checks for main branch protection

**Configuration**:
```yaml
# In GitHub repo settings:
branch_protection:
  required_status_checks:
    - "test (3.11)"
    - "lint"
    - "build"
    - "benchmark-gate"  # Only post-MVP
```

### PR Comments with Results

**Decision**: Post automated comments on PRs with CI results

```yaml
- name: Post benchmark results
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v6
  with:
    script: |
      const fs = require('fs');
      const results = JSON.parse(fs.readFileSync('results/benchmark_latest.json'));
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: `## Benchmark Results\n\n✅ Accuracy: ${results.accuracy}%\n✅ Citations: ${results.citations}%\n⏱️ p95: ${results.p95}ms`
      });
```

---

## 8. Performance Optimization

### Build Time Targets

**Decision**: Target <5 minutes for full PR validation

**Optimization Strategy**:
- Parallel jobs (test + lint simultaneously)
- Docker layer caching (reuse unchanged layers)
- Pip caching (avoid re-downloading packages)
- Skip benchmark for docs-only changes

**Expected Breakdown**:
- Setup: 30-45s
- Test: 60-90s
- Lint: 30-45s
- Build: 90-120s
- Benchmark: 120-180s (only for code changes)
- **Total**: 330-480s (~6-8 minutes)

**With Optimization**:
- Caching: Save 60-90s on deps
- Skip rules: Save 120-180s on docs-only PRs
- Parallelization: Already applied
- **Target**: 4-6 minutes

### Artifact Retention

**Decision**: Keep artifacts for debugging, auto-cleanup old runs

```yaml
- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: |
      .coverage
      test-report.xml
    retention-days: 30  # Auto-delete after 30 days
```

---

## 9. Local Development Parity

### Make Targets

**Decision**: Local make targets mirror CI commands

**Local Makefile**:
```makefile
.PHONY: test lint build benchmark verify

test:
	pytest tests/ -v

lint:
	black --check tests/ app/
	ruff check tests/ app/

build:
	docker build -t hive-assistant:local .

benchmark:
	./scripts/benchmark.sh --api-url http://localhost:8080

verify: test lint build
	@echo "✅ All checks passed"
```

**CI Usage**:
```bash
make test        # Runs in CI
make lint        # Runs in CI
make build       # Runs in CI
make benchmark   # Runs in CI
make verify      # Runs all
```

**Developer Usage** (local):
```bash
make verify      # Same as CI - ensures no surprises
```

---

## 10. Technology Stack Summary

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **CI/CD Platform** | GitHub Actions | Free, native to repo, self-contained |
| **Runners** | GitHub-hosted ubuntu-latest | Pre-built with Docker, Python 3.11+ |
| **Container Registry** | ghcr.io | Included with GitHub, free tier |
| **Code Formatter** | black | Industry standard, opinionated |
| **Linter** | ruff | Fast, written in Rust, Pythonic |
| **Type Checker** | mypy | Strict mode, catches type errors |
| **Security Scanner** | bandit | Python-specific, catches common issues |
| **Dependency Scanner** | pip-audit | Checks for known CVEs in requirements |
| **Image Security** | Trivy | Scans Docker images for vulnerabilities |
| **Test Framework** | pytest | Flexible, powerful, extensible |
| **Coverage** | pytest-cov + codecov | Track coverage trends |
| **Benchmarks** | Custom (existing) | Already implemented, just integrate |

---

## 11. Constitution Principle Enforcement

### How CI/CD Enforces Principles

**Accuracy Over Speed**:
- ✅ Benchmark gate requires 80% minimum accuracy
- ✅ Slow (5-10 min) PR validation ensures thoroughness
- ✅ Rejects fast but inaccurate answers

**Transparency**:
- ✅ Benchmark validates 100% citation coverage
- ✅ PR comments show detailed results
- ✅ All checks visible in GitHub UI

**Self-Contained**:
- ✅ GitHub Actions (free, included)
- ✅ ghcr.io (included with account)
- ✅ No external CI/CD services required

**Reproducible**:
- ✅ Benchmark uses seed control (deterministic)
- ✅ Same SHA produces same image
- ✅ Local make targets replicate CI

**Performance**:
- ✅ Latency gates enforce <10s p95
- ✅ Optimization targets <5 min CI validation
- ✅ No manual steps needed

---

## 12. Decisions Requiring Approval

- [x] Use GitHub Actions for CI/CD platform
- [x] Use ghcr.io for container registry  
- [x] Use ubuntu-latest runners
- [x] Implement benchmark as PR quality gate
- [x] Use black + ruff + mypy for code quality
- [x] Tag images with commit SHA + semantic versions
- [x] Require 80% code coverage minimum
- [x] Implement docker layer caching for performance

**Next Phase**: Phase 1 Design (data models, workflow contracts)
