#!/bin/bash
# Stress testing script for performance benchmarking
# Runs concurrent requests and measures performance degradation

set -e

API_URL="${1:-http://localhost:8000}"
CONCURRENCY="${2:-10}"
DURATION="${3:-300}"  # 5 minutes default
OUTPUT_JSON="${4:-stress-results.json}"

if [[ -z "${API_URL}" ]]; then
    echo "Usage: stress-test.sh <api-url> [concurrency] [duration-seconds] [output-json]"
    exit 1
fi

echo "🔫 Stress Testing: ${API_URL}"
echo "   Concurrency: ${CONCURRENCY}"
echo "   Duration: ${DURATION}s"
echo ""

# Initialize metrics
TOTAL_REQUESTS=0
SUCCESSFUL_REQUESTS=0
FAILED_REQUESTS=0
TOTAL_LATENCY=0
MAX_LATENCY=0
MIN_LATENCY=999999

# Function to make a single request and record metrics
make_request() {
    local start=$(date +%s%N)
    
    if curl -sf "${API_URL}/health" > /dev/null 2>&1; then
        ((SUCCESSFUL_REQUESTS++))
        local end=$(date +%s%N)
        local latency=$(( (end - start) / 1000000 ))  # Convert to ms
        
        TOTAL_LATENCY=$((TOTAL_LATENCY + latency))
        if (( latency > MAX_LATENCY )); then
            MAX_LATENCY=${latency}
        fi
        if (( latency < MIN_LATENCY )); then
            MIN_LATENCY=${latency}
        fi
    else
        ((FAILED_REQUESTS++))
    fi
    ((TOTAL_REQUESTS++))
}

# Run stress test
START_TIME=$(date +%s)
while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ ${ELAPSED} -ge ${DURATION} ]; then
        break
    fi
    
    # Spawn concurrent requests
    for ((i=0; i<${CONCURRENCY}; i++)); do
        make_request &
    done
    
    wait
done

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

# Calculate averages
AVG_LATENCY=$((TOTAL_LATENCY / SUCCESSFUL_REQUESTS))
SUCCESS_RATE=$((SUCCESSFUL_REQUESTS * 100 / TOTAL_REQUESTS))

# Generate results
cat > "${OUTPUT_JSON}" << EOF
{
  "stress_test": {
    "api_url": "${API_URL}",
    "concurrency": ${CONCURRENCY},
    "duration_seconds": ${DURATION},
    "actual_duration_seconds": ${TOTAL_TIME},
    "total_requests": ${TOTAL_REQUESTS},
    "successful": ${SUCCESSFUL_REQUESTS},
    "failed": ${FAILED_REQUESTS},
    "success_rate_percent": ${SUCCESS_RATE},
    "latency_ms": {
      "min": ${MIN_LATENCY},
      "max": ${MAX_LATENCY},
      "avg": ${AVG_LATENCY}
    }
  }
}
EOF

echo ""
echo "📊 Stress Test Results:"
echo "   Total Requests: ${TOTAL_REQUESTS}"
echo "   Successful: ${SUCCESSFUL_REQUESTS}"
echo "   Failed: ${FAILED_REQUESTS}"
echo "   Success Rate: ${SUCCESS_RATE}%"
echo "   Latency:"
echo "     Min: ${MIN_LATENCY}ms"
echo "     Max: ${MAX_LATENCY}ms"
echo "     Avg: ${AVG_LATENCY}ms"
echo ""
echo "Results saved to: ${OUTPUT_JSON}"

# Exit with error if too many failures
if [ ${SUCCESS_RATE} -lt 95 ]; then
    echo "❌ Success rate below 95%"
    exit 1
fi

echo "✅ Stress test completed successfully"
exit 0
