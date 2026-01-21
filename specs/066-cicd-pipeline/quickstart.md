# CI/CD Quick Start Guide

**Target Audience**: Developers setting up and running the CI/CD pipeline

---

## 5-Minute Overview

The CI/CD pipeline runs automatically on every PR and push to main. It validates your code through:

1. **Tests** (~2 min) - Unit tests + coverage gate (80% required)
2. **Lint** (~1 min) - Format, linting, type checking, security scans
3. **Build** (~1.5 min) - Docker image creation + vulnerability scan
4. **Benchmark** (~3 min) - LLM accuracy + citation validation

Total runtime: **~5-7 minutes** per PR (with caching). You get an automatic comment on your PR with results.

---

## Local Development (Before Pushing)

Run the same validation locally to avoid CI failures:

### Install Dev Dependencies

```bash
# Python 3.11+ required
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov black ruff mypy bandit pip-audit
```

### Run Local Validation

**Option 1: Individual Checks**

```bash
# Format check (will error if files need formatting)
black --check src/ tests/

# Auto-fix formatting
black src/ tests/

# Linting (ruff)
ruff check src/ tests/

# Type checking (mypy)
mypy src/

# Security (bandit)
bandit -r src/

# Dependency audit (pip-audit)
pip-audit

# Tests + coverage
pytest tests/ --cov=src/ --cov-report=term --cov-report=html
# View coverage: open htmlcov/index.html
```

**Option 2: Run All at Once**

```bash
# If a Makefile exists with targets (see below), use:
make verify
```

### Makefile Targets (Recommended)

Create a `Makefile` in repo root with these targets:

```makefile
.PHONY: test lint format build benchmark verify clean

# Run all validation checks (CI equivalent)
verify: format lint test build

# Format code
format:
	black src/ tests/

# Lint without fixing
lint:
	black --check src/ tests/
	ruff check src/ tests/
	mypy src/
	bandit -r src/
	pip-audit

# Run tests with coverage
test:
	pytest tests/ \
	  --cov=src/ \
	  --cov-report=term \
	  --cov-report=html:htmlcov \
	  --junit-xml=test-results.xml

# Build Docker image locally
build:
	docker build -t hive-core:local .

# Run benchmark suite (requires API running)
benchmark:
	python -m tests.benchmark.benchmark \
	  --api-url http://localhost:8000 \
	  --suite full

# Spin up API for local testing
run-api:
	docker run -d --name hive-api -p 8000:8000 hive-core:local
	sleep 5
	curl http://localhost:8000/health

# Stop API container
stop-api:
	docker stop hive-api && docker rm hive-api

# Clean up generated files
clean:
	rm -rf htmlcov/ .coverage test-results.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
```

**Usage**:

```bash
# Format + lint + test locally before pushing
make verify

# If tests fail, debug locally before push
make test          # re-run tests
make clean test    # fresh run

# Check coverage
make test
open htmlcov/index.html

# For benchmark changes
make build run-api benchmark stop-api
```

---

## PR Submission Workflow

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature
```

### 2. Make Changes

```bash
# Edit code, write tests, etc.
```

### 3. Run Local Validation

```bash
make verify  # or run individual checks above
```

### 4. Commit and Push

```bash
git add .
git commit -m "feat: add feature description"
git push origin feature/my-feature
```

### 5. GitHub Actions Runs Automatically

- PR page shows CI status checks
- Tests, lint, build, benchmark run in parallel
- Results appear in PR comments within 5-7 minutes

### 6. Review Comments

Check the PR comments for results:

```
✅ All Checks Passed
- Tests: 145/145, 82.5% coverage
- Quality: All gates passed
- Image: pushed to ghcr.io
- Benchmarks: 86% accuracy, 100% citations
```

Or if there are failures:

```
❌ Tests Failed
Failed: 3
Error: Expected 80% coverage, got 75%

❌ Benchmarks Failed
Accuracy: 76% (need >= 80%)
Citations: 95% (need 100%)
```

### 7. Fix Issues and Re-push

If tests/benchmarks failed:

```bash
# Fix code locally
make test  # verify fix locally

# Re-push (creates new build automatically)
git add .
git commit -m "fix: improve accuracy to 81%"
git push origin feature/my-feature
```

### 8. Merge After All Checks Pass

Once all status checks are green ✅:
- Click "Merge pull request"
- CI runs once more on main branch
- Image is tagged `main-{sha}` and `latest`
- Released to ghcr.io

---

## Understanding CI Failures

### ❌ Tests Failed

```
Tests: 145 passed, 3 failed, coverage 75%
Error: Coverage below 80% threshold
```

**Fix**:
```bash
# See which files lack coverage
make clean test
open htmlcov/index.html  # Find untested lines

# Add tests for uncovered lines
# Then re-run and re-push
```

### ❌ Lint Failed

```
formatting.compliant: false
Files needing format: src/main.py, src/parser.py
```

**Fix**:
```bash
make format
git add .
git commit -m "style: apply black formatting"
git push origin feature/my-feature
```

### ❌ Type Checking Failed

```
mypy errors: 2
src/parser.py:45: Argument 1 has incompatible type "str"; expected "int"
```

**Fix**:
```bash
# Review the type error
# Add type hints or fix logic
mypy src/  # verify locally
make verify
git add . && git commit -m "fix: type annotations" && git push
```

### ❌ Security Scan Failed

```
bandit: HIGH severity issue in src/utils.py:12
Issue: Using pickle can allow arbitrary code execution
```

**Fix**:
- Review the bandit report
- Use safer alternatives (json instead of pickle)
- Update code and re-push

### ❌ Benchmark Failed

```
Accuracy: 76% (need >= 80%)
Citations: 95% (need 100%)
```

**Fix**:
```bash
# Accuracy failures = LLM accuracy issues
# Run full benchmark locally to debug

make build run-api
python -m tests.benchmark.benchmark \
  --api-url http://localhost:8000 \
  --suite full \
  --output-json results.json

# Analyze failed questions in results.json
# Improve prompt/model logic, re-test, re-push

make stop-api
```

---

## Environment Variables

### For Local Development

Create `.env.local` (not committed):

```bash
# API Configuration
ENV=test
API_HOST=localhost
API_PORT=8000

# Benchmark settings
BENCHMARK_TIMEOUT_SECONDS=300
BENCHMARK_VERBOSE=true
```

Load in your shell:

```bash
set -a
source .env.local
set +a
python -m tests.benchmark.benchmark ...
```

### GitHub Secrets (CI Only)

These are configured in GitHub repo settings → Secrets:

```
GITHUB_TOKEN      # Auto-provided by GitHub Actions
SLACK_WEBHOOK     # For CI notifications (optional)
```

Developers don't need to set these.

---

## Debugging CI Issues

### I pushed and CI ran, but I don't see results

1. Go to PR page
2. Scroll down to "Checks" section
3. Click "Details" on failed check
4. View full logs (green ✓ passed, red ✗ failed)

### My local tests pass but CI fails

This usually means caching or environment differences:

```bash
# Option 1: Test with Docker (CI uses ubuntu-latest)
docker run --rm -v $PWD:/app -w /app python:3.11 bash -c "
  pip install -r requirements.txt
  make verify
"

# Option 2: Re-run exact CI steps locally
python3.11 -m venv venv-ci
source venv-ci/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
make verify
```

### Image build fails in CI but works locally

Docker BuildKit caching might be stale:

```bash
# Disable cache for clean build
docker build --no-cache -t hive-core:local .

# Test again
make run-api benchmark
```

---

## Performance Tips

### Speed Up CI

1. **Avoid unnecessary pushes**
   - Run `make verify` locally first
   - Only push when all checks pass

2. **Leverage caching**
   - Don't update requirements.txt unless needed
   - CI reuses pip cache (95% hit rate typical)

3. **Use draft PRs for early feedback**
   - Submit draft PR early
   - CI runs but doesn't block merge
   - Get feedback while making changes

### Speed Up Local Development

1. **Use existing venv**
   - Don't recreate venv each time
   - `make test` reuses venv

2. **Skip expensive checks**
   - Just edit files: `make format lint test`
   - Skip build/benchmark until ready

3. **Cache Docker layers**
   - First build: 90 seconds
   - Subsequent: 15 seconds (cached)

---

## Common Questions

**Q: What's the difference between PR validation and main build?**

A: PR validation runs all checks before merge. Main build skips some checks (tests already passed) and focuses on tagging/releasing the image. The main-branch image gets `latest` tag.

**Q: Can I skip CI for small changes?**

A: Add `[skip ci]` to commit message to skip CI. Use sparingly:

```bash
git commit -m "docs: update README [skip ci]"
git push  # CI won't run
```

**Q: How do I run just benchmarks locally?**

A:
```bash
# Make sure API is running
make build run-api

# Run benchmarks only
make benchmark

# Clean up
make stop-api
```

**Q: What if I need to update Python version?**

A: Update:
1. `requirements.txt` - add new package needs
2. `Dockerfile` - change `FROM python:3.11` to newer version
3. `.github/workflows/pr-validation.yml` - change `python-version: 3.11` to new version
4. CI will pick up changes automatically

**Q: Benchmark accuracy is 79%, just 1% below threshold. Can I merge anyway?**

A: No. The 80% gate is hard requirement (enforces quality). Fix the accuracy issues:
- Improve prompts
- Enhance retrieval
- Add missing training data
- Re-test and re-push

---

## Next Steps

1. **Set up local environment**: Follow "Local Development" section above
2. **Create feature branch**: `git checkout -b feature/my-feature`
3. **Make changes and test**: `make verify`
4. **Push and let CI run**: `git push origin feature/my-feature`
5. **Review CI comments** and fix any failures
6. **Merge when green**: Click merge button

---

## Support

- **CI Logs**: PR page → "Checks" tab → Click failed check → View logs
- **Common Issues**: See "Debugging CI Issues" section above
- **Ask Team**: Tag #devops or post in #engineering channel

---

## Related Documentation

- [data-model.md](data-model.md) - Pipeline data structures
- [plan.md](plan.md) - Implementation phases and timeline
- [research.md](research.md) - Technology decisions and rationale
