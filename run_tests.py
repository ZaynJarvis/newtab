#!/usr/bin/env python3
"""Simple test runner for Local Web Memory E2E tests."""

import subprocess
import sys
import time
import os
from pathlib import Path


def run_command(cmd, description, timeout=300):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent / "backend",
            capture_output=False,
            timeout=timeout
        )
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n✅ {description} - PASSED ({duration:.1f}s)")
            return True
        else:
            print(f"\n❌ {description} - FAILED ({duration:.1f}s)")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏰ {description} - TIMEOUT ({timeout}s)")
        return False
    except Exception as e:
        print(f"\n💥 {description} - ERROR: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    # Check if we're in the right directory
    if not (Path.cwd() / "backend" / "pyproject.toml").exists():
        print("❌ Error: Run this script from the project root directory")
        print("   Expected: backend/pyproject.toml to exist")
        return False
    
    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        print("✅ uv is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: uv is not installed")
        print("   Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    
    # Check if dependencies are installed
    try:
        result = subprocess.run(
            ["uv", "run", "python", "-c", "import pytest, playwright"],
            cwd=Path.cwd() / "backend",
            capture_output=True
        )
        if result.returncode == 0:
            print("✅ Python dependencies are available")
        else:
            print("⚠️  Installing dependencies...")
            subprocess.run(["uv", "install"], cwd=Path.cwd() / "backend", check=True)
            print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Error: Failed to install dependencies")
        return False
    
    return True


def main():
    """Main test runner."""
    print("🚀 Local Web Memory E2E Test Runner")
    print("=" * 60)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "all"
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    results = []
    
    if test_type in ["simple", "all"]:
        success = run_command(
            ["uv", "run", "pytest", "tests/test_simple_backend.py", "-v"],
            "Simple Backend Tests",
            60
        )
        results.append(("Simple Backend", success))
    
    if test_type in ["integration", "all"]:
        success = run_command(
            ["uv", "run", "pytest", "tests/test_integration_api.py", "-v"],
            "Integration API Tests",
            120
        )
        results.append(("Integration API", success))
    
    if test_type in ["backend", "all"]:
        success = run_command(
            ["uv", "run", "pytest", "tests/test_e2e_playwright.py", "-v"],
            "Backend E2E Tests",
            180
        )
        results.append(("Backend E2E", success))
    
    if test_type in ["extension", "all"] and not os.environ.get("SKIP_BROWSER_TESTS"):
        success = run_command(
            ["uv", "run", "pytest", "tests/test_e2e_extension.py", "-v"],
            "Extension E2E Tests",
            300
        )
        results.append(("Extension E2E", success))
    elif test_type in ["extension", "all"]:
        print("\n⚠️  Skipping Extension E2E Tests (SKIP_BROWSER_TESTS set)")
    
    if test_type in ["performance"]:
        success = run_command(
            ["uv", "run", "pytest", "tests/test_performance.py", "-v"],
            "Performance Tests",
            180
        )
        results.append(("Performance", success))
    
    if test_type in ["cache"]:
        success = run_command(
            ["uv", "run", "pytest", "tests/test_query_cache.py", "-v"],
            "Cache Tests",
            60
        )
        results.append(("Cache", success))
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {name:20} {status}")
    
    print(f"\n🎯 Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


def print_help():
    """Print help information."""
    print("""
🧪 Local Web Memory Test Runner

Usage:
    python run_tests.py [test_type]

Test Types:
    simple      - Run simple backend tests (fastest)
    integration - Run integration API tests
    backend     - Run backend E2E tests
    extension   - Run extension E2E tests (requires display)
    performance - Run performance tests
    cache       - Run cache tests
    all         - Run all tests (default)

Examples:
    python run_tests.py simple
    python run_tests.py integration
    python run_tests.py all

Environment Variables:
    SKIP_BROWSER_TESTS=true  - Skip browser-based tests
    TEST_LOG_LEVEL=DEBUG     - Enable debug logging

Quick Commands:
    # Fastest tests (for CI)
    python run_tests.py simple

    # Full test suite
    python run_tests.py all

    # Skip browser tests
    SKIP_BROWSER_TESTS=true python run_tests.py all
""")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        print_help()
    else:
        main()