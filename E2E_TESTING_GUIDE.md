# E2E Testing Guide for New Tab

This guide provides comprehensive instructions for running end-to-end tests for the New Tab Chrome Extension and Backend.

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** with `uv` package manager
2. **Node.js 18+** (for extension development)
3. **Chrome/Chromium browser** (for extension testing)

### Installation

```bash
# Navigate to backend directory
cd backend

# Install dependencies using uv
uv install

# Install Playwright browsers (required for e2e tests)
uv run playwright install chromium
```

## 📋 Test Structure

### Current Test Files

| File | Purpose | Type | Status |
|------|---------|------|---------|
| `backend/tests/test_e2e_playwright.py` | Backend API E2E tests | E2E | ✅ Active |
| `backend/tests/test_e2e_extension.py` | Extension + Backend integration | E2E | ✅ Active |
| `backend/tests/test_simple_backend.py` | Simple backend API tests | Integration | ✅ Active |
| `backend/tests/test_integration_api.py` | Comprehensive API integration | Integration | ✅ Active |
| `backend/tests/test_query_cache.py` | Cache functionality tests | Unit | ✅ Active |
| `backend/tests/test_performance.py` | Performance benchmarks | Performance | ✅ Active |

### Deprecated Files (Cleaned Up)

- `test/comprehensive_ui_test.py` → Use `backend/tests/test_e2e_extension.py`
- `test/simple_extension_test.py` → Use `backend/tests/test_e2e_extension.py`
- `test/test_extension_playwright.py` → Use `backend/tests/test_e2e_extension.py`

## 🧪 Running Tests

### 1. Simple Backend Tests (Fastest)

```bash
cd backend
uv run pytest tests/test_simple_backend.py -v
```

**Duration:** ~10 seconds  
**Purpose:** Quick smoke tests for API endpoints

### 2. Integration Tests

```bash
cd backend
uv run pytest tests/test_integration_api.py -v
```

**Duration:** ~30 seconds  
**Purpose:** Comprehensive API testing with mocks

### 3. Backend E2E Tests

```bash
cd backend
uv run pytest tests/test_e2e_playwright.py -v
```

**Duration:** ~60 seconds  
**Purpose:** Full backend API testing with real server

### 4. Extension E2E Tests (Requires Display)

```bash
cd backend
uv run pytest tests/test_e2e_extension.py -v
```

**Duration:** ~120 seconds  
**Purpose:** Extension + Backend integration testing  
**Requirements:** Display available (not headless)

### 5. Performance Tests

```bash
cd backend
uv run pytest tests/test_performance.py -v
```

**Duration:** ~90 seconds  
**Purpose:** Performance benchmarking

### 6. All Tests

```bash
cd backend
uv run pytest -v
```

**Duration:** ~5 minutes  
**Purpose:** Complete test suite

## 🎯 Test Categories

### Unit Tests
```bash
uv run pytest -m unit -v
```
- Fast, isolated tests
- No external dependencies
- Test individual components

### Integration Tests
```bash
uv run pytest -m integration -v
```
- Test component interactions
- May use mocks for external services
- Database and API testing

### E2E Tests
```bash
uv run pytest -m e2e -v
```
- Full system testing
- Real browsers and servers
- Complete user workflows

### Performance Tests
```bash
uv run pytest -m performance -v
```
- Performance benchmarking
- Load testing
- Memory usage analysis

## 🔧 Configuration

### Test Markers

Tests are categorized using pytest markers:

```python
@pytest.mark.unit        # Unit tests
@pytest.mark.integration # Integration tests
@pytest.mark.e2e         # End-to-end tests
@pytest.mark.performance # Performance tests
@pytest.mark.slow        # Slow running tests
```

### Environment Variables

```bash
# Optional: Set custom test server port
export TEST_SERVER_PORT=8001

# Optional: Enable verbose logging
export TEST_LOG_LEVEL=DEBUG

# Optional: Skip browser-based tests
export SKIP_BROWSER_TESTS=true
```

### Backend Server Setup

The tests automatically start a test server, but you can also run it manually:

```bash
cd backend
uv run python -m src.main
```

Server will be available at `http://localhost:8000`

## 🐛 Troubleshooting

### Common Issues

#### 1. Playwright Installation Issues

```bash
# Reinstall Playwright browsers
uv run playwright install --force chromium
```

#### 2. Extension Loading Issues

```bash
# Check extension path
ls -la extension/manifest.json

# Verify extension structure
tree extension/
```

#### 3. Server Port Conflicts

```bash
# Check if port is in use
lsof -i :8000
lsof -i :8001

# Kill processes if needed
pkill -f uvicorn
```

#### 4. Permission Issues

```bash
# Fix permissions for test files
chmod +x backend/scripts/*.sh
```

#### 5. Browser Display Issues (Linux/Remote)

```bash
# For headless environments, skip extension tests
export SKIP_BROWSER_TESTS=true
uv run pytest tests/test_simple_backend.py tests/test_integration_api.py -v
```

### Test Debugging

#### Run Single Test

```bash
uv run pytest tests/test_e2e_extension.py::TestExtensionBasicFunctionality::test_extension_loads_new_tab -v -s
```

#### Enable Debug Output

```bash
uv run pytest tests/test_e2e_extension.py -v -s --tb=long
```

#### Manual Extension Testing

```bash
cd backend
uv run python tests/test_e2e_extension.py --manual
```

This opens a browser window for manual inspection.

## 📊 Test Coverage

### Generate Coverage Report

```bash
cd backend
uv run pytest --cov=src --cov-report=html tests/
```

View coverage report: `backend/htmlcov/index.html`

### Coverage Targets

- **Unit Tests:** >90% coverage
- **Integration Tests:** >80% coverage
- **E2E Tests:** >70% coverage

## 🚀 CI/CD Integration

### GitHub Actions

The project includes CI/CD configuration:

```yaml
# .github/workflows/ci.yml
- name: Run Backend Tests
  run: |
    cd backend
    uv run pytest tests/test_simple_backend.py tests/test_integration_api.py -v
```

### Local Pre-commit

```bash
# Install pre-commit hooks
pre-commit install

# Run all tests before commit
uv run pytest tests/test_simple_backend.py tests/test_integration_api.py
```

## 📈 Performance Benchmarks

### Expected Performance

| Test Suite | Duration | Memory Usage |
|------------|----------|--------------|
| Simple Backend | <10s | <50MB |
| Integration | <30s | <100MB |
| Backend E2E | <60s | <150MB |
| Extension E2E | <120s | <200MB |
| Performance | <90s | <100MB |

### Performance Testing

```bash
# Run performance benchmarks
uv run pytest tests/test_performance.py -v

# Profile memory usage
uv run pytest tests/test_performance.py --profile-svg
```

## 🔄 Continuous Testing

### Watch Mode (Development)

```bash
# Install pytest-watch
uv add --dev pytest-watch

# Run tests in watch mode
uv run ptw tests/test_simple_backend.py
```

### Automated Testing

```bash
# Run tests every 30 minutes
while true; do
  uv run pytest tests/test_simple_backend.py
  sleep 1800
done
```

## 📚 Test Data

### Sample Data

Tests use predefined sample data:

```python
# Sample page data
sample_page = {
    "url": "https://example.com/test",
    "title": "Test Page",
    "content": "Test content",
    "metadata": {"test": True}
}
```

### Fixtures

Common test fixtures are available in `backend/tests/conftest.py`:

- `client`: FastAPI test client
- `mock_ark_client`: Mocked API client
- `sample_page_data`: Sample page data
- `test_server`: Running test server

## 🎛️ Advanced Configuration

### Custom Test Configuration

Create `backend/pytest.local.ini`:

```ini
[tool:pytest]
testpaths = tests
markers =
    custom: Custom test marker
addopts = 
    --strict-markers
    --maxfail=5
    --tb=short
```

### Custom Test Data

Create test data files in `backend/tests/data/`:

```bash
mkdir -p backend/tests/data
echo '{"test": "data"}' > backend/tests/data/sample.json
```

## 🚦 Quality Gates

### Required Tests for PR

1. ✅ `test_simple_backend.py` - Must pass
2. ✅ `test_integration_api.py` - Must pass
3. ⚠️ `test_e2e_playwright.py` - Should pass
4. ⚠️ `test_e2e_extension.py` - Optional (requires display)

### Test Command for CI

```bash
cd backend && uv run pytest tests/test_simple_backend.py tests/test_integration_api.py tests/test_e2e_playwright.py -v
```

---

## 📞 Support

If you encounter issues with testing:

1. Check this guide first
2. Look at existing test files for examples
3. Check the troubleshooting section
4. Create an issue with test output and environment details

**Happy Testing! 🧪✨**