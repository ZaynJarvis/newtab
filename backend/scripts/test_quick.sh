#!/bin/bash

# Quick Test Script for Local Web Memory Backend
# Runs essential tests for rapid development feedback

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}⚡ Quick Test Suite - Local Web Memory Backend${NC}"
echo -e "${BLUE}=============================================${NC}"

# Change to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

# Set test environment variables
export ARK_API_TOKEN="test-token-for-testing"
export DATABASE_FILE=":memory:"
export QUERY_CACHE_FILE="/tmp/test_query_cache.json"
export LOG_LEVEL="error"

# Clean up previous test artifacts
rm -f /tmp/test_query_cache.json
rm -f test_*.db

echo -e "${BLUE}Running quick unit and integration tests...${NC}"
echo ""

# Run quick tests
python3 -m pytest tests/ -v \
    -m 'not (e2e or performance or slow)' \
    --tb=short \
    --maxfail=5 \
    -x

echo ""
echo -e "${GREEN}✅ Quick tests completed successfully!${NC}"
echo -e "${YELLOW}💡 For comprehensive testing, run: ./scripts/run_all_tests.sh${NC}"