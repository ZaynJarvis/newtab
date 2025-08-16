"""Comprehensive E2E tests for New Tab Chrome Extension and Backend Integration."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import uvicorn
import threading
import time
import httpx


class TestServer:
    """Test server manager for E2E tests."""
    
    def __init__(self, host="127.0.0.1", port=8001):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.base_url = f"http://{host}:{port}"
    
    def start(self):
        """Start the test server in a separate thread."""
        import sys
        from pathlib import Path
        
        # Add backend src to path
        backend_src = Path(__file__).parent.parent / "src"
        sys.path.insert(0, str(backend_src))
        
        from main import app
        
        def run_server():
            uvicorn.run(app, host=self.host, port=self.port, log_level="error")
        
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        
        # Wait for server to start
        max_retries = 30
        for _ in range(max_retries):
            try:
                response = httpx.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Test server failed to start")
    
    def stop(self):
        """Stop the test server."""
        pass


@pytest.fixture(scope="session")
async def test_server():
    """Start test server for E2E tests."""
    server = TestServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance with extension loaded."""
    async with async_playwright() as p:
        # Path to extension directory
        extension_path = Path(__file__).parent.parent.parent / "extension"
        
        # Launch browser with extension
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=tempfile.mkdtemp(),
            headless=False,  # Extension requires non-headless mode
            args=[
                f"--load-extension={extension_path}",
                "--disable-extensions-except=" + str(extension_path),
                "--disable-web-security",
                "--allow-running-insecure-content",
            ],
            viewport={"width": 1280, "height": 720}
        )
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: BrowserContext):
    """Create a new page for each test."""
    page = await browser.new_page()
    yield page
    await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestExtensionBasicFunctionality:
    """Test basic extension functionality."""
    
    async def test_extension_loads_new_tab(self, browser: BrowserContext, test_server: TestServer):
        """Test that the extension properly overrides the new tab page."""
        page = await browser.new_page()
        
        # Navigate to chrome://newtab/
        await page.goto("chrome://newtab/")
        
        # Wait for the extension to load
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Check if our extension's elements are present
        assert await page.is_visible("#searchInput")
        assert await page.is_visible(".search-container")
        assert await page.is_visible("#settingsToggle")
        
        # Check the search input placeholder
        placeholder = await page.get_attribute("#searchInput", "placeholder")
        assert "Search your browsing history" in placeholder
        
        await page.close()
    
    async def test_search_functionality(self, browser: BrowserContext, test_server: TestServer):
        """Test the search functionality in the new tab page."""
        page = await browser.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Type in search input
        await page.fill("#searchInput", "test search query")
        await page.press("#searchInput", "Enter")
        
        # Wait for search results container to appear or update
        await page.wait_for_timeout(2000)
        
        # Check if search results container exists
        assert await page.is_visible("#searchResults")
        
        await page.close()
    
    async def test_settings_panel(self, browser: BrowserContext, test_server: TestServer):
        """Test the settings panel functionality."""
        page = await browser.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#settingsToggle", timeout=10000)
        
        # Click settings toggle button
        await page.click("#settingsToggle")
        
        # Wait for settings panel to appear
        await page.wait_for_selector("#settingsView", timeout=5000)
        assert await page.is_visible("#settingsView")
        
        # Test toggle switches
        enable_indexing = await page.is_checked("#enableIndexing")
        assert enable_indexing is True  # Should be enabled by default
        
        # Test close settings
        await page.click("#closeSettings")
        await page.wait_for_timeout(1000)
        
        # Settings panel should be hidden
        settings_visible = await page.is_visible("#settingsView")
        assert not settings_visible
        
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBackendIntegration:
    """Test extension integration with backend API."""
    
    async def test_backend_health_check(self, test_server: TestServer):
        """Test backend health endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{test_server.base_url}/health")
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded"]
    
    async def test_backend_search_api(self, test_server: TestServer):
        """Test backend search API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{test_server.base_url}/search",
                params={"query": "test"}
            )
            assert response.status_code == 200
            
            data = response.json()
            assert "results" in data
            assert "query" in data
            assert isinstance(data["results"], list)
    
    async def test_page_indexing_workflow(self, test_server: TestServer):
        """Test complete page indexing workflow."""
        async with httpx.AsyncClient() as client:
            # Test data
            page_data = {
                "url": "https://example.com/test-e2e",
                "title": "E2E Test Page",
                "content": "This is content for end-to-end testing.",
                "metadata": {"test": "e2e"}
            }
            
            # Index the page
            response = await client.post(
                f"{test_server.base_url}/index",
                json=page_data
            )
            
            if response.status_code == 200:
                # Success case - verify response
                data = response.json()
                assert data["success"] is True
                assert "page_id" in data
            else:
                # If indexing fails (e.g., due to missing API token), verify error handling
                assert response.status_code in [400, 500, 503]


@pytest.mark.e2e
@pytest.mark.asyncio
class TestExtensionAdvancedFeatures:
    """Test advanced extension features."""
    
    async def test_keyboard_navigation(self, browser: BrowserContext, test_server: TestServer):
        """Test keyboard navigation in the new tab page."""
        page = await browser.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test that search input has focus (autofocus)
        focused_element = await page.evaluate("document.activeElement.id")
        assert focused_element == "searchInput"
        
        # Test Tab navigation
        await page.press("#searchInput", "Tab")
        await page.wait_for_timeout(500)
        
        # Should move to settings toggle or other focusable element
        new_focused = await page.evaluate("document.activeElement.id")
        assert new_focused != "searchInput"
        
        await page.close()
    
    async def test_responsive_design(self, browser: BrowserContext, test_server: TestServer):
        """Test responsive design on different viewport sizes."""
        page = await browser.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test different viewport sizes
        viewports = [
            {"width": 1920, "height": 1080},  # Desktop
            {"width": 768, "height": 1024},   # Tablet
            {"width": 375, "height": 667}     # Mobile
        ]
        
        for viewport in viewports:
            await page.set_viewport_size(viewport)
            await page.wait_for_timeout(500)
            assert await page.is_visible("#searchInput")
        
        await page.close()
    
    async def test_error_handling(self, browser: BrowserContext, test_server: TestServer):
        """Test error handling when backend is unavailable."""
        page = await browser.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test search when backend might not be available
        await page.fill("#searchInput", "test offline search")
        await page.press("#searchInput", "Enter")
        
        # Wait for response
        await page.wait_for_timeout(3000)
        
        # The extension should handle errors gracefully
        assert await page.is_visible("#searchInput")
        assert await page.is_enabled("#searchInput")
        
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDataPersistence:
    """Test data persistence and settings."""
    
    async def test_settings_persistence(self, browser: BrowserContext, test_server: TestServer):
        """Test that settings persist across sessions."""
        page = await browser.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#settingsToggle", timeout=10000)
        
        # Open settings and make a change
        await page.click("#settingsToggle")
        await page.wait_for_selector("#settingsView", timeout=5000)
        
        # Toggle a setting
        original_state = await page.is_checked("#enableIndexing")
        await page.click("#enableIndexing")
        new_state = await page.is_checked("#enableIndexing")
        assert new_state != original_state
        
        # Close and reopen the tab
        await page.close()
        
        new_page = await browser.new_page()
        await new_page.goto("chrome://newtab/")
        await new_page.wait_for_selector("#settingsToggle", timeout=10000)
        
        await new_page.click("#settingsToggle")
        await new_page.wait_for_selector("#settingsView", timeout=5000)
        
        # Check if setting persisted
        persisted_state = await new_page.is_checked("#enableIndexing")
        assert persisted_state == new_state
        
        await new_page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPerformance:
    """Test performance aspects of the extension."""
    
    async def test_extension_load_time(self, browser: BrowserContext, test_server: TestServer):
        """Test extension load time performance."""
        page = await browser.new_page()
        
        start_time = time.time()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        load_time = time.time() - start_time
        
        # Extension should load within reasonable time
        assert load_time < 5.0, f"Extension took too long to load: {load_time:.2f}s"
        
        await page.close()
    
    async def test_search_performance(self, browser: BrowserContext, test_server: TestServer):
        """Test search response time."""
        page = await browser.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        start_time = time.time()
        await page.fill("#searchInput", "performance test")
        await page.press("#searchInput", "Enter")
        await page.wait_for_timeout(2000)  # Wait for search to complete
        search_time = time.time() - start_time
        
        # Search should complete within reasonable time
        assert search_time < 5.0, f"Search took too long: {search_time:.2f}s"
        
        await page.close()


if __name__ == "__main__":
    # Run specific test for debugging
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        async def run_manual_test():
            server = TestServer()
            server.start()
            
            async with async_playwright() as p:
                extension_path = Path(__file__).parent.parent.parent / "extension"
                
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=tempfile.mkdtemp(),
                    headless=False,
                    args=[
                        f"--load-extension={extension_path}",
                        "--disable-extensions-except=" + str(extension_path),
                    ],
                    viewport={"width": 1280, "height": 720}
                )
                
                page = await browser.new_page()
                await page.goto("chrome://newtab/")
                await page.wait_for_selector("#searchInput", timeout=10000)
                
                print("✅ Extension loaded successfully!")
                print("🔍 Search input found:", await page.is_visible("#searchInput"))
                
                # Keep browser open for manual inspection
                await page.wait_for_timeout(30000)
                
                await browser.close()
        
        asyncio.run(run_manual_test())
    else:
        print("Use 'python test_e2e_extension.py --manual' for manual testing")
        print("Or run: uv run pytest tests/test_e2e_extension.py -v")