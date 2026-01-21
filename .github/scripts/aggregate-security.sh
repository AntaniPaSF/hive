#!/bin/bash
# Security findings aggregator and reporter
# Combines results from multiple security scanning tools

set -e

OUTPUT_FILE="${1:-security-findings.json}"
STRICT_MODE="${2:-false}"  # Fail on any finding if true

echo "📊 Aggregating security findings..."

# Initialize findings array
cat > "${OUTPUT_FILE}" << 'EOF'
{
  "summary": {
    "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "total_findings": 0,
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "findings": []
}
EOF

# Process SAST results
if [ -f bandit-results.json ]; then
    echo "  Processing SAST findings..."
    jq '.results[]? | {type: "SAST", tool: "Bandit", severity: .severity, issue_type: .issue_type, line_number: .line_number}' bandit-results.json 2>/dev/null >> "${OUTPUT_FILE}.tmp" || true
fi

# Process dependency scan results
if [ -f pip-audit-results.json ]; then
    echo "  Processing dependency findings..."
    jq '.vulnerabilities[]? | {type: "Dependency", tool: "pip-audit", severity: .severity, package: .package, version: .version}' pip-audit-results.json 2>/dev/null >> "${OUTPUT_FILE}.tmp" || true
fi

# Process container scan results
if [ -f trivy-results.json ]; then
    echo "  Processing container findings..."
    jq '.Results[]?.Misconfigurations[]? | {type: "Container", tool: "Trivy", severity: .Severity, title: .Title}' trivy-results.json 2>/dev/null >> "${OUTPUT_FILE}.tmp" || true
fi

# Process secret scan results
if [ -f trufflehog-results.json ]; then
    echo "  Processing secret findings..."
    SECRETS=$(jq 'length' trufflehog-results.json 2>/dev/null || echo 0)
    if [ "${SECRETS}" -gt 0 ]; then
        jq '.[] | {type: "Secret", tool: "TruffleHog", severity: "CRITICAL", detector: .DetectorName}' trufflehog-results.json >> "${OUTPUT_FILE}.tmp" || true
    fi
fi

# Count findings by severity
if [ -f "${OUTPUT_FILE}.tmp" ]; then
    CRITICAL=$(grep -c '"severity":"CRITICAL"' "${OUTPUT_FILE}.tmp" 2>/dev/null || echo 0)
    HIGH=$(grep -c '"severity":"HIGH"' "${OUTPUT_FILE}.tmp" 2>/dev/null || echo 0)
    MEDIUM=$(grep -c '"severity":"MEDIUM"' "${OUTPUT_FILE}.tmp" 2>/dev/null || echo 0)
    LOW=$(grep -c '"severity":"LOW"' "${OUTPUT_FILE}.tmp" 2>/dev/null || echo 0)
    
    TOTAL=$((CRITICAL + HIGH + MEDIUM + LOW))
    
    rm "${OUTPUT_FILE}.tmp" 2>/dev/null || true
else
    CRITICAL=0
    HIGH=0
    MEDIUM=0
    LOW=0
    TOTAL=0
fi

# Generate final report
cat > "${OUTPUT_FILE}" << EOF
{
  "summary": {
    "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    "total_findings": ${TOTAL},
    "critical": ${CRITICAL},
    "high": ${HIGH},
    "medium": ${MEDIUM},
    "low": ${LOW}
  },
  "severity_breakdown": {
    "CRITICAL": ${CRITICAL},
    "HIGH": ${HIGH},
    "MEDIUM": ${MEDIUM},
    "LOW": ${LOW}
  }
}
EOF

echo ""
echo "📈 Security Findings Summary:"
echo "   Total Findings: ${TOTAL}"
echo "   CRITICAL: ${CRITICAL}"
echo "   HIGH: ${HIGH}"
echo "   MEDIUM: ${MEDIUM}"
echo "   LOW: ${LOW}"
echo ""

if [ "${CRITICAL}" -gt 0 ]; then
    echo "❌ CRITICAL findings detected: ${CRITICAL}"
    if [ "${STRICT_MODE}" == "true" ]; then
        exit 1
    fi
fi

if [ "${HIGH}" -gt 0 ]; then
    echo "⚠️  HIGH severity findings: ${HIGH}"
fi

echo "✅ Security report generated: ${OUTPUT_FILE}"
