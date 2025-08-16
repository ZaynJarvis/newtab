#!/bin/bash

# Local Web Memory Backend - Test Runner Script
set -e

echo "🧪 Running Local Web Memory Backend Tests..."

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Check if uv is available
if ! command -v uv >/dev/null 2>&1; then
    echo "❌ Error: uv not found"
    echo "   Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ Using uv for Python environment management"

# Install dependencies if needed
if [ ! -f "uv.lock" ] || [ "pyproject.toml" -nt "uv.lock" ]; then
    echo "📦 Installing/updating dependencies..."
    uv sync
fi

# Run tests with different options based on arguments
case "${1:-all}" in
    "cache")
        echo "🎯 Running cache tests only..."
        uv run python -m pytest tests/test_query_cache.py -v
        ;;
    "unit")
        echo "🎯 Running unit tests..."
        uv run python -m pytest tests/ -v --tb=short
        ;;
    "coverage")
        echo "🎯 Running tests with coverage..."
        uv run python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing -v
        echo "📊 Coverage report generated in htmlcov/"
        ;;
    "verbose")
        echo "🎯 Running tests in verbose mode..."
        uv run python -m pytest tests/ -v -s
        ;;
    "all"|*)
        echo "🎯 Running all tests..."
        uv run python -m pytest tests/ -v
        ;;
esac

echo "✅ Tests completed!"
echo ""
echo "Usage: $0 [cache|unit|coverage|verbose|all]"
echo "  cache    - Run only cache tests"
echo "  unit     - Run unit tests with short traceback"
echo "  coverage - Run tests with coverage analysis"
echo "  verbose  - Run tests with verbose output"
echo "  all      - Run all tests (default)"