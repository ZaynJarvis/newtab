"""Simple Playwright test to manually inspect the Chrome extension.
This file has been deprecated. Use backend/tests/test_e2e_playwright.py instead.
"""

# This file is deprecated - functionality moved to backend/tests/
import warnings

def main():
    warnings.warn(
        "simple_extension_test.py is deprecated. Use backend tests instead.",
        DeprecationWarning,
        stacklevel=2
    )
    print("❌ This test file is deprecated.")
    print("✅ Use: cd backend && uv run pytest tests/test_e2e_playwright.py -v")
    return


async def test_extension_basic():
    """Basic test to load extension and inspect new tab functionality."""
    
    async with async_playwright() as p:
        # Path to extension directory
        extension_path = Path(__file__).parent.parent / "extension"
        print(f"Extension path: {extension_path}")
        
        # Launch browser with extension
        context = await p.chromium.launch_persistent_context(
            user_data_dir=tempfile.mkdtemp(),
            headless=False,  # Extension requires non-headless mode
            args=[
                f"--load-extension={extension_path}",
                f"--disable-extensions-except={extension_path}",
                "--disable-web-security",
                "--allow-running-insecure-content",
            ],
            viewport={"width": 1280, "height": 720}
        )
        
        print("Browser launched with extension")
        
        # Create new page and navigate to new tab
        page = await context.new_page()
        print("New page created")
        
        try:
            await page.goto("chrome://newtab/")
            print("Navigated to chrome://newtab/")
            
            # Wait for the extension to load
            await page.wait_for_selector("#searchInput", timeout=10000)
            print("Search input found - extension loaded successfully!")
            
            # Test basic UI elements
            elements_to_check = [
                "#searchInput",
                ".search-container", 
                "#settingsToggle",
                "#searchResults",
                "#quickStats"
            ]
            
            print("\nChecking UI elements:")
            for element in elements_to_check:
                is_visible = await page.is_visible(element)
                print(f"  {element}: {'✓ visible' if is_visible else '✗ not visible'}")
            
            # Test search input
            placeholder = await page.get_attribute("#searchInput", "placeholder")
            print(f"\nSearch placeholder: {placeholder}")
            
            # Test typing in search
            await page.fill("#searchInput", "test search")
            search_value = await page.input_value("#searchInput")
            print(f"Search input value: {search_value}")
            
            # Test settings panel
            await page.click("#settingsToggle")
            await page.wait_for_timeout(1000)
            settings_visible = await page.is_visible("#settingsView")
            print(f"Settings panel visible after click: {settings_visible}")
            
            # Keep browser open for manual inspection
            print("\nExtension test completed. Browser will stay open for 15 seconds for manual inspection...")
            await page.wait_for_timeout(15000)
            
        except Exception as e:
            print(f"Error during test: {e}")
            # Take screenshot for debugging
            await page.screenshot(path="extension_error.png")
            print("Screenshot saved as extension_error.png")
            
        finally:
            await context.close()
            print("Browser closed")


if __name__ == "__main__":
    asyncio.run(test_extension_basic())