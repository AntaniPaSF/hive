#!/bin/bash
#
# LLM Benchmark Suite Wrapper Script
# 
# Single-command execution wrapper for the benchmark suite.
# Provides usage instructions and automatic environment setup.
#
# Usage:
#   ./scripts/benchmark.sh [OPTIONS]
#
# Examples:
#   ./scripts/benchmark.sh --api-url http://localhost:8080
#   ./scripts/benchmark.sh --help
#

set -euo pipefail

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default configuration
DEFAULT_API_URL="${BENCHMARK_API_URL:-}"
DEFAULT_TIMEOUT="${BENCHMARK_TIMEOUT:-5.0}"
DEFAULT_THRESHOLD="${BENCHMARK_THRESHOLD:-0.8}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored message
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if Python virtual environment exists
check_venv() {
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        log_warn "Virtual environment not found at $PROJECT_ROOT/.venv"
        log_info "Creating virtual environment..."
        python3 -m venv "$PROJECT_ROOT/.venv"
        log_info "Installing dependencies..."
        "$PROJECT_ROOT/.venv/bin/pip" install -q --upgrade pip
        "$PROJECT_ROOT/.venv/bin/pip" install -q -r "$PROJECT_ROOT/requirements.txt"
        log_info "✓ Virtual environment setup complete"
    fi
}

# Verify dependencies are installed
check_dependencies() {
    local python_cmd="$PROJECT_ROOT/.venv/bin/python"
    
    if ! "$python_cmd" -c "import yaml, Levenshtein, requests, numpy, dotenv" 2>/dev/null; then
        log_warn "Missing dependencies detected"
        log_info "Installing benchmark dependencies..."
        "$PROJECT_ROOT/.venv/bin/pip" install -q -r "$PROJECT_ROOT/requirements.txt"
        log_info "✓ Dependencies installed"
    fi
}

# Display usage information
usage() {
    cat << EOF
LLM Benchmark Suite - Single-command execution wrapper

Usage:
    $0 [OPTIONS]

Options:
    --api-url URL          LLM API endpoint URL (required if BENCHMARK_API_URL not set)
    --timeout SECONDS      Request timeout in seconds (default: $DEFAULT_TIMEOUT)
    --threshold VALUE      Fuzzy matching threshold 0.0-1.0 (default: $DEFAULT_THRESHOLD)
    --ground-truth PATH    Path to ground truth YAML file
    --results-dir PATH     Directory for storing results (default: results/)
    --version              Display benchmark suite version
    --validate-only        Validate ground truth without running benchmark
    --help                 Show this help message

Environment Variables:
    BENCHMARK_API_URL      Default API endpoint URL
    BENCHMARK_TIMEOUT      Default request timeout
    BENCHMARK_THRESHOLD    Default fuzzy matching threshold
    APP_PORT              Port for local API (exported as 8080 if not set)

Examples:
    # Run benchmark against local API
    $0 --api-url http://localhost:8080

    # Use custom timeout and threshold
    $0 --api-url http://localhost:8080 --timeout 10 --threshold 0.85

    # Validate ground truth syntax only
    $0 --validate-only

    # Use environment variables (from .env file)
    export BENCHMARK_API_URL=http://localhost:8080
    $0

EOF
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    # Show help if requested
    if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
        usage
        exit 0
    fi
    
    log_info "LLM Benchmark Suite - Starting..."
    
    # Ensure APP_PORT is set for API compatibility
    export APP_PORT="${APP_PORT:-8080}"
    
    # Setup environment
    check_venv
    check_dependencies
    
    # Execute benchmark with all arguments
    log_info "Running benchmark..."
    "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/tests/benchmark/benchmark.py" "$@"
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_info "✓ Benchmark completed successfully"
    else
        log_error "✗ Benchmark failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Run main function with all arguments
main "$@"
