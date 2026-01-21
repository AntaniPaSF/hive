#!/bin/bash
# Performance analysis and metrics extraction
# Analyzes benchmark results and generates performance report

set -e

RESULTS_FILE="${1}"
OUTPUT_REPORT="${2:-performance-report.md}"

if [[ ! -f "${RESULTS_FILE}" ]]; then
    echo "Usage: analyze-performance.sh <results.json> [output-report.md]"
    exit 1
fi

echo "📈 Analyzing performance metrics..."

# Extract key metrics from results
ACCURACY=$(jq '.accuracy // 0' "${RESULTS_FILE}")
CITATIONS=$(jq '.citations_accuracy // 0' "${RESULTS_FILE}")
P50=$(jq '.latency.p50 // 0' "${RESULTS_FILE}")
P95=$(jq '.latency.p95 // 0' "${RESULTS_FILE}")
P99=$(jq '.latency.p99 // 0' "${RESULTS_FILE}")
MIN=$(jq '.latency.min // 0' "${RESULTS_FILE}")
MAX=$(jq '.latency.max // 0' "${RESULTS_FILE}")

# Generate report
cat > "${OUTPUT_REPORT}" << EOF
# Performance Analysis Report

## Accuracy Metrics

- **Overall Accuracy**: ${ACCURACY}%
- **Citation Accuracy**: ${CITATIONS}%

### Accuracy Gates
$([ $(echo "${ACCURACY} >= 80" | bc) -eq 1 ] && echo "✅ Accuracy gate passed (≥80%)" || echo "❌ Accuracy gate FAILED (<80%)")
$([ $(echo "${CITATIONS} >= 100" | bc) -eq 1 ] && echo "✅ Citation gate passed (100%)" || echo "⚠️  Citation gate WARNING (<100%)")

## Latency Metrics

| Percentile | Latency (ms) | Status |
|-----------|-------------|--------|
| Min | ${MIN} | - |
| P50 | ${P50} | $([ $(echo "${P50} <= 100" | bc) -eq 1 ] && echo "✅ Good" || echo "⚠️  Fair") |
| P95 | ${P95} | $([ $(echo "${P95} <= 500" | bc) -eq 1 ] && echo "✅ Good" || echo "⚠️  Fair") |
| P99 | ${P99} | $([ $(echo "${P99} <= 1000" | bc) -eq 1 ] && echo "✅ Good" || echo "⚠️  Fair") |
| Max | ${MAX} | - |

## Performance Recommendations

EOF

# Add recommendations based on metrics
if (( $(echo "${ACCURACY} < 90" | bc -l) )); then
    echo "- ⚠️  **Accuracy Concern**: Current accuracy is ${ACCURACY}%. Target: ≥95%" >> "${OUTPUT_REPORT}"
fi

if (( $(echo "${P95} > 500" | bc -l) )); then
    echo "- ⚠️  **Latency Concern**: P95 latency is ${P95}ms. Target: <500ms" >> "${OUTPUT_REPORT}"
fi

if (( $(echo "${P99} > 1000" | bc -l) )); then
    echo "- ⚠️  **Tail Latency Concern**: P99 latency is ${P99}ms. Target: <1000ms" >> "${OUTPUT_REPORT}"
fi

if (( $(echo "${ACCURACY} >= 95" | bc -l) )) && (( $(echo "${P95} <= 500" | bc -l) )); then
    echo "- ✅ **Performance is excellent** - No immediate concerns" >> "${OUTPUT_REPORT}"
fi

echo "" >> "${OUTPUT_REPORT}"
echo "---" >> "${OUTPUT_REPORT}"
echo "Generated: $(date -u +'%Y-%m-%d %H:%M:%S UTC')" >> "${OUTPUT_REPORT}"

echo "✅ Performance analysis complete"
echo "Report saved to: ${OUTPUT_REPORT}"
