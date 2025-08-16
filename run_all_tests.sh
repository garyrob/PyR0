#!/bin/bash
# Master test runner for PyR0 project
# Exits immediately on first failure (zero tolerance policy)

set -e  # Exit immediately on any error
set -o pipefail  # Pipe failures propagate

# Colors for output
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
    
    echo -e "${YELLOW}Running: $test_name${NC}"
    echo "Command: $test_command"
    echo "---"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ $test_name PASSED${NC}\n"
    else
        echo -e "${RED}✗ $test_name FAILED${NC}"
        echo -e "${RED}ABORTING: Test suite failed at $test_name${NC}"
        exit 1
    fi
}

# Core functionality tests
echo "=== Core Tests ==="
run_test "Real Verification Test" "uv run test_real_verification.py"
run_test "Security Verification Test" "uv run test_security_verification.py"
run_test "Verify API Test" "uv run test_verify_api.py"

# Merkle tree tests
echo -e "\n=== Merkle Tree Tests ==="
run_test "Merkle ZKP Test" "uv run test/test_merkle_zkp.py"

# Demo scripts (these should also validate functionality)
echo -e "\n=== Demo Scripts ==="
run_test "Ed25519 Demo" "uv run demo/ed25519_demo.py"

# Merkle demos require merkle_py which is part of the project
run_test "Merkle Demo" "uv run demo/merkle_demo.py"
run_test "Merkle ZKP Demo" "uv run demo/merkle_zkp_demo.py"

# If we get here, all tests passed
echo ""
echo "=================================="
echo -e "${GREEN}ALL TESTS PASSED!${NC}"
echo "=================================="
exit 0