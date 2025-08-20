#!/bin/bash
# Master test runner for PyR0 project
# Exits immediately on first failure (zero tolerance policy)

set -e  # Exit immediately on any error
set -o pipefail  # Pipe failures propagate

# Colors for output (using printf for better compatibility)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "     PyR0 Test Suite Runner"
echo "=================================="
echo "Zero tolerance mode: Will exit on first failure"
echo ""

# Function to run a test - exits immediately on failure
run_test() {
    local test_name=$1
    local test_command=$2
    
    printf "${YELLOW}Running: $test_name${NC}\n"
    echo "Command: $test_command"
    echo "---"
    
    if eval "$test_command"; then
        printf "${GREEN}✓ $test_name PASSED${NC}\n\n"
    else
        printf "${RED}✗ $test_name FAILED${NC}\n"
        printf "${RED}ABORTING: Test suite failed at $test_name${NC}\n"
        exit 1
    fi
}

# Core functionality tests
echo "=== Core Tests ==="
run_test "Import Test" "uv run test/test_import.py"
run_test "Real Verification Test" "uv run test/test_real_verification.py"
run_test "Security Verification Test" "uv run test/test_security_verification.py"
run_test "Verify API Test" "uv run test/test_verify_api.py"

# API tests
printf "\n=== API Tests ===\n"
run_test "Build Guest Test" "uv run test/test_build_guest.py"
run_test "Receipt API Test" "uv run test/test_receipt_api.py"
run_test "API Invariants Test" "uv run test/test_api_invariants.py"

# Serialization tests
printf "\n=== Serialization Tests ===\n"
run_test "InputBuilder Test" "uv run test/test_input_builder.py"
run_test "CBOR Serialization Test" "uv run test/test_cbor_serialization.py"

# Composition tests
printf "\n=== Composition Tests ===\n"
run_test "Composer API Test" "uv run test/test_composer_api.py"
run_test "Proof Composition Test" "uv run test/test_composition.py"

# Demo scripts (these should also validate functionality)
printf "\n=== Demo Scripts ===\n"
run_test "Ed25519 Demo" "uv run demo/ed25519_demo.py"

# If we get here, all tests passed
echo ""
echo "=================================="
printf "${GREEN}ALL TESTS PASSED!${NC}\n"
echo "=================================="
exit 0