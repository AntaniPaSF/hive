# Phase 2-7: Implementation Tasks

> Status: READY FOR EXECUTION | 82 tasks across 6 phases
> Estimated effort: 120-160 dev-hours | Timeline: 3-4 weeks
> Phases: 2 (Foundation) → 3 (PR Validation) → 4 (Main Build) → 5 (Benchmarking) → 6 (Polish) → 7 (Testing)

---

## Phase 2: Foundation Setup (10 tasks, 8-12 hours)

### Task 2.1: Create .github directory structure
- **Description**: Create directories for workflows, scripts, and documentation
- **Files to create**:
  - `.github/workflows/` (empty)
  - `.github/scripts/` (empty)
  - `.github/CODEOWNERS` (reference file)
- **Success criteria**:
  - Directories exist and are tracked in git
  - CODEOWNERS added (CICD team responsible for .github/)
- **Time estimate**: 0.5 hours

### Task 2.2: Add branch protection rules
- **Description**: Configure GitHub branch protection for main branch
- **GitHub Settings**:
  - Require status checks to pass (tests, lint, build, benchmark)
  - Require code reviews: 1 approval
  - Require up-to-date branches before merge
  - Dismiss stale reviews on push
  - Require signed commits (optional, team decision)
- **Success criteria**:
  - Branch protection rules applied to main
  - Verified by attempting merge without approvals (should block)
- **Time estimate**: 1 hour

### Task 2.3: Configure GitHub Secrets
- **Description**: Set up secrets for CI/CD access
- **Secrets to configure**:
  - `GITHUB_TOKEN` (auto-provided, verify it works for ghcr.io)
  - `SLACK_WEBHOOK` (for notifications, optional)
- **GitHub Settings** → Secrets and variables → Actions
- **Success criteria**:
  - Secrets accessible in workflow (test with echo ${{ secrets.GITHUB_TOKEN }})
  - GITHUB_TOKEN can push to ghcr.io
- **Time estimate**: 1 hour

### Task 2.4: Create Makefile with verification targets
- **Description**: Add Makefile to repo root with CI-equivalent targets
- **File**: `Makefile`
- **Targets to add**:
  - `make verify` (run format, lint, test, build)
  - `make format` (black src/ tests/)
  - `make lint` (black check + ruff + mypy + bandit + pip-audit)
  - `make test` (pytest --cov)
  - `make build` (docker build -t hive-core:local .)
  - `make benchmark` (python -m tests.benchmark.benchmark)
  - `make run-api` (docker run -p 8000:8000 hive-core:local)
  - `make stop-api` (docker stop/rm)
  - `make clean` (__pycache__, .coverage, etc.)
- **Success criteria**:
  - `make verify` runs successfully for main branch code
  - All targets are documented
- **Time estimate**: 2 hours

### Task 2.5: Add development dependencies to requirements.txt
- **Description**: Ensure all tools are in requirements.txt for local development
- **Tools to add**:
  - pytest, pytest-cov
  - black, ruff, mypy
  - bandit, pip-audit
  - docker (might already be system package)
- **File**: `requirements.txt` (or `requirements-dev.txt`)
- **Success criteria**:
  - `pip install -r requirements.txt` installs all tools
  - `make lint` runs without import errors
- **Time estimate**: 1 hour

### Task 2.6: Create .env.example with CI variables
- **Description**: Document environment variables used in CI
- **File**: `.env.example`
- **Variables to document**:
  - ENV=test (or prod)
  - API_HOST=localhost
  - API_PORT=8000
  - BENCHMARK_TIMEOUT_SECONDS=300
  - BENCHMARK_SUITE=full (or smoke)
- **Success criteria**:
  - .env.example tracked in git (not secrets)
  - Developers can copy to .env.local and use
- **Time estimate**: 0.5 hours

### Task 2.7: Update Dockerfile for CI compatibility
- **Description**: Ensure Dockerfile is optimized and CI-compatible
- **Checks**:
  - Base image: `python:3.11-slim` (or newest compatible)
  - Health check endpoint: `/health` returns 200 OK
  - Startup time: < 10 seconds to /health ok
  - Image size: < 250 MB (target), < 300 MB (hard limit)
  - No root user running (security best practice)
- **File**: `Dockerfile`
- **Success criteria**:
  - `docker build` succeeds with < 250 MB size
  - `docker run` + `curl http://localhost:8000/health` responds 200 OK within 10s
  - No critical Trivy vulnerabilities
- **Time estimate**: 2 hours

### Task 2.8: Create GitHub Actions workflow scaffolding
- **Description**: Create empty .yml files for all 5 workflows (to be filled in Phase 3+)
- **Files to create**:
  - `.github/workflows/pr-validation.yml` (empty stub)
  - `.github/workflows/main-build.yml` (empty stub)
  - `.github/workflows/benchmark.yml` (empty stub, if separate)
  - `.github/workflows/security-scan.yml` (empty stub, if separate)
  - `.github/workflows/release.yml` (empty stub, if separate)
- **Content**: Just add name and description as comments
- **Success criteria**:
  - Files exist and are tracked
  - No YAML syntax errors (even if empty)
- **Time estimate**: 0.5 hours

### Task 2.9: Add documentation
- **Description**: Ensure all Phase 1-2 docs are in place
- **Files**:
  - `specs/066-cicd-pipeline/spec.md` (✅ from Phase 1 Specify)
  - `specs/066-cicd-pipeline/plan.md` (✅ from Phase 1 Plan)
  - `specs/066-cicd-pipeline/research.md` (✅ from Phase 0)
  - `specs/066-cicd-pipeline/data-model.md` (✅ from Phase 1 Design)
  - `specs/066-cicd-pipeline/contracts/workflow-pr-validation.yaml` (✅ from Phase 1 Design)
  - `specs/066-cicd-pipeline/contracts/workflow-main-build.yaml` (✅ from Phase 1 Design)
  - `specs/066-cicd-pipeline/quickstart.md` (✅ from Phase 1 Design)
- **Success criteria**:
  - All files present and committed
  - Links work (file references)
- **Time estimate**: 0.5 hours

### Task 2.10: Commit Phase 2 completion
- **Description**: Final commit for foundation phase
- **Commit message**: "build(foundation): Phase 2 - GitHub Actions setup and configuration"
- **Files to commit**: Makefile, .env.example, Dockerfile updates, empty workflow files, .github/CODEOWNERS
- **Success criteria**:
  - Clean git status
  - All changes committed to 066-cicd-pipeline branch
- **Time estimate**: 0.5 hours

---

## Phase 3: PR Validation Workflow (18 tasks, 24-32 hours)

### Task 3.1: Implement pr-validation.yml - job structure
- **Description**: Create pr-validation.yml with job names and triggers
- **File**: `.github/workflows/pr-validation.yml`
- **Content to add**:
  - name: "PR Validation"
  - on: [pull_request, pull_request_target]
  - env: REGISTRY, IMAGE_NAME, etc.
  - jobs: setup, tests, lint, build, benchmark (5 jobs)
- **Success criteria**:
  - File is valid YAML
  - Jobs section has all 5 job definitions
- **Time estimate**: 1 hour

### Task 3.2: Implement setup job
- **Description**: Implement the setup job with checkout, Python, Docker, caching
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - `actions/checkout@v4`
  - `actions/setup-python@v5` (Python 3.11, cache: pip)
  - `docker/setup-buildx-action@v3`
  - `actions/cache@v3` (pip cache)
- **Success criteria**:
  - Job runs without errors
  - Python 3.11.x available
  - pip cache restored
  - Docker buildx available
- **Time estimate**: 2 hours

### Task 3.3: Implement tests job
- **Description**: Add tests job with pytest, coverage, JUnit output
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Install: `pip install -r requirements.txt pytest pytest-cov`
  - Run: `pytest tests/ --cov=src/ --cov-report=json --junit-xml=test-results.xml`
  - Coverage gate: fail if < 80%
  - Upload artifacts: test-results.xml, coverage.json
- **Success criteria**:
  - Job runs, parses coverage, fails if < 80%
  - Artifacts uploaded and visible in Actions
- **Time estimate**: 3 hours

### Task 3.4: Implement lint job - formatting
- **Description**: Add black formatting check to lint job
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Install: `pip install black`
  - Run: `black --check src/ tests/`
  - Fail if formatting needed (exit code != 0)
  - Log which files need formatting
- **Success criteria**:
  - Job runs, detects formatting issues
  - Provides actionable error (list files)
- **Time estimate**: 1.5 hours

### Task 3.5: Implement lint job - linting
- **Description**: Add ruff linting to lint job
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Install: `pip install ruff`
  - Run: `ruff check src/ tests/ --output-format=json`
  - Parse JSON output for violation counts
  - Fail if any violations (besides INFO level)
- **Success criteria**:
  - Job detects linting violations
  - Outputs human-readable error
- **Time estimate**: 1.5 hours

### Task 3.6: Implement lint job - type checking
- **Description**: Add mypy type checking to lint job
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Install: `pip install mypy`
  - Run: `mypy src/ --json`
  - Parse JSON for error count
  - Fail if errors > 0
- **Success criteria**:
  - Job detects type errors
  - Lists files and line numbers with errors
- **Time estimate**: 1.5 hours

### Task 3.7: Implement lint job - security (bandit)
- **Description**: Add bandit security scanning to lint job
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Install: `pip install bandit`
  - Run: `bandit -r src/ -f json -o bandit.json`
  - Parse JSON for CRITICAL/HIGH severity
  - Fail if CRITICAL or HIGH found
- **Success criteria**:
  - Job detects security issues
  - Only fails on CRITICAL/HIGH (not MEDIUM/LOW)
- **Time estimate**: 1.5 hours

### Task 3.8: Implement lint job - dependency audit
- **Description**: Add pip-audit vulnerability scanning to lint job
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Install: `pip install pip-audit`
  - Run: `pip-audit --desc > pip-audit.json`
  - Parse for CRITICAL vulns (CVSS >= 9.0)
  - Fail if CRITICAL found
- **Success criteria**:
  - Job detects CVE vulnerabilities in dependencies
  - Fails on CRITICAL severity
- **Time estimate**: 1.5 hours

### Task 3.9: Implement build job - Docker build
- **Description**: Add Docker build and push to lint job
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Generate tags: `pr-{branch}-{short-sha}`
  - `docker/build-push-action@v5` with caching
  - Push to ghcr.io
  - Extract image digest
- **Success criteria**:
  - Image builds in < 180 seconds
  - Image pushed to ghcr.io
  - Tag pattern is correct
  - Cache hit rate > 80% on second run
- **Time estimate**: 3 hours

### Task 3.10: Implement build job - Trivy scan
- **Description**: Add Trivy vulnerability scan after Docker build
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Pull image: `docker pull ghcr.io/org/hive-core:pr-{tag}`
  - Scan: `trivy image --severity CRITICAL,HIGH --exit-code 1`
  - Fail if CRITICAL/HIGH vulnerabilities found
  - Upload scan results
- **Success criteria**:
  - Job detects image vulnerabilities
  - Fails on CRITICAL/HIGH
  - Scan results uploaded as artifact
- **Time estimate**: 2 hours

### Task 3.11: Implement benchmark job - API startup
- **Description**: Add benchmark job with API startup and health check
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Pull image: `docker pull ghcr.io/org/hive-core:pr-{tag}`
  - Spin up container: `docker run -d -p 8000:8000 ghcr.io/...`
  - Health check loop: `curl -f http://localhost:8000/health` (max 60s)
  - Fail if not healthy within 60s
- **Success criteria**:
  - Container starts and becomes healthy
  - Or job fails with timeout message if not healthy
- **Time estimate**: 2 hours

### Task 3.12: Implement benchmark job - run suite
- **Description**: Run full benchmark suite against API
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Run: `python -m tests.benchmark.benchmark --api-url http://localhost:8000 --suite full --output-json benchmark-results.json`
  - Parse results JSON for accuracy and citations_accuracy
  - Fail if accuracy < 80%
  - Fail if citations_accuracy < 100%
- **Success criteria**:
  - Benchmark runs to completion
  - Accuracy gate blocks merge if < 80%
  - Citation gate blocks merge if < 100%
- **Time estimate**: 2 hours

### Task 3.13: Implement benchmark job - regression detection
- **Description**: Detect benchmark regressions vs main branch
- **File**: `.github/workflows/pr-validation.yml`
- **Steps**:
  - Store main branch baseline (from artifact or dynamically fetch)
  - Compare current accuracy to baseline * 0.95
  - Fail if regression detected
  - Store current results for future comparisons
- **Success criteria**:
  - Regression detection works
  - Fails merge if accuracy dropped > 5%
- **Time estimate**: 2 hours

### Task 3.14: Add PR comment reporting
- **Description**: Post automatic PR comment with results
- **File**: `.github/workflows/pr-validation.yml`
- **Script**: Create `.github/scripts/pr-comment.sh`
- **Content**:
  - Parse all job results
  - Format as markdown table (tests, coverage, lint violations, etc.)
  - Post via GitHub API
  - Include link to full logs
- **Success criteria**:
  - Comment automatically posted on every PR
  - Shows pass/fail summary
  - Includes links to failed steps
- **Time estimate**: 2 hours

### Task 3.15: Add conditional job dependencies
- **Description**: Set job dependencies to run in optimal order
- **File**: `.github/workflows/pr-validation.yml`
- **Dependencies**:
  - setup (runs first)
  - tests, lint (parallel after setup)
  - build (after tests + lint pass)
  - benchmark (after build passes)
- **Success criteria**:
  - Jobs run in correct dependency order
  - Parallel jobs save time vs sequential
- **Time estimate**: 1 hour

### Task 3.16: Add skip conditions
- **Description**: Skip expensive jobs for doc-only PRs
- **File**: `.github/workflows/pr-validation.yml`
- **Logic**:
  - Skip benchmarks if only .md, .yaml files changed
  - Skip full build if only docs changed
  - Always run tests + lint
- **Success criteria**:
  - PR with only README.md changes skips benchmark
  - PR with code changes runs full validation
- **Time estimate**: 1 hour

### Task 3.17: Add timeouts and error handling
- **Description**: Add timeout-minutes and continue-on-error as needed
- **File**: `.github/workflows/pr-validation.yml`
- **Timeouts**:
  - setup: 10 minutes
  - tests: 15 minutes
  - lint: 10 minutes
  - build: 20 minutes
  - benchmark: 30 minutes
- **Error handling**:
  - Don't continue-on-error for critical jobs
  - Allow failures for informational jobs (e.g., warnings)
- **Success criteria**:
  - Jobs timeout gracefully
  - No hanging workflows
- **Time estimate**: 1 hour

### Task 3.18: Test pr-validation.yml end-to-end
- **Description**: Create test PR and verify all steps work
- **Steps**:
  - Push feature branch with small code change
  - Create PR against main
  - Verify all 5 jobs run
  - Verify comment posted with results
  - Check that image is pushed to ghcr.io
  - Verify benchmark results are accurate
- **Success criteria**:
  - PR shows all 5 green checkmarks
  - Comment has complete report
  - Image visible in ghcr.io
- **Time estimate**: 3 hours (includes debugging if needed)

---

## Phase 4: Main Build Workflow (10 tasks, 12-16 hours)

### Task 4.1: Create main-build.yml structure
- **Description**: Create main-build.yml for main branch pushes
- **File**: `.github/workflows/main-build.yml`
- **Content**:
  - name: "Main Build"
  - on: [push: branches: [main]]
  - jobs: build-and-push, benchmark, notify
- **Success criteria**:
  - File is valid YAML
  - Triggered only on main branch
- **Time estimate**: 1 hour

### Task 4.2: Implement build-and-push job
- **Description**: Build and push production image with main-{sha} and latest tags
- **File**: `.github/workflows/main-build.yml`
- **Steps**:
  - Generate tags: main-{short-sha}, latest
  - Build and push with Docker BuildKit caching
  - Extract digest
  - Run Trivy scan (must pass)
- **Success criteria**:
  - Image tagged main-abc1234 and latest
  - Both tags pushed to ghcr.io
  - Trivy scan passes
- **Time estimate**: 2 hours

### Task 4.3: Implement benchmark job for main
- **Description**: Run benchmark on main to establish baseline
- **File**: `.github/workflows/main-build.yml`
- **Steps**:
  - Pull main-{sha} image
  - Spin up API
  - Run full benchmark suite
  - Store results for future PR comparisons
  - No accuracy gate (for info only, all PRs gate against this)
- **Success criteria**:
  - Benchmark runs successfully
  - Results stored for baseline comparisons
  - Job doesn't fail even if accuracy is low (for debug)
- **Time estimate**: 2 hours

### Task 4.4: Add caching to main workflow
- **Description**: Ensure main workflow benefits from Docker caching
- **File**: `.github/workflows/main-build.yml`
- **Caching**:
  - Use gha cache backend for Docker layers
  - Cache should hit 85-95% of layers (build < 30s)
- **Success criteria**:
  - Build time < 30 seconds (cached) vs 120s (uncached)
  - Cache stats visible in build logs
- **Time estimate**: 1 hour

### Task 4.5: Create notification script
- **Description**: Create script to send Slack/email notifications
- **File**: `.github/scripts/notify.sh`
- **Content**:
  - On success: "Main build succeeded, image: ghcr.io/org/hive-core:main-{sha}"
  - On failure: "Main build failed, check logs"
  - Include benchmark accuracy link
  - Post to Slack webhook (if configured)
- **Success criteria**:
  - Script runs without errors
  - Can be tested locally
- **Time estimate**: 1.5 hours

### Task 4.6: Implement notify job
- **Description**: Add notify job to main workflow
- **File**: `.github/workflows/main-build.yml`
- **Steps**:
  - Call .github/scripts/notify.sh
  - Pass build status, image tag, benchmark results
  - Run on success and on failure (use if: always())
- **Success criteria**:
  - Notifications sent on main builds
  - Include relevant build metadata
- **Time estimate**: 1 hour

### Task 4.7: Add automated releases
- **Description**: Create releases.yml for Git tag triggers
- **File**: `.github/workflows/release.yml` (or part of main-build.yml)
- **Trigger**: on: [push: tags: "v*.*.*"]
- **Steps**:
  - Build image
  - Tag with semantic version: v1.0.0
  - Push to ghcr.io
  - Create GitHub Release
- **Success criteria**:
  - Pushing git tag triggers build
  - Image has semantic version tag
  - GitHub Release created
- **Time estimate**: 2 hours

### Task 4.8: Add secrets handling
- **Description**: Ensure secrets are properly injected and not exposed
- **File**: `.github/workflows/main-build.yml`
- **Secrets used**:
  - GITHUB_TOKEN (for ghcr.io login, auto-provided)
  - SLACK_WEBHOOK (for notifications, optional)
- **Security**:
  - No secrets printed in logs
  - Mask secrets in output
  - Use ${{ secrets.SECRET_NAME }}
- **Success criteria**:
  - Secrets not exposed in logs
  - Can be verified by checking build output
- **Time estimate**: 1 hour

### Task 4.9: Add status checks and required reviews
- **Description**: Configure GitHub to require status checks on main
- **File**: Branch protection rules (GitHub Settings)
- **Configuration**:
  - Require main-build workflow to pass before merge
  - Require PR review
  - Require branch to be up to date
- **Success criteria**:
  - Can verify by attempting merge without passing checks (should block)
- **Time estimate**: 1 hour

### Task 4.10: Test main-build.yml end-to-end
- **Description**: Merge PR to main and verify build runs
- **Steps**:
  - Complete a PR (all checks passing)
  - Merge to main
  - Verify main-build.yml workflow runs
  - Verify image tagged main-{sha} and latest
  - Verify image in ghcr.io
  - Verify benchmark runs and baseline stored
  - Verify notification sent
- **Success criteria**:
  - Main build completes successfully
  - Image visible in ghcr.io with correct tags
  - Can pull and run: `docker run ghcr.io/org/hive-core:latest`
- **Time estimate**: 2 hours

---

## Phase 5: Benchmarking Integration (15 tasks, 18-24 hours)

### Task 5.1: Analyze existing benchmark.py
- **Description**: Review tests/benchmark/benchmark.py to understand test format
- **File**: `tests/benchmark/benchmark.py` (from 001-llm-benchmark-suite)
- **Analysis**:
  - What metrics does it track? (accuracy, latency, citations)
  - What input format? (YAML, JSON)
  - What output format? (JSON, XML)
  - How to integrate with CI?
- **Success criteria**:
  - Document integration points
  - Identify what CI needs to parse/validate
- **Time estimate**: 2 hours

### Task 5.2: Add CI-specific benchmark mode
- **Description**: Extend benchmark.py with CI mode (faster, deterministic)
- **File**: `tests/benchmark/benchmark.py`
- **Features**:
  - --suite flag: full (all tests) or smoke (subset for CI)
  - --output-format: json or junit
  - --api-url: configurable API endpoint
  - Deterministic results (same seed for reproducibility)
- **Success criteria**:
  - benchmark.py accepts CI arguments
  - Smoke suite runs in < 2 minutes
  - Full suite runs in < 5 minutes
  - Output is machine-readable JSON
- **Time estimate**: 2 hours

### Task 5.3: Parse benchmark JSON output
- **Description**: Create script to parse benchmark results and extract gates
- **File**: `.github/scripts/check-benchmark.sh`
- **Parsing**:
  - Extract accuracy: must be >= 80%
  - Extract citations_accuracy: must be 100%
  - Extract latency p95: warning if > 1000ms
  - Compare to baseline: must not regress > 5%
- **Output**:
  - JSON with pass/fail status
  - Human-readable message for PR comment
- **Success criteria**:
  - Script correctly parses benchmark JSON
  - Fails if accuracy < 80%
  - Fails if citations_accuracy < 100%
  - Warns (doesn't fail) if latency > 1000ms
- **Time estimate**: 2 hours

### Task 5.4: Store benchmark baselines
- **Description**: Implement baseline storage for regression detection
- **Storage options**:
  - Option A: Store in GitHub artifact per main build
  - Option B: Store in repo (e.g., .github/benchmarks/main.json)
  - Option C: Use GitHub API to fetch latest main build artifact
- **Recommendation**: Option A (artifact is clean, no repo bloat)
- **Implementation**:
  - After main build benchmark: upload as artifact named "main-benchmark"
  - In PR: download latest main-benchmark artifact
  - Compare PR results to main baseline
- **Success criteria**:
  - PR can access main branch baseline
  - Regression detection works
  - Baseline updates after each main push
- **Time estimate**: 2 hours

### Task 5.5: Add regression detection logic
- **Description**: Implement regression detection in check-benchmark.sh
- **File**: `.github/scripts/check-benchmark.sh`
- **Logic**:
  - Read main baseline accuracy
  - Read current PR accuracy
  - If current < (baseline * 0.95): REGRESSION
  - Output JSON with regression_detected: true/false
- **Success criteria**:
  - Detects accuracy drop > 5%
  - Doesn't flag normal variation
- **Time estimate**: 1 hour

### Task 5.6: Add benchmark result visualization
- **Description**: Create script to generate markdown table of results
- **File**: `.github/scripts/benchmark-summary.sh`
- **Output**:
  ```
  | Metric | Value | Baseline | Status |
  |--------|-------|----------|--------|
  | Accuracy | 85.2% | 82.5% | ✅ |
  | Citations | 100% | 100% | ✅ |
  | P95 Latency | 487ms | 520ms | ✅ |
  ```
- **Success criteria**:
  - Markdown table renders correctly in PR comments
  - Includes status indicators (✅ pass, ⚠️ warning, ❌ fail)
- **Time estimate**: 1 hour

### Task 5.7: Store benchmark artifacts
- **Description**: Ensure benchmark results are stored as GitHub Actions artifacts
- **File**: `.github/workflows/pr-validation.yml` (benchmark job)
- **Artifacts**:
  - benchmark-results.json (full results, retain 30 days)
  - benchmark-results.xml (JUnit format, for integration)
  - benchmark-detailed.html (optional, if generated)
- **Upload**:
  - `actions/upload-artifact@v3`
  - Name: "benchmark-results"
- **Success criteria**:
  - Artifacts visible in Actions tab for each PR
  - Downloadable for analysis
- **Time estimate**: 1 hour

### Task 5.8: Add benchmark timeout handling
- **Description**: Add graceful timeout handling for long-running benchmarks
- **File**: `.github/workflows/pr-validation.yml`
- **Implementation**:
  - Benchmark job timeout: 30 minutes
  - API startup timeout: 60 seconds
  - Benchmark suite timeout: 25 minutes
  - If timeout: fail with clear message
- **Success criteria**:
  - Job times out gracefully if benchmark runs > 30 min
  - Error message is clear: "Benchmark suite exceeded 25 min"
- **Time estimate**: 1 hour

### Task 5.9: Add benchmark skip conditions
- **Description**: Skip benchmarks for quick CI runs (docs-only PRs)
- **File**: `.github/workflows/pr-validation.yml`
- **Logic**:
  - If PR changes only: .md, .yaml, .env files → skip benchmark
  - If PR changes code: run benchmark
  - Option to force benchmark: add label "benchmark-required"
- **Success criteria**:
  - PR with only README.md changes skips benchmark (saves 3 min)
  - PR with code changes runs benchmark
  - Label can force benchmark even for doc changes
- **Time estimate**: 1.5 hours

### Task 5.10: Add benchmark performance tracking
- **Description**: Track benchmark suite performance over time
- **File**: `.github/scripts/track-benchmark-performance.sh`
- **Tracking**:
  - Store p50, p95, p99 latencies per build
  - Detect performance degradation trends
  - Alert if P95 increases > 10% vs last 5 builds
- **Success criteria**:
  - Can generate trend report
  - Detects performance regressions
- **Time estimate**: 2 hours

### Task 5.11: Add benchmark question sampling
- **Description**: Include sample failed questions in PR comments
- **File**: `.github/scripts/benchmark-summary.sh`
- **Content**:
  - If any questions failed: show 3 samples
  - Show question, expected, actual, why it failed
  - Format as markdown details (collapsible)
- **Success criteria**:
  - PR comment shows sample failed questions
  - Helps developers debug accuracy issues
- **Time estimate**: 1.5 hours

### Task 5.12: Add benchmark local validation
- **Description**: Create script to run benchmark locally matching CI
- **File**: `.github/scripts/run-benchmarks-local.sh` (or Makefile target)
- **Steps**:
  - `docker build -t hive-core:local .`
  - `docker run -d -p 8000:8000 hive-core:local`
  - Wait for health
  - Run benchmark suite
  - Compare results to CI format
- **Success criteria**:
  - Developers can run `make benchmark` locally
  - Format matches CI output
  - Can debug locally before pushing
- **Time estimate**: 1.5 hours

### Task 5.13: Test benchmark accuracy gate
- **Description**: Create test PR with intentionally low accuracy
- **Steps**:
  - Create PR with code that reduces accuracy (e.g., remove important retrieval)
  - Push and verify CI detects accuracy < 80%
  - Verify PR comment shows failure
  - Verify merge is blocked
- **Success criteria**:
  - Accuracy gate works: PR with 76% accuracy is blocked
  - Error message is clear
- **Time estimate**: 2 hours

### Task 5.14: Test benchmark citation gate
- **Description**: Create test PR with missing citations
- **Steps**:
  - Create PR where some questions don't cite sources
  - Push and verify CI detects citations < 100%
  - Verify merge is blocked
- **Success criteria**:
  - Citations gate works: PR with 95% citations is blocked
  - Error message is clear
- **Time estimate**: 2 hours

### Task 5.15: Test benchmark regression detection
- **Description**: Create test PR that regresses accuracy
- **Steps**:
  - Establish baseline on main (e.g., 82% accuracy)
  - Create PR that reduces accuracy to 78% (< 82% * 0.95)
  - Verify regression is detected
  - Verify merge is blocked
- **Success criteria**:
  - Regression detection works
  - Merge blocked with clear message
- **Time estimate**: 2 hours

---

## Phase 6: Polish & Additional Features (12 tasks, 14-18 hours)

### Task 6.1: Add security scanning workflow
- **Description**: Optional separate workflow for comprehensive security scanning
- **File**: `.github/workflows/security-scan.yml` (optional)
- **Scans**:
  - Trivy image scanning (already in main workflow)
  - SAST: bandit (already in lint)
  - Dependency scan: pip-audit (already in lint)
  - Optional: GitHub code scanning (CodeQL)
- **Trigger**: On PR or schedule (weekly)
- **Success criteria**:
  - Workflow runs without errors
  - Provides actionable security feedback
- **Time estimate**: 2 hours

### Task 6.2: Add performance benchmarking
- **Description**: Track performance metrics over time
- **File**: `.github/scripts/track-performance.sh`
- **Metrics**:
  - Build time trend (optimization over time)
  - Test execution time trend
  - Image size trend
  - Benchmark P95 latency trend
- **Output**: Optional performance dashboard or report
- **Success criteria**:
  - Can generate performance report
  - Detects regressions (slower builds, larger images)
- **Time estimate**: 2 hours

### Task 6.3: Add Docker image layer caching optimization
- **Description**: Optimize Dockerfile for maximum cache hits
- **File**: `Dockerfile`
- **Optimization**:
  - Move RUN pip install before COPY src/
  - Separate dependencies layer from code layer
  - Cache dependencies (rarely changes) separately from code (often changes)
  - Target: 85-95% cache hit rate
- **Success criteria**:
  - Build time with cache < 20 seconds
  - Build time without cache 120-180 seconds
  - Cache hit rate > 85% tracked in logs
- **Time estimate**: 2 hours

### Task 6.4: Add workflow notifications
- **Description**: Add Slack/email notifications for workflow results
- **File**: `.github/workflows/pr-validation.yml` and `.github/workflows/main-build.yml`
- **Implementation**:
  - On PR failure: post Slack message with link
  - On main build success: post Slack with image tag
  - Optional: email digest of daily CI stats
- **Success criteria**:
  - Notifications sent correctly
  - Include actionable links to logs
- **Time estimate**: 1.5 hours

### Task 6.5: Add workflow documentation
- **Description**: Create workflow-specific documentation
- **Files**:
  - `.github/workflows/README.md` - overview of all workflows
  - `.github/workflows/TROUBLESHOOTING.md` - common issues
  - `.github/scripts/README.md` - script documentation
- **Content**:
  - What does each workflow do?
  - When does it run?
  - How to debug if it fails?
  - What secrets/permissions are needed?
- **Success criteria**:
  - Documentation is complete and accurate
  - New developers can understand workflows
- **Time estimate**: 2 hours

### Task 6.6: Add workflow status badge
- **Description**: Add CI status badge to README.md
- **File**: `README.md`
- **Content**:
  - Badge showing pr-validation status
  - Links to latest build
  - ```markdown
    ![PR Validation](https://github.com/org/hive-core/actions/workflows/pr-validation.yml/badge.svg)
    ```
- **Success criteria**:
  - Badge appears on GitHub repo page
  - Reflects current CI status
- **Time estimate**: 0.5 hours

### Task 6.7: Add workflow cost optimization
- **Description**: Monitor GitHub Actions usage and optimize costs
- **File**: `.github/workflows/cost-report.yml` (optional)
- **Features**:
  - Track minutes used per workflow
  - Alert if approaching free tier limits (2000 min/month)
  - Suggest optimizations (caching, conditional runs)
- **Success criteria**:
  - Can generate cost report
  - Identifies optimization opportunities
- **Time estimate**: 1.5 hours

### Task 6.8: Add multi-platform builds
- **Description**: Optional: build images for multiple architectures
- **File**: `.github/workflows/main-build.yml`
- **Platforms**: linux/amd64, linux/arm64 (if team uses Mac M1/M2)
- **Implementation**: Use `docker buildx build --platform` multi-platform builds
- **Note**: May increase build time, consider for later
- **Success criteria**:
  - Build succeeds for multiple platforms
  - Image manifest includes all platforms
- **Time estimate**: 2 hours (optional, skip if not needed)

### Task 6.9: Add GitHub Actions cache optimization
- **Description**: Optimize cache key strategy for better hit rates
- **File**: `.github/workflows/pr-validation.yml`
- **Optimization**:
  - Cache key includes requirements.txt hash
  - Separate cache for main and PRs (main has more stable cache)
  - Override cache for PR dependencies
- **Success criteria**:
  - Cache hit rate > 85%
  - First build slightly slower, subsequent builds < 5 seconds for setup
- **Time estimate**: 1 hour

### Task 6.10: Add workflow debugging features
- **Description**: Add tmate for SSH debugging if needed
- **File**: `.github/workflows/pr-validation.yml`
- **Feature**: Optional tmate step (requires label "debug")
- **Usage**: Add "debug" label to PR to enable SSH access to runner
- **Success criteria**:
  - Can SSH into runner for debugging
  - Only enabled for explicitly labeled PRs
  - Can inspect environment, logs, etc.
- **Time estimate**: 1 hour

### Task 6.11: Add workflow concurrency controls
- **Description**: Prevent parallel runs of same workflow
- **File**: `.github/workflows/pr-validation.yml` and `.github/workflows/main-build.yml`
- **Implementation**:
  - Use `concurrency:` key
  - Cancel in-progress runs when new push
  - Prevents resource waste
- **Success criteria**:
  - Only one instance of workflow runs per branch
  - New push cancels old run
- **Time estimate**: 1 hour

### Task 6.12: Final Polish and Testing
- **Description**: End-to-end testing of all workflow features
- **Steps**:
  - Create PR with code and test changes
  - Verify all 5 jobs run correctly
  - Check PR comment format
  - Verify image in ghcr.io
  - Merge and verify main-build runs
  - Verify image tagged "latest"
  - Clean up test PRs
- **Success criteria**:
  - All workflows run end-to-end
  - No manual intervention needed
  - Results are clear and actionable
- **Time estimate**: 3 hours

---

## Phase 7: Testing & Validation (8 tasks, 10-14 hours)

### Task 7.1: Create test PR for passing scenario
- **Description**: Create PR that passes all checks
- **Steps**:
  - Small code change with tests
  - Run `make verify` locally (should pass)
  - Push PR
  - Verify all 5 checks pass
  - Verify comment shows "✅ All checks passed"
  - Merge and verify main build runs
- **Success criteria**:
  - PR merges successfully
  - Main build completes
- **Time estimate**: 1.5 hours

### Task 7.2: Create test PR for test failure
- **Description**: Create PR with failing test
- **Steps**:
  - Break a test (make it fail assertion)
  - Push PR
  - Verify tests job fails
  - Verify comment shows failure
  - Fix test and re-push
  - Verify CI passes
- **Success criteria**:
  - CI detects test failures
  - Error message is clear
  - Re-push after fix works
- **Time estimate**: 1 hour

### Task 7.3: Create test PR for coverage failure
- **Description**: Create PR with insufficient coverage
- **Steps**:
  - Add code without tests (reduces coverage)
  - Push PR
  - Verify tests job fails (coverage < 80%)
  - Verify comment shows coverage % and failure reason
  - Add tests and re-push
  - Verify CI passes
- **Success criteria**:
  - Coverage gate works
  - Feedback is clear
- **Time estimate**: 1 hour

### Task 7.4: Create test PR for linting failure
- **Description**: Create PR with linting issues
- **Steps**:
  - Add code that violates linting rules (unused import, etc.)
  - Push PR
  - Verify lint job fails
  - Verify comment shows which files/rules violated
  - Fix and re-push
- **Success criteria**:
  - Lint job detects violations
  - Helpful error messages
- **Time estimate**: 1 hour

### Task 7.5: Create test PR for type checking failure
- **Description**: Create PR with type errors
- **Steps**:
  - Add code with type mismatch (pass string where int expected)
  - Push PR
  - Verify lint job fails (mypy detects)
  - Verify comment shows type error location
  - Fix types and re-push
- **Success criteria**:
  - Type checking works
  - Error is actionable
- **Time estimate**: 1 hour

### Task 7.6: Create test PR for security issue
- **Description**: Create PR with security vulnerability
- **Steps**:
  - Add code with security issue (hardcoded password, unsafe pickle use, etc.)
  - Push PR
  - Verify lint job fails (bandit detects)
  - Verify comment shows security risk
  - Fix and re-push
- **Success criteria**:
  - Security scanning works
  - Blocks insecure code
- **Time estimate**: 1 hour

### Task 7.7: Create test PR for benchmark failure
- **Description**: Create PR with accuracy below 80%
- **Steps**:
  - Break LLM accuracy (e.g., remove key prompt section)
  - Push PR
  - Verify benchmark job runs
  - Verify accuracy < 80%
  - Verify comment shows failure
  - Verify merge is blocked
  - Fix accuracy and re-push
- **Success criteria**:
  - Accuracy gate works
  - Merge is blocked
- **Time estimate**: 2 hours

### Task 7.8: Create regression test
- **Description**: Create PR that would cause accuracy regression
- **Steps**:
  - Establish baseline on main (e.g., 85% accuracy)
  - Create PR that reduces accuracy to 80.5% (regression of 4.5%)
  - Verify regression detection works
  - Verify merge is blocked
  - Verify message is clear: "Regression: 80.5% vs baseline 85%"
- **Success criteria**:
  - Regression detection works correctly
  - Doesn't fail on minor normal variation
- **Time estimate**: 2 hours

---

## Phase 8: Documentation & Handoff (5 tasks, 6-8 hours)

### Task 8.1: Create CONTRIBUTING.md
- **Description**: Guide for developers on CI/CD processes
- **File**: `CONTRIBUTING.md`
- **Content**:
  - How to set up development environment
  - How to run tests locally
  - How to submit a PR
  - Understanding CI failures and how to fix them
  - Links to workflow documentation
- **Success criteria**:
  - Complete and clear
  - New developers can follow it
- **Time estimate**: 2 hours

### Task 8.2: Create DEPLOYMENT.md
- **Description**: Guide for releases and deployments
- **File**: `DEPLOYMENT.md`
- **Content**:
  - How to release a new version
  - Git tag naming convention (v1.0.0)
  - What happens when tag is pushed
  - How to verify deployment
  - Rollback procedures (if applicable)
- **Success criteria**:
  - Complete and actionable
  - Team can follow for releases
- **Time estimate**: 1.5 hours

### Task 8.3: Create TROUBLESHOOTING.md
- **Description**: Common CI issues and solutions
- **File**: `TROUBLESHOOTING.md`
- **Content**:
  - "CI takes too long" → cache optimization tips
  - "Tests pass locally but fail in CI" → docker build difference explanation
  - "Benchmark accuracy dropped 1%" → normal variation vs regression
  - "Image not pushed to ghcr.io" → authentication issue troubleshooting
  - Links to logs and how to read them
- **Success criteria**:
  - Covers 10+ common issues
  - Each with clear solution
- **Time estimate**: 1.5 hours

### Task 8.4: Create workflow status page / dashboard
- **Description**: Optional: create dashboard showing CI health
- **File**: GitHub Pages or simple HTML with GitHub API
- **Content**:
  - Latest 10 PR validation runs (pass/fail)
  - Latest 10 main builds (pass/fail)
  - Benchmark trend (accuracy, latency over last 30 days)
  - Average build time
- **Success criteria**:
  - Dashboard is accessible
  - Shows CI trends
- **Time estimate**: 2 hours (optional, can skip for MVP)

### Task 8.5: Final handoff and training
- **Description**: Team training on new CI/CD system
- **Content**:
  - Live demo of PR workflow (create → CI runs → merge)
  - Live demo of failure scenarios (fix and re-push)
  - Q&A on workflow design decisions
  - Links to documentation
- **Success criteria**:
  - Team understands CI/CD system
  - Team knows how to debug failures
  - Documentation is the source of truth going forward
- **Time estimate**: 1 hour (meeting)

---

## Summary: Task Count & Effort

| Phase | Tasks | Est. Hours | Parallel? |
|-------|-------|-----------|-----------|
| 2 - Foundation | 10 | 8-12 | Yes (after setup) |
| 3 - PR Validation | 18 | 24-32 | Partial (jobs are parallel) |
| 4 - Main Build | 10 | 12-16 | Yes (after Phase 3) |
| 5 - Benchmarking | 15 | 18-24 | Partial (can start mid-Phase 3) |
| 6 - Polish | 12 | 14-18 | Yes (independent features) |
| 7 - Testing | 8 | 10-14 | Yes (can run in parallel) |
| 8 - Documentation | 5 | 6-8 | Yes (independent) |
| **TOTAL** | **78** | **92-124** | **✓ Highly Parallelizable** |

---

## Recommended Execution Order

**Week 1**:
- Phase 2: Foundation (10 tasks, 8-12 hours)
- Start Phase 3: Implement pr-validation.yml jobs (6-8 tasks)

**Week 2**:
- Complete Phase 3: PR Validation workflow (10+ tasks)
- Phase 4: Main Build workflow (10 tasks)

**Week 3**:
- Phase 5: Benchmark integration (15 tasks)
- Phase 6: Polish (6-8 tasks)

**Week 4**:
- Phase 7: Testing (8 tasks)
- Phase 8: Documentation (5 tasks)

**Team assignments**:
- Person A: Phase 2 Foundation + Phase 3 Workflow
- Person B: Phase 4 Main Build + Phase 5 Benchmarking
- Person C: Phase 6 Polish + Phase 7 Testing
- Team: Phase 8 Documentation + Handoff

---

## Related Documents

- [spec.md](spec.md) - Requirements (6 user stories, 25 FR, 10 SC)
- [plan.md](plan.md) - Implementation phases
- [research.md](research.md) - Technology decisions
- [data-model.md](data-model.md) - CI/CD entities
- [contracts/workflow-pr-validation.yaml](contracts/workflow-pr-validation.yaml) - PR workflow contract
- [contracts/workflow-main-build.yaml](contracts/workflow-main-build.yaml) - Main build workflow contract
- [quickstart.md](quickstart.md) - Developer guide
