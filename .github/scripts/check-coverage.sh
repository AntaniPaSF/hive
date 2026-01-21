#!/bin/bash
# Script: check-coverage.sh
# Purpose: Verify test coverage meets minimum threshold
# Used by: pr-validation.yml tests job

set -e

COVERAGE_FILE="${1:-coverage.json}"
THRESHOLD="${2:-80}"

if [ ! -f "$COVERAGE_FILE" ]; then
    echo "❌ Coverage file not found: $COVERAGE_FILE"
    exit 1
fi

echo "Checking coverage threshold..."

# Extract coverage percentage
COVERAGE=$(python -c "import json; print(json.load(open('$COVERAGE_FILE'))['totals']['percent_covered'])" 2>/dev/null || echo "0")

echo "Coverage: ${COVERAGE}%"
echo "Threshold: ${THRESHOLD}%"

if (( $(echo "$COVERAGE < $THRESHOLD" | bc -l) )); then
    echo "❌ Coverage below threshold: ${COVERAGE}% < ${THRESHOLD}%"
    exit 1
else
    echo "✅ Coverage meets threshold: ${COVERAGE}% >= ${THRESHOLD}%"
    exit 0
fi
