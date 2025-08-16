#!/bin/bash

# Run All Tests Script for Local Web Memory Backend
# This script runs the complete test suite with proper reporting

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR"

echo -e "${BLUE}🧪 Local Web Memory Backend - Comprehensive Test Suite${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo "Project Directory: $PROJECT_DIR"
echo "Backend Directory: $BACKEND_DIR"
echo ""

# Change to backend directory
cd "$BACKEND_DIR"

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Warning: Not in a virtual environment${NC}"
    echo -e "${YELLOW}   Consider running: uv venv && source .venv/bin/activate${NC}"
    echo ""
fi

# Function to run command with timing and error handling
run_test_command() {
    local command="$1"
    local description="$2"
    local start_time=$(date +%s)
    
    echo -e "${BLUE}▶️  $description${NC}"
    echo "Command: $command"
    echo ""
    
    if eval "$command"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${GREEN}✅ $description completed in ${duration}s${NC}"
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo -e "${RED}❌ $description failed after ${duration}s${NC}"
        return 1
    fi
    echo ""
}

# Function to check dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking Dependencies${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        return 1
    fi
    
    # Check uv
    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}⚠️  uv not found, falling back to pip${NC}"
        USE_UV=false
    else
        USE_UV=true
        echo -e "${GREEN}✅ uv found${NC}"
    fi
    
    # Check pytest
    if ! python3 -c "import pytest" 2>/dev/null; then
        echo -e "${RED}❌ pytest not installed${NC}"
        echo "Installing dependencies..."
        if $USE_UV; then
            uv pip install pytest pytest-cov pytest-asyncio httpx playwright psutil
        else
            pip install pytest pytest-cov pytest-asyncio httpx playwright psutil
        fi
    fi
    
    echo -e "${GREEN}✅ Dependencies check completed${NC}"
    echo ""
}

# Function to setup test environment
setup_test_environment() {
    echo -e "${BLUE}🔧 Setting up test environment${NC}"
    
    # Set test environment variables
    export ARK_API_TOKEN="test-token-for-testing"
    export DATABASE_FILE=":memory:"
    export QUERY_CACHE_FILE="/tmp/test_query_cache.json"
    export LOG_LEVEL="error"
    
    # Clean up any previous test artifacts
    rm -f /tmp/test_query_cache.json
    rm -f test_*.db
    rm -f coverage.xml
    rm -rf .coverage
    rm -rf htmlcov/
    rm -rf .pytest_cache/
    
    echo -e "${GREEN}✅ Test environment setup completed${NC}"
    echo ""
}

# Function to install playwright browsers if needed
setup_playwright() {
    echo -e "${BLUE}🎭 Setting up Playwright${NC}"
    
    if python3 -c "import playwright" 2>/dev/null; then
        # Install playwright browsers
        python3 -m playwright install chromium
        echo -e "${GREEN}✅ Playwright browsers installed${NC}"
    else
        echo -e "${YELLOW}⚠️  Playwright not available, E2E tests may be skipped${NC}"
    fi
    echo ""
}

# Function to run unit tests
run_unit_tests() {
    echo -e "${BLUE}🔬 Running Unit Tests${NC}"
    
    run_test_command \
        "python3 -m pytest tests/ -v -m 'unit or not (e2e or performance or slow)' --tb=short" \
        "Unit Tests"
}

# Function to run integration tests
run_integration_tests() {
    echo -e "${BLUE}🔗 Running Integration Tests${NC}"
    
    run_test_command \
        "python3 -m pytest tests/ -v -m 'integration' --tb=short" \
        "Integration Tests"
}

# Function to run E2E tests
run_e2e_tests() {
    echo -e "${BLUE}🌐 Running End-to-End Tests${NC}"
    
    # Check if playwright is available
    if python3 -c "import playwright" 2>/dev/null; then
        run_test_command \
            "python3 -m pytest tests/ -v -m 'e2e' --tb=short -s" \
            "End-to-End Tests"
    else
        echo -e "${YELLOW}⚠️  Skipping E2E tests - Playwright not available${NC}"
        echo ""
    fi
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}⚡ Running Performance Tests${NC}"
    
    run_test_command \
        "python3 -m pytest tests/ -v -m 'performance' --tb=short -s" \
        "Performance Benchmark Tests"
}

# Function to run tests with coverage
run_coverage_tests() {
    echo -e "${BLUE}📊 Running Tests with Coverage${NC}"
    
    run_test_command \
        "python3 -m pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing --cov-fail-under=70" \
        "Coverage Analysis"
    
    if [ -f "htmlcov/index.html" ]; then
        echo -e "${GREEN}📈 Coverage report generated: htmlcov/index.html${NC}"
    fi
    echo ""
}

# Function to run linting and code quality checks
run_code_quality() {
    echo -e "${BLUE}🔍 Running Code Quality Checks${NC}"
    
    # Check if tools are available
    if command -v flake8 &> /dev/null; then
        run_test_command \
            "flake8 src/ --max-line-length=100 --ignore=E203,W503" \
            "Flake8 Linting"
    else
        echo -e "${YELLOW}⚠️  flake8 not available, skipping linting${NC}"
    fi
    
    if command -v black &> /dev/null; then
        run_test_command \
            "black --check --diff src/" \
            "Black Code Formatting Check"
    else
        echo -e "${YELLOW}⚠️  black not available, skipping format check${NC}"
    fi
    
    if command -v mypy &> /dev/null; then
        run_test_command \
            "mypy src/ --ignore-missing-imports" \
            "MyPy Type Checking"
    else
        echo -e "${YELLOW}⚠️  mypy not available, skipping type checking${NC}"
    fi
    echo ""
}

# Function to generate test report
generate_test_report() {
    echo -e "${BLUE}📋 Generating Test Report${NC}"
    
    local report_file="test_report.txt"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat > "$report_file" << EOF
Local Web Memory Backend - Test Report
=====================================
Generated: $timestamp
Project: Local Web Memory Backend
Environment: $(python3 --version)

Test Categories Executed:
- Unit Tests
- Integration Tests
- End-to-End Tests (if Playwright available)
- Performance Tests
- Code Coverage Analysis

Files:
- Coverage Report: htmlcov/index.html
- Coverage XML: coverage.xml
- Test Report: $report_file

For detailed results, check the console output above.
EOF

    echo -e "${GREEN}✅ Test report generated: $report_file${NC}"
    echo ""
}

# Main execution
main() {
    local start_total_time=$(date +%s)
    
    # Parse command line arguments
    SKIP_PERFORMANCE=false
    SKIP_E2E=false
    COVERAGE_ONLY=false
    QUICK_RUN=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-performance)
                SKIP_PERFORMANCE=true
                shift
                ;;
            --skip-e2e)
                SKIP_E2E=true
                shift
                ;;
            --coverage-only)
                COVERAGE_ONLY=true
                shift
                ;;
            --quick)
                QUICK_RUN=true
                SKIP_PERFORMANCE=true
                SKIP_E2E=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --skip-performance  Skip performance tests"
                echo "  --skip-e2e         Skip end-to-end tests"
                echo "  --coverage-only    Run only coverage tests"
                echo "  --quick            Quick run (skip slow tests)"
                echo "  --help             Show this help"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run test pipeline
    check_dependencies || exit 1
    setup_test_environment || exit 1
    
    if [ "$COVERAGE_ONLY" = true ]; then
        setup_playwright
        run_coverage_tests || exit 1
    elif [ "$QUICK_RUN" = true ]; then
        run_unit_tests || exit 1
        run_integration_tests || exit 1
    else
        setup_playwright
        run_unit_tests || exit 1
        run_integration_tests || exit 1
        
        if [ "$SKIP_E2E" = false ]; then
            run_e2e_tests || exit 1
        fi
        
        if [ "$SKIP_PERFORMANCE" = false ]; then
            run_performance_tests || exit 1
        fi
        
        run_coverage_tests || exit 1
        run_code_quality
    fi
    
    generate_test_report
    
    local end_total_time=$(date +%s)
    local total_duration=$((end_total_time - start_total_time))
    
    echo -e "${GREEN}🎉 All tests completed successfully!${NC}"
    echo -e "${GREEN}⏱️  Total execution time: ${total_duration}s${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Review coverage report: htmlcov/index.html"
    echo "2. Check test_report.txt for summary"
    echo "3. Address any failing tests or low coverage areas"
    echo ""
}

# Handle script interruption
trap 'echo -e "\n${RED}❌ Test execution interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@"