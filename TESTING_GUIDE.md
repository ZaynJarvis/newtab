# Testing Guide for New Tab Backend

This guide provides comprehensive instructions for running and understanding the test suite for the New Tab Backend project.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Categories](#test-categories)
- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Test Configuration](#test-configuration)
- [Writing Tests](#writing-tests)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

## 🔍 Overview

The New Tab Backend includes a comprehensive test suite covering:

- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **End-to-End Tests**: Full workflow testing with Playwright
- **Performance Tests**: Benchmarking and load testing
- **Docker Tests**: Container and deployment testing

### Test Technology Stack

- **pytest**: Primary testing framework
- **httpx**: Async HTTP client for API testing
- **Playwright**: Browser automation for E2E testing
- **pytest-cov**: Code coverage reporting
- **pytest-asyncio**: Async test support
- **psutil**: System monitoring for performance tests

## 📂 Test Categories

### Unit Tests (`unit`)

Test individual functions and classes in isolation:

- Database operations
- Vector store functionality
- API client methods
- Utility functions
- Configuration validation

**Location**: Throughout `tests/` directory
**Markers**: `@pytest.mark.unit` or unmarked

### Integration Tests (`integration`)

Test API endpoints and component interactions:

- HTTP endpoint testing
- Database integration
- External API integration
- CORS functionality
- Error handling

**Location**: `tests/test_integration_api.py`
**Markers**: `@pytest.mark.integration`

### End-to-End Tests (`e2e`)

Test complete workflows using browser automation:

- Full API workflows
- Multi-step operations
- Real browser interactions
- Chrome extension compatibility

**Location**: `tests/test_e2e_playwright.py`
**Markers**: `@pytest.mark.e2e`

### Performance Tests (`performance`)

Benchmark and stress test the system:

- Response time testing
- Concurrent request handling
- Memory usage monitoring
- Throughput measurement
- Scalability testing

**Location**: `tests/test_performance.py`
**Markers**: `@pytest.mark.performance`

### Slow Tests (`slow`)

Long-running tests for comprehensive coverage:

- Large dataset testing
- Extended duration tests
- Memory leak detection
- Stress testing

**Markers**: `@pytest.mark.slow`

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure you're in the backend directory
cd backend

# Install dependencies using uv
uv sync

# Or using pip
pip install -r requirements.txt
```

### Run All Tests

```bash
# Quick test run (excludes slow tests)
./scripts/test_quick.sh

# Comprehensive test suite
./scripts/run_all_tests.sh

# Docker-based testing
./scripts/test_docker_setup.sh
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/ -m "unit or not (e2e or performance or slow)"

# Integration tests
pytest tests/ -m "integration"

# E2E tests
pytest tests/ -m "e2e"

# Performance tests
pytest tests/ -m "performance"
```

## 🧪 Running Tests

### Command Line Options

#### Basic Test Execution

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_integration_api.py

# Run specific test function
pytest tests/test_integration_api.py::TestHealthAPI::test_health_endpoint_success
```

#### Using Markers

```bash
# Run only unit tests
pytest tests/ -m "unit"

# Run everything except slow tests
pytest tests/ -m "not slow"

# Run integration and unit tests
pytest tests/ -m "integration or unit"

# Run performance tests only
pytest tests/ -m "performance"
```

#### Advanced Options

```bash
# Stop on first failure
pytest tests/ -x

# Run failed tests from last run
pytest tests/ --lf

# Run in parallel (install pytest-xdist)
pytest tests/ -n auto

# Generate JUnit XML report
pytest tests/ --junit-xml=test-results.xml

# Show local variables in tracebacks
pytest tests/ -l
```

### Environment Configuration

Set environment variables for testing:

```bash
# Required for tests
export ARK_API_TOKEN="test-token-for-testing"
export DATABASE_FILE=":memory:"
export QUERY_CACHE_FILE="/tmp/test_query_cache.json"
export LOG_LEVEL="error"

# Run tests
pytest tests/
```

### Docker Testing

```bash
# Build and run tests in Docker
docker build -t newtab-test ./backend
docker run --rm newtab-test ./start.sh test

# Using docker-compose
docker-compose -f docker-compose.dev.yml --profile testing up test-runner
```

## ⚙️ Test Configuration

### pytest.ini Configuration

The project includes a `pytest.ini` file with default settings:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance benchmark tests
    slow: Slow running tests

addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --color=yes
    --durations=10
```

### Test Fixtures

Key fixtures available in `conftest.py`:

- **`client`**: FastAPI test client
- **`async_client`**: Async HTTP client
- **`test_db`**: In-memory database instance
- **`mock_ark_client`**: Mocked API client
- **`sample_page_data`**: Test page data
- **`sample_pages_data`**: Multiple test pages

### Coverage Configuration

Coverage settings in `pytest.ini`:

```ini
[coverage:run]
source = src
omit = 
    */tests/*
    */venv/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError

show_missing = true
precision = 2
```

## ✍️ Writing Tests

### Unit Test Example

```python
import pytest
from src.core.database import Database

@pytest.mark.unit
def test_database_initialization():
    """Test database initialization."""
    db = Database(":memory:")
    assert db is not None
    assert db.connection is not None

@pytest.mark.unit
def test_page_insertion(test_db, sample_page_data):
    """Test page insertion."""
    page_id = test_db.insert_page(
        url=sample_page_data["url"],
        title=sample_page_data["title"],
        content=sample_page_data["content"]
    )
    assert isinstance(page_id, int)
    assert page_id > 0
```

### Integration Test Example

```python
import pytest

@pytest.mark.integration
def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]

@pytest.mark.integration
async def test_async_search(async_client):
    """Test async search endpoint."""
    response = await async_client.get("/search?query=test")
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
```

### E2E Test Example

```python
import pytest

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_page_indexing_workflow(test_server):
    """Test complete page indexing workflow."""
    async with httpx.AsyncClient() as client:
        # Index a page
        page_data = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "content": "Test content"
        }
        
        response = await client.post(
            f"{test_server.base_url}/index",
            json=page_data
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            
            # Search for the page
            search_response = await client.get(
                f"{test_server.base_url}/search?query=test"
            )
            assert search_response.status_code == 200
```

### Performance Test Example

```python
import pytest
import time
import statistics

@pytest.mark.performance
def test_search_performance(client):
    """Test search endpoint performance."""
    times = []
    
    for _ in range(10):
        start = time.perf_counter()
        response = client.get("/search?query=test")
        end = time.perf_counter()
        
        assert response.status_code == 200
        times.append(end - start)
    
    avg_time = statistics.mean(times)
    assert avg_time < 1.0, f"Average response time {avg_time:.3f}s exceeds 1s"
```

### Test Utilities

Common testing utilities:

```python
# Timing helper
class PerformanceTimer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.duration = time.perf_counter() - self.start

# Usage
with PerformanceTimer() as timer:
    response = client.get("/health")
assert timer.duration < 0.1
```

## 🔄 Continuous Integration

### GitHub Actions Integration

The project includes comprehensive CI/CD in `.github/workflows/ci-cd.yml`:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    
    steps:
    - name: Run unit tests
      run: |
        cd backend
        uv run pytest tests/ -m 'unit' --cov=src --cov-report=xml
    
    - name: Run integration tests
      run: |
        cd backend
        uv run pytest tests/ -m 'integration'
```

### Test Commands

Automated test scripts:

```bash
# Quick development testing
./scripts/test_quick.sh

# Comprehensive testing with coverage
./scripts/run_all_tests.sh --coverage-only

# Performance testing only
./scripts/run_all_tests.sh --skip-e2e --performance-only

# Skip slow tests
./scripts/run_all_tests.sh --quick
```

### Coverage Reports

Generate and view coverage:

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html

# Generate XML for CI
pytest tests/ --cov=src --cov-report=xml
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/Users/bytedance/code/newtab/backend
pytest tests/

# Or use -m flag
python -m pytest tests/
```

#### 2. Database Connection Issues
```bash
# Clean up test databases
rm -f test_*.db
rm -f /tmp/test_query_cache.json

# Restart tests
pytest tests/
```

#### 3. Playwright Installation
```bash
# Install Playwright browsers
playwright install chromium

# Or using uv
uv run playwright install chromium
```

#### 4. Permission Issues
```bash
# Fix permissions
chmod +x scripts/*.sh

# Run with proper permissions
sudo ./scripts/run_all_tests.sh
```

### Debug Options

```bash
# Debug failing tests
pytest tests/ --pdb

# Capture output
pytest tests/ -s

# Show fixtures
pytest tests/ --fixtures

# Dry run (collect tests only)
pytest tests/ --collect-only
```

### Performance Issues

```bash
# Run tests with timing
pytest tests/ --durations=10

# Profile memory usage
pytest tests/ --profile

# Run minimal test set
pytest tests/ -m "unit and not slow"
```

### Test Data Cleanup

```bash
# Clean test artifacts
rm -rf .pytest_cache/
rm -f .coverage
rm -rf htmlcov/
rm -f test-results.xml
rm -f /tmp/test_query_cache.json
```

## 📊 Test Metrics

### Coverage Goals

- **Overall**: > 80%
- **Critical paths**: > 90%
- **New code**: > 95%

### Performance Benchmarks

- **Health endpoint**: < 100ms
- **Search endpoint**: < 1s
- **Index endpoint**: < 5s
- **Concurrent requests**: > 10 req/s

### Test Execution Time

- **Unit tests**: < 30s
- **Integration tests**: < 2min
- **E2E tests**: < 5min
- **Performance tests**: < 3min
- **Full suite**: < 10min

## 📚 Best Practices

### Test Organization

1. **One concept per test**: Each test should verify one behavior
2. **Descriptive names**: Test names should explain what they verify
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Independent tests**: Tests should not depend on each other
5. **Cleanup**: Always clean up test data

### Mock Usage

```python
# Mock external dependencies
@patch('src.api.indexing.ark_client')
def test_indexing_with_mock(mock_client):
    mock_client.generate_keywords.return_value = ["test", "keywords"]
    # Test implementation
```

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functions properly."""
    result = await some_async_function()
    assert result is not None
```

## 🎯 Test Strategy

### Test Pyramid

1. **Unit Tests (70%)**: Fast, isolated, many
2. **Integration Tests (20%)**: Medium speed, API level
3. **E2E Tests (10%)**: Slow, full workflow, few

### When to Write Tests

- **Before implementing** (TDD): For complex logic
- **During implementation**: For immediate feedback
- **After implementing**: For legacy code coverage
- **When fixing bugs**: Regression tests

### What to Test

**Always Test:**
- Public API endpoints
- Error conditions
- Edge cases
- Performance critical paths

**Consider Testing:**
- Private methods (if complex)
- Configuration loading
- Integration points

**Don't Test:**
- Framework code
- Simple getters/setters
- External libraries

---

This testing guide ensures comprehensive coverage and reliable quality assurance for the New Tab Backend project.