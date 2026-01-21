# Quickstart: LLM Benchmark Suite

**Goal**: Run the LLM benchmark suite against your local chatbot API in under 10 minutes

**Prerequisites**:
- Python 3.11+ installed
- LLM API running locally (e.g., `http://localhost:8080`)
- Git repository cloned

---

## 0. Single-Command Execution (Fastest - 3 minutes) ✨

**NEW**: Use the wrapper script for automatic setup:

```bash
cd /path/to/hive
./scripts/benchmark.sh --api-url http://localhost:8080
```

**What this does**:
- ✓ Auto-creates virtual environment if missing
- ✓ Auto-installs dependencies
- ✓ Runs benchmark with your API
- ✓ Generates results in CLI + JSON

Skip to Step 4 for results! Or continue below for manual setup.

---

## 1. Install Dependencies (2 minutes)

```bash
cd /path/to/hive
pip install -r requirements.txt
```

**Dependencies Installed**:
- PyYAML (YAML parsing)
- python-Levenshtein (fuzzy matching)
- requests (HTTP client)
- numpy (percentile calculations)
- python-dotenv (environment config)
- pytest (for unit tests)

---

## 2. Configure API Endpoint (1 minute)

### Option A: Environment Variable

```bash
export BENCHMARK_API_URL=http://localhost:8080
```

### Option B: CLI Argument (skip export)

```bash
# Will use --api-url flag when running benchmark
```

### Option C: .env File

```bash
cat > .env << EOF
BENCHMARK_API_URL=http://localhost:8080
BENCHMARK_TIMEOUT=5
BENCHMARK_THRESHOLD=0.8
EOF
```

---

## 3. Verify API is Running (1 minute)

```bash
curl http://localhost:8080/health
# Expected: {"status": "ok"}
```

If API is not running, start it first:

```bash
make start  # From project root
# Wait for "Server started on port 8080" message
```

---

## 4. Run Benchmark Suite (3-5 minutes)

### Quick Run (Uses Defaults)

```bash
python tests/benchmark/benchmark.py
```

### Custom Configuration

```bash
python tests/benchmark/benchmark.py \
  --api-url http://localhost:8080 \
  --timeout 5 \
  --threshold 0.8 \
  --ground-truth tests/benchmark/ground_truth.yaml \
  --results-dir results
```

**Output** (Example):
```
=== LLM Benchmark Suite ===
Loading ground truth from: tests/benchmark/ground_truth.yaml
Loaded 20 questions

Testing against: http://localhost:8080
Configuration: timeout=5s, fuzzy_threshold=0.8

[1/20] Q001: How do I request vacation time? ... PASS (2.3s, score=0.87)
[2/20] Q002: What is the meal allowance limit? ... PASS (1.9s, score=0.92)
[3/20] Q003: How do I submit an expense report? ... FAIL (2.1s, score=0.65)
...
[20/20] Q020: What is the remote work policy? ... PASS (2.5s, score=0.89)

=== Results ===
Accuracy: 85.0% (17/20 passed)
Citation Coverage: 100.0% (20/20 responses)

Performance:
  p50: 2340 ms
  p95: 4580 ms
  p99: 5120 ms
  Mean: 2650 ms

Failed Questions:
  Q003: Expected "Submit expense report via finance portal within 30 days"
        Got: "Use the portal to submit expenses"
        Similarity: 0.65 (threshold: 0.8)

Report saved to: results/benchmark_2026-01-21_14-30-15.json
```

---

## 5. Review Results (2 minutes)

### CLI Output

Human-readable summary printed to terminal (see above)

### JSON Report

```bash
cat results/benchmark_2026-01-21_14-30-15.json | jq .summary
```

**Output**:
```json
{
  "total_questions": 20,
  "passed_questions": 17,
  "accuracy_percentage": 85.0,
  "citation_coverage_percentage": 100.0
}
```

### Full Results

```bash
cat results/benchmark_2026-01-21_14-30-15.json | jq '.results[] | select(.accuracy_status == "FAIL")'
```

---

## 6. Interpret Results

### Success Criteria (from spec.md)

- ✅ **SC-002**: Accuracy ≥ 80% → **85% PASS**
- ✅ **SC-006**: Citation coverage = 100% → **100% PASS**
- ✅ **Performance**: p95 < 10s → **4.58s PASS**

### What if Tests Fail?

**Low Accuracy (<80%)**:
1. Review failed questions in results JSON
2. Check if expected answers are too strict (consider adding variations)
3. Adjust fuzzy threshold: `--threshold 0.75` (more lenient)
4. Verify LLM has correct knowledge base loaded

**Missing Citations**:
1. Check API response format (should include `citations` array)
2. Verify citation enforcement is enabled in backend
3. Review API contract: `specs/001-llm-benchmark-suite/contracts/api_contract.md`

**Slow Performance (p95 > 10s)**:
1. Profile backend bottlenecks (embeddings, vector search, LLM inference)
2. Check hardware resources (CPU usage, memory)
3. Consider reducing knowledge base size for testing

---

## 7. Adding New Test Questions (5 minutes)

Edit `tests/benchmark/ground_truth.yaml`:

```yaml
questions:
  # ... existing questions ...
  
  - id: "Q021"  # Use next sequential ID
    category: "benefits"
    question: "What is the health insurance coverage?"
    expected_answer: "Full medical, dental, and vision coverage with company premium contribution."
    variations:
      - "Medical, dental, vision coverage with employer contribution."
    citation_required: true
    tags: ["benefits", "insurance", "health"]
```

Re-run benchmark:

```bash
python tests/benchmark/benchmark.py
# Now tests 21 questions
```

---

## 8. Continuous Integration (Optional)

Add to CI pipeline (GitHub Actions example):

```yaml
# .github/workflows/benchmark.yml
name: LLM Benchmark

on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Start API
        run: make start &
        
      - name: Wait for API
        run: sleep 10
      
      - name: Run benchmark
        run: python tests/benchmark/benchmark.py --api-url http://localhost:8080
      
      - name: Check accuracy threshold
        run: |
          python -c "
          import json
          with open('results/benchmark_*.json') as f:
              report = json.load(f)
          if report['summary']['accuracy_percentage'] < 80:
              print('FAIL: Accuracy below 80%')
              exit(1)
          "
```

---

## Troubleshooting

### "Connection refused" Error

**Problem**: API endpoint not reachable

**Solution**:
```bash
# Check if API is running
curl http://localhost:8080/health

# Start API if needed
make start

# Verify port in config
echo $BENCHMARK_API_URL
```

### "Timeout after 5s" Errors

**Problem**: API responses too slow

**Solution**:
```bash
# Increase timeout
python tests/benchmark/benchmark.py --timeout 10

# Or set env var
export BENCHMARK_TIMEOUT=10
```

### "Invalid YAML" Error

**Problem**: Malformed ground_truth.yaml

**Solution**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('tests/benchmark/ground_truth.yaml'))"

# Check for missing required fields (id, question, expected_answer, category)
```

### Low Accuracy Scores

**Problem**: Fuzzy matching too strict

**Solution**:
```bash
# Lower threshold
python tests/benchmark/benchmark.py --threshold 0.7

# Or add answer variations to ground_truth.yaml
```

---

## Command Reference

```bash
# Basic run
python tests/benchmark/benchmark.py

# Custom API URL
python tests/benchmark/benchmark.py --api-url http://localhost:9000

# Custom timeout
python tests/benchmark/benchmark.py --timeout 10

# Custom fuzzy threshold
python tests/benchmark/benchmark.py --threshold 0.75

# Custom ground truth file
python tests/benchmark/benchmark.py --ground-truth custom_questions.yaml

# Custom results directory
python tests/benchmark/benchmark.py --results-dir my_results

# Run unit tests
pytest tests/unit/test_validators.py -v

# Run with verbose logging
python tests/benchmark/benchmark.py --verbose
```

---

## Next Steps

- **Extend Ground Truth**: Add more questions covering edge cases
- **Tune Thresholds**: Adjust fuzzy matching based on your domain
- **Citation Validation**: Implement P2 story (validate against knowledge base manifest)
- **Regression Detection**: Implement P3 story (compare against baseline results)
- **Automation**: Add to CI/CD pipeline

**Support**: See `specs/001-llm-benchmark-suite/spec.md` for full feature specification
