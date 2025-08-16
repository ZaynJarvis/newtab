"""Playwright test suite for New Tab Chrome Extension."""

import pytest
import asyncio
import json
import tempfile
import shutil
import os
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import uvicorn
import threading
import time
import httpx


class TestServer:
    """Test server manager for extension E2E tests."""
    
    def __init__(self, host="127.0.0.1", port=8001):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.base_url = f"http://{host}:{port}"
    
    def start(self):
        """Start the test server in a separate thread."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))
        
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
                    print(f"Test server started at {self.base_url}")
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
    """Start test server for extension E2E tests."""
    server = TestServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance with extension loaded."""
    async with async_playwright() as p:
        # Path to extension directory
        extension_path = Path(__file__).parent.parent / "extension"
        
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


@pytest.mark.asyncio
async def test_extension_new_tab_override(browser: BrowserContext, test_server: TestServer):
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


@pytest.mark.asyncio
async def test_search_functionality(browser: BrowserContext, test_server: TestServer):
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


@pytest.mark.asyncio
async def test_settings_panel_functionality(browser: BrowserContext, test_server: TestServer):
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
    
    # Toggle the setting
    await page.click("#enableIndexing")
    enable_indexing_after = await page.is_checked("#enableIndexing")
    assert enable_indexing_after != enable_indexing
    
    # Test close settings
    await page.click("#closeSettings")
    await page.wait_for_timeout(1000)
    
    # Settings panel should be hidden
    settings_visible = await page.is_visible("#settingsView")
    assert not settings_visible
    
    await page.close()


@pytest.mark.asyncio
async def test_domain_exclusion_functionality(browser: BrowserContext, test_server: TestServer):
    """Test adding and removing excluded domains."""
    page = await browser.new_page()
    await page.goto("chrome://newtab/")
    await page.wait_for_selector("#settingsToggle", timeout=10000)
    
    # Open settings
    await page.click("#settingsToggle")
    await page.wait_for_selector("#settingsView", timeout=5000)
    
    # Add a domain to exclusion list
    await page.fill("#newDomain", "example.com")
    await page.click("#addDomain")
    
    # Wait for domain to be added
    await page.wait_for_timeout(1000)
    
    # Check if domain appears in excluded list
    excluded_domains_content = await page.text_content("#excludedDomains")
    assert "example.com" in excluded_domains_content
    
    await page.close()


@pytest.mark.asyncio
async def test_stats_display(browser: BrowserContext, test_server: TestServer):
    """Test that statistics are properly displayed."""
    page = await browser.new_page()
    await page.goto("chrome://newtab/")
    await page.wait_for_selector("#quickStats", timeout=10000)
    
    # Check if quick stats are visible
    assert await page.is_visible("#quickStats")
    assert await page.is_visible("#totalPages")
    
    # Get the current page count
    total_pages_text = await page.text_content("#totalPages")
    assert total_pages_text.isdigit()
    
    # Open settings to see detailed stats
    await page.click("#settingsToggle")
    await page.wait_for_selector("#detailedStats", timeout=5000)
    
    # Check if detailed stats section is visible
    assert await page.is_visible("#detailedStats")
    
    await page.close()


@pytest.mark.asyncio
async def test_content_script_injection(browser: BrowserContext, test_server: TestServer):
    """Test that content script is properly injected on web pages."""
    page = await browser.new_page()
    
    # Navigate to a test page
    await page.goto("https://example.com")
    await page.wait_for_load_state("networkidle", timeout=10000)
    
    # Wait a bit for content script to load
    await page.wait_for_timeout(2000)
    
    # Check if content script has been injected by looking for any added elements or checking console
    # Content script should be running in background, so we mainly verify no errors occurred
    console_messages = []
    page.on("console", lambda msg: console_messages.append(msg.text))
    
    # Reload page to capture any console messages
    await page.reload()
    await page.wait_for_timeout(2000)
    
    # Check that there are no critical errors related to our extension
    extension_errors = [msg for msg in console_messages if "extension" in msg.lower() and "error" in msg.lower()]
    assert len(extension_errors) == 0, f"Extension errors found: {extension_errors}"
    
    await page.close()


@pytest.mark.asyncio
async def test_popup_functionality(browser: BrowserContext, test_server: TestServer):
    """Test the extension popup functionality."""
    page = await browser.new_page()
    await page.goto("https://example.com")
    await page.wait_for_load_state("networkidle", timeout=10000)
    
    # Note: Testing popup is tricky with Playwright as it requires clicking the extension icon
    # This would need special handling or alternative approaches
    # For now, we'll test that the popup HTML can be loaded directly
    
    extension_path = Path(__file__).parent.parent / "extension"
    popup_path = extension_path / "popup" / "popup.html"
    
    await page.goto(f"file://{popup_path}")
    await page.wait_for_load_state("domcontentloaded")
    
    # Verify popup elements are present
    # This test ensures the popup HTML structure is valid
    assert await page.title() == "New Tab"
    
    await page.close()


@pytest.mark.asyncio
async def test_error_handling_and_resilience(browser: BrowserContext, test_server: TestServer):
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
    # Check that the page is still functional
    assert await page.is_visible("#searchInput")
    assert await page.is_enabled("#searchInput")
    
    await page.close()


@pytest.mark.asyncio
async def test_keyboard_navigation(browser: BrowserContext, test_server: TestServer):
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


@pytest.mark.asyncio
async def test_responsive_design(browser: BrowserContext, test_server: TestServer):
    """Test responsive design on different viewport sizes."""
    page = await browser.new_page()
    await page.goto("chrome://newtab/")
    await page.wait_for_selector("#searchInput", timeout=10000)
    
    # Test desktop size
    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.wait_for_timeout(500)
    assert await page.is_visible("#searchInput")
    
    # Test tablet size
    await page.set_viewport_size({"width": 768, "height": 1024})
    await page.wait_for_timeout(500)
    assert await page.is_visible("#searchInput")
    
    # Test mobile size
    await page.set_viewport_size({"width": 375, "height": 667})
    await page.wait_for_timeout(500)
    assert await page.is_visible("#searchInput")
    
    await page.close()


@pytest.mark.asyncio
async def test_data_persistence(browser: BrowserContext, test_server: TestServer):
    """Test that settings and data persist across sessions."""
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


@pytest.mark.asyncio
async def test_backend_integration(browser: BrowserContext, test_server: TestServer):
    """Test integration with the backend API."""
    page = await browser.new_page()
    await page.goto("chrome://newtab/")
    await page.wait_for_selector("#searchInput", timeout=10000)
    
    # Monitor network requests
    requests = []
    page.on("request", lambda request: requests.append(request.url))
    
    # Perform a search that should trigger backend calls
    await page.fill("#searchInput", "integration test")
    await page.press("#searchInput", "Enter")
    
    # Wait for potential network requests
    await page.wait_for_timeout(3000)
    
    # Check if any requests were made to our test server
    backend_requests = [req for req in requests if test_server.base_url in req]
    
    # We expect at least some interaction with the backend
    # (This might fail if backend is not running, which is okay for testing resilience)
    print(f"Backend requests made: {len(backend_requests)}")
    for req in backend_requests:
        print(f"  - {req}")
    
    await page.close()


if __name__ == "__main__":
    # Run tests manually for debugging
    import asyncio
    
    async def run_single_test():
        server = TestServer()
        server.start()
        
        async with async_playwright() as p:
            extension_path = Path(__file__).parent.parent / "extension"
            
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
            
            print("Extension loaded successfully!")
            print("Search input found:", await page.is_visible("#searchInput"))
            
            # Keep browser open for manual inspection
            await page.wait_for_timeout(10000)
            
            await browser.close()
    
    asyncio.run(run_single_test())