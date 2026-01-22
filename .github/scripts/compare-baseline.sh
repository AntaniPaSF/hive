#!/bin/bash
# Compare current benchmark against baseline for regression detection
# Usage: compare-baseline.sh <current.json> <baseline.json> [threshold_percent]
# Returns: 0 if no significant regression, 1 if regression detected

set -e

CURRENT="${1}"
BASELINE="${2}"
THRESHOLD="${3:-10}"  # Default 10% regression threshold

if [[ ! -f "${CURRENT}" ]]; then
    echo "❌ Current benchmark file not found: ${CURRENT}"
    exit 1
fi

if [[ ! -f "${BASELINE}" ]]; then
    echo "⚠️  Baseline file not found: ${BASELINE}"
    echo "   This is first build, no regression check"
    exit 0
fi

echo "📊 Comparing benchmark against baseline..."
echo "   Current: ${CURRENT}"
echo "   Baseline: ${BASELINE}"
echo "   Threshold: ${THRESHOLD}%"

# Extract key metrics
CURRENT_ACCURACY=$(jq '.accuracy // 0' "${CURRENT}")
BASELINE_ACCURACY=$(jq '.accuracy // 0' "${BASELINE}")

CURRENT_P95=$(jq '.latency.p95 // 0' "${CURRENT}")
BASELINE_P95=$(jq '.latency.p95 // 0' "${BASELINE}")

CURRENT_P99=$(jq '.latency.p99 // 0' "${CURRENT}")
BASELINE_P99=$(jq '.latency.p99 // 0' "${BASELINE}")

CURRENT_CITATIONS=$(jq '.citations_accuracy // 0' "${CURRENT}")
BASELINE_CITATIONS=$(jq '.citations_accuracy // 0' "${BASELINE}")

# Calculate regressions
ACCURACY_CHANGE=$(echo "scale=2; (${BASELINE_ACCURACY} - ${CURRENT_ACCURACY}) / ${BASELINE_ACCURACY} * 100" | bc)
P95_CHANGE=$(echo "scale=2; (${CURRENT_P95} - ${BASELINE_P95}) / ${BASELINE_P95} * 100" | bc)
P99_CHANGE=$(echo "scale=2; (${CURRENT_P99} - ${BASELINE_P99}) / ${BASELINE_P99} * 100" | bc)
CITATIONS_CHANGE=$(echo "scale=2; (${BASELINE_CITATIONS} - ${CURRENT_CITATIONS}) / ${BASELINE_CITATIONS} * 100" | bc)

# Display results
echo ""
echo "📈 Metric Comparison:"
echo "   Accuracy:        ${CURRENT_ACCURACY}% (baseline: ${BASELINE_ACCURACY}%, change: ${ACCURACY_CHANGE}%)"
echo "   Citations:       ${CURRENT_CITATIONS}% (baseline: ${BASELINE_CITATIONS}%, change: ${CITATIONS_CHANGE}%)"
echo "   Latency P95:     ${CURRENT_P95}ms (baseline: ${BASELINE_P95}ms, change: ${P95_CHANGE}%)"
echo "   Latency P99:     ${CURRENT_P99}ms (baseline: ${BASELINE_P99}ms, change: ${P99_CHANGE}%)"

# Check for regressions
REGRESSION_DETECTED=0

if (( $(echo "${ACCURACY_CHANGE} < -${THRESHOLD}" | bc -l) )); then
    echo ""
    echo "❌ Accuracy regression detected: ${ACCURACY_CHANGE}%"
    REGRESSION_DETECTED=1
fi

if (( $(echo "${CITATIONS_CHANGE} < -${THRESHOLD}" | bc -l) )); then
    echo ""
    echo "❌ Citation accuracy regression detected: ${CITATIONS_CHANGE}%"
    REGRESSION_DETECTED=1
fi

if (( $(echo "${P95_CHANGE} > ${THRESHOLD}" | bc -l) )); then
    echo ""
    echo "⚠️  P95 latency degradation: ${P95_CHANGE}%"
fi

if (( $(echo "${P99_CHANGE} > ${THRESHOLD}" | bc -l) )); then
    echo ""
    echo "⚠️  P99 latency degradation: ${P99_CHANGE}%"
fi

if [ "${REGRESSION_DETECTED}" -eq 1 ]; then
    echo ""
    echo "❌ Regression threshold exceeded (${THRESHOLD}%)"
    exit 1
fi

echo ""
echo "✅ No significant regression detected"
exit 0
