#!/bin/bash
# Script: check-benchmark.sh
# Purpose: Parse benchmark results and verify gates
# Used by: pr-validation.yml benchmark job

set -e

BENCHMARK_FILE="${1:-benchmark-results.json}"

if [ ! -f "$BENCHMARK_FILE" ]; then
    echo "❌ Benchmark file not found: $BENCHMARK_FILE"
    exit 1
fi

echo "Checking benchmark gates..."

# Extract metrics
ACCURACY=$(jq '.accuracy' "$BENCHMARK_FILE" 2>/dev/null || echo "0")
CITATIONS=$(jq '.citations_accuracy' "$BENCHMARK_FILE" 2>/dev/null || echo "0")
P95=$(jq '.latency.p95' "$BENCHMARK_FILE" 2>/dev/null || echo "9999")

echo "Accuracy: ${ACCURACY}%"
echo "Citations: ${CITATIONS}%"
echo "P95 Latency: ${P95}ms"

# Check hard gates
FAILED=0

if (( $(echo "$ACCURACY < 80" | bc -l) )); then
    echo "❌ GATE FAILED: Accuracy ${ACCURACY}% < 80%"
    FAILED=1
else
    echo "✅ Accuracy gate passed (${ACCURACY}% >= 80%)"
fi

if (( $(echo "$CITATIONS < 100" | bc -l) )); then
    echo "❌ GATE FAILED: Citations ${CITATIONS}% < 100%"
    FAILED=1
else
    echo "✅ Citations gate passed (${CITATIONS}% = 100%)"
fi

# Check soft gates (warnings only)
if (( $(echo "$P95 > 1000" | bc -l) )); then
    echo "⚠️  WARNING: P95 latency ${P95}ms > 1000ms (informational only)"
else
    echo "✅ P95 latency gate passed (${P95}ms < 1000ms)"
fi

exit $FAILED
