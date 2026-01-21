#!/bin/bash
# Ollama Model Download Script
# Downloads and configures Mistral 7B model for RAG LLM Service
#
# Usage:
#   ./scripts/download-ollama-model.sh [MODEL_NAME]
#
# Default model: mistral:7b
# Alternative models: llama2:7b, phi:latest, gemma:7b

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_MODEL="mistral:7b"
MODEL_NAME="${1:-$DEFAULT_MODEL}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
MAX_RETRIES=5
RETRY_DELAY=10

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Ollama is installed
check_ollama_installed() {
    if ! command -v ollama &> /dev/null; then
        log_error "Ollama is not installed."
        echo "Please install Ollama from: https://ollama.ai/download"
        exit 1
    fi
    log_info "Ollama CLI found: $(which ollama)"
}

# Wait for Ollama service to be ready
wait_for_ollama() {
    log_info "Waiting for Ollama service at $OLLAMA_HOST..."
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
            log_info "Ollama service is ready!"
            return 0
        fi
        
        log_warn "Attempt $i/$MAX_RETRIES: Ollama not ready yet. Retrying in ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    done
    
    log_error "Ollama service did not become ready after $MAX_RETRIES attempts."
    log_error "Please ensure Ollama is running: docker-compose up ollama -d"
    exit 1
}

# Check if model is already downloaded
check_model_exists() {
    log_info "Checking if model '$MODEL_NAME' already exists..."
    
    if ollama list 2>/dev/null | grep -q "^${MODEL_NAME}"; then
        log_info "Model '$MODEL_NAME' is already downloaded."
        return 0
    else
        log_info "Model '$MODEL_NAME' not found. Downloading..."
        return 1
    fi
}

# Download the model
download_model() {
    log_info "Downloading model: $MODEL_NAME"
    log_info "This may take several minutes (model size: ~4-8 GB)..."
    
    if ollama pull "$MODEL_NAME"; then
        log_info "Successfully downloaded model: $MODEL_NAME"
        return 0
    else
        log_error "Failed to download model: $MODEL_NAME"
        return 1
    fi
}

# Verify model works
verify_model() {
    log_info "Verifying model: $MODEL_NAME"
    
    # Test with a simple prompt
    TEST_PROMPT="Hello, this is a test. Respond with just 'OK'."
    
    if echo "$TEST_PROMPT" | ollama run "$MODEL_NAME" > /dev/null 2>&1; then
        log_info "Model verification successful!"
        return 0
    else
        log_error "Model verification failed."
        return 1
    fi
}

# Display model info
show_model_info() {
    log_info "Model information:"
    echo ""
    ollama show "$MODEL_NAME" 2>/dev/null || true
    echo ""
    log_info "Available models:"
    ollama list
}

# Main execution
main() {
    echo "========================================"
    echo "  Ollama Model Download Script"
    echo "========================================"
    echo ""
    
    # Step 1: Check Ollama installation
    check_ollama_installed
    
    # Step 2: Wait for Ollama service
    wait_for_ollama
    
    # Step 3: Check if model exists
    if check_model_exists; then
        log_info "Skipping download - model already exists."
    else
        # Step 4: Download model
        if ! download_model; then
            exit 1
        fi
    fi
    
    # Step 5: Verify model
    if ! verify_model; then
        log_warn "Model verification failed, but download completed."
        log_warn "You may need to troubleshoot the model."
    fi
    
    # Step 6: Show model info
    show_model_info
    
    echo ""
    log_info "Setup complete! Model '$MODEL_NAME' is ready for use."
    echo ""
    echo "Next steps:"
    echo "  1. Start the RAG service: docker-compose up rag-service -d"
    echo "  2. Test the service: curl http://localhost:8000/health"
    echo "  3. Run a query: curl -X POST http://localhost:8000/query -H 'Content-Type: application/json' -d '{\"question\":\"What is the vacation policy?\"}'"
    echo ""
}

# Run main function
main "$@"
