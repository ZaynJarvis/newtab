"""Comprehensive UI/UX testing for New Tab Chrome Extension.
This file has been deprecated. Use test_e2e_extension.py instead.
"""

# This file is deprecated - functionality moved to test_e2e_extension.py
import warnings

def main():
    warnings.warn(
        "comprehensive_ui_test.py is deprecated. Use 'uv run pytest tests/test_e2e_extension.py' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    print("❌ This test file is deprecated.")
    print("✅ Use: cd backend && uv run pytest tests/test_e2e_extension.py")
    return [], []


class ExtensionTester:
    """Comprehensive tester for the Chrome extension."""
    
    def __init__(self):
        self.extension_path = Path(__file__).parent.parent / "extension"
        self.findings = []
        self.improvements = []
        
    def add_finding(self, category, issue, severity="medium", suggestion=None):
        """Add a finding to the list."""
        self.findings.append({
            "category": category,
            "issue": issue,
            "severity": severity,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        })
        
    def add_improvement(self, category, description, priority="medium", implementation=None):
        """Add an improvement opportunity."""
        self.improvements.append({
            "category": category,
            "description": description,
            "priority": priority,
            "implementation": implementation,
            "timestamp": datetime.now().isoformat()
        })
    
    async def run_comprehensive_test(self):
        """Run all tests and generate report."""
        print("🔍 Starting comprehensive UI/UX testing...")
        
        async with async_playwright() as p:
            # Launch browser with extension
            context = await p.chromium.launch_persistent_context(
                user_data_dir=tempfile.mkdtemp(),
                headless=False,
                args=[
                    f"--load-extension={self.extension_path}",
                    f"--disable-extensions-except={self.extension_path}",
                    "--disable-web-security",
                    "--allow-running-insecure-content",
                ],
                viewport={"width": 1280, "height": 720}
            )
            
            try:
                await self.test_initial_load(context)
                await self.test_search_functionality(context)
                await self.test_keyboard_navigation(context)
                await self.test_settings_panel(context)
                await self.test_responsive_design(context)
                await self.test_accessibility(context)
                await self.test_performance(context)
                await self.test_error_handling(context)
                await self.test_visual_feedback(context)
                await self.test_user_experience(context)
                
            finally:
                await context.close()
        
        self.generate_report()
        return self.findings, self.improvements
    
    async def test_initial_load(self, context):
        """Test initial page load and basic UI elements."""
        print("📱 Testing initial load...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        
        # Test load time
        start_time = datetime.now()
        await page.wait_for_selector("#searchInput", timeout=10000)
        load_time = (datetime.now() - start_time).total_seconds()
        
        if load_time > 2:
            self.add_finding("performance", f"Slow initial load time: {load_time:.2f}s", "medium",
                           "Optimize JavaScript loading and reduce blocking operations")
        
        # Test if all critical elements are present
        critical_elements = ["#searchInput", ".search-container", "#settingsToggle", "#quickStats"]
        for element in critical_elements:
            if not await page.is_visible(element):
                self.add_finding("ui", f"Critical element not visible: {element}", "high",
                               "Ensure all critical UI elements load correctly")
        
        # Test autofocus
        focused_element = await page.evaluate("document.activeElement.id")
        if focused_element != "searchInput":
            self.add_finding("ux", "Search input doesn't have autofocus", "medium",
                           "Improve focus management for better user experience")
        
        await page.close()
    
    async def test_search_functionality(self, context):
        """Test search functionality and results display."""
        print("🔍 Testing search functionality...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test search input
        await page.fill("#searchInput", "test query")
        await page.wait_for_timeout(500)  # Wait for debounced search
        
        # Check if loading state appears
        loading_visible = await page.is_visible(".loading")
        if not loading_visible:
            self.add_improvement("ux", "Add loading state for search operations", "medium",
                               "Show spinner or skeleton while searching")
        
        # Test search results
        await page.wait_for_timeout(2000)
        results_visible = await page.is_visible("#searchResults")
        if not results_visible:
            self.add_finding("functionality", "Search results not displayed", "high",
                           "Ensure search results are properly shown")
        
        # Test empty search
        await page.fill("#searchInput", "")
        await page.wait_for_timeout(500)
        results_after_clear = await page.text_content("#searchResults")
        if results_after_clear.strip():
            self.add_finding("ux", "Results not cleared when search is empty", "low",
                           "Clear results when search input is empty")
        
        # Test long search queries
        long_query = "a" * 200
        await page.fill("#searchInput", long_query)
        input_value = await page.input_value("#searchInput")
        if len(input_value) == 200:
            self.add_improvement("ux", "Add input validation for very long queries", "low",
                               "Limit search query length to reasonable bounds")
        
        await page.close()
    
    async def test_keyboard_navigation(self, context):
        """Test keyboard navigation and shortcuts."""
        print("⌨️ Testing keyboard navigation...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test typing focuses input
        await page.press("body", "t")
        focused_after_keypress = await page.evaluate("document.activeElement.id")
        if focused_after_keypress != "searchInput":
            self.add_finding("accessibility", "Typing doesn't focus search input", "medium",
                           "Improve keyboard accessibility by focusing input on keypress")
        
        # Test tab navigation
        await page.press("#searchInput", "Tab")
        await page.wait_for_timeout(100)
        new_focused = await page.evaluate("document.activeElement.id")
        if new_focused == "searchInput":
            self.add_improvement("accessibility", "Add more tab-navigable elements", "medium",
                               "Improve tab navigation flow through the interface")
        
        # Test escape key
        await page.press("#searchInput", "Escape")
        still_focused = await page.evaluate("document.activeElement.id")
        if still_focused != "searchInput":
            self.add_finding("ux", "Escape key removes focus from search", "low",
                           "Keep focus on search input after escape")
        
        await page.close()
    
    async def test_settings_panel(self, context):
        """Test settings panel functionality."""
        print("⚙️ Testing settings panel...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#settingsToggle", timeout=10000)
        
        # Test settings panel opening
        await page.click("#settingsToggle")
        await page.wait_for_timeout(500)
        settings_visible = await page.is_visible("#settingsView")
        
        if not settings_visible:
            self.add_finding("functionality", "Settings panel doesn't open", "high",
                           "Fix settings panel animation and visibility")
        else:
            # Test settings panel content
            toggle_switches = await page.query_selector_all("input[type='checkbox']")
            if len(toggle_switches) < 2:
                self.add_improvement("features", "Add more configuration options", "low",
                                   "Add more user-configurable settings")
            
            # Test close settings
            await page.click("#closeSettings")
            await page.wait_for_timeout(500)
            settings_closed = not await page.is_visible("#settingsView")
            
            if not settings_closed:
                self.add_finding("ux", "Settings panel doesn't close properly", "medium",
                               "Fix settings panel close functionality")
            
            # Test focus return after closing
            focused_after_close = await page.evaluate("document.activeElement.id")
            if focused_after_close != "searchInput":
                self.add_improvement("ux", "Focus doesn't return to search after closing settings", "low",
                                   "Improve focus management")
        
        await page.close()
    
    async def test_responsive_design(self, context):
        """Test responsive design across different screen sizes."""
        print("📱 Testing responsive design...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test different viewport sizes
        viewports = [
            {"width": 320, "height": 568, "name": "Mobile Small"},
            {"width": 375, "height": 667, "name": "Mobile Medium"},
            {"width": 768, "height": 1024, "name": "Tablet"},
            {"width": 1024, "height": 768, "name": "Tablet Landscape"},
            {"width": 1440, "height": 900, "name": "Desktop"},
            {"width": 1920, "height": 1080, "name": "Large Desktop"}
        ]
        
        for viewport in viewports:
            await page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
            await page.wait_for_timeout(300)
            
            # Check if search input is still visible and usable
            search_visible = await page.is_visible("#searchInput")
            if not search_visible:
                self.add_finding("responsive", f"Search input not visible on {viewport['name']}", "high",
                               f"Fix layout for {viewport['name']} viewport")
            
            # Check if text is readable
            if viewport["width"] < 400:
                font_size = await page.evaluate("""
                    getComputedStyle(document.getElementById('searchInput')).fontSize
                """)
                if font_size and int(font_size.replace('px', '')) < 14:
                    self.add_improvement("accessibility", f"Font too small on {viewport['name']}", "medium",
                                       "Increase font sizes for better mobile readability")
        
        await page.close()
    
    async def test_accessibility(self, context):
        """Test accessibility features."""
        print("♿ Testing accessibility...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test ARIA labels
        search_input = await page.get_attribute("#searchInput", "aria-label")
        if not search_input:
            self.add_improvement("accessibility", "Add ARIA labels to search input", "medium",
                               "Add proper ARIA labels for screen readers")
        
        # Test color contrast (simplified check)
        bg_color = await page.evaluate("""
            getComputedStyle(document.body).backgroundColor
        """)
        
        text_color = await page.evaluate("""
            getComputedStyle(document.getElementById('searchInput')).color
        """)
        
        if bg_color and text_color:
            # This is a simplified check - in reality you'd use a proper contrast ratio calculator
            if "rgba(0, 0, 0, 0)" in bg_color or bg_color == "rgba(0, 0, 0, 0)":
                self.add_improvement("accessibility", "Improve color contrast for better readability", "medium",
                                   "Ensure sufficient color contrast ratios")
        
        # Test keyboard accessibility
        await page.press("#searchInput", "Tab")
        focusable_elements = await page.evaluate("""
            Array.from(document.querySelectorAll('button, input, a, [tabindex]')).length
        """)
        
        if focusable_elements < 3:
            self.add_improvement("accessibility", "Add more keyboard-navigable elements", "medium",
                               "Ensure all interactive elements are keyboard accessible")
        
        await page.close()
    
    async def test_performance(self, context):
        """Test performance aspects."""
        print("⚡ Testing performance...")
        
        page = await context.new_page()
        
        # Monitor network requests
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        
        start_time = datetime.now()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        load_time = (datetime.now() - start_time).total_seconds()
        
        # Check for excessive requests
        if len(requests) > 10:
            self.add_improvement("performance", f"High number of requests during load: {len(requests)}", "medium",
                               "Optimize and reduce number of network requests")
        
        # Test search performance
        search_start = datetime.now()
        await page.fill("#searchInput", "performance test")
        await page.wait_for_timeout(2000)  # Wait for search to complete
        search_time = (datetime.now() - search_start).total_seconds()
        
        if search_time > 3:
            self.add_improvement("performance", f"Slow search response: {search_time:.2f}s", "high",
                               "Optimize search performance and add caching")
        
        # Test memory usage (simplified)
        js_heap_size = await page.evaluate("performance.memory?.usedJSHeapSize || 0")
        if js_heap_size > 50 * 1024 * 1024:  # 50MB
            self.add_improvement("performance", f"High memory usage: {js_heap_size // (1024*1024)}MB", "medium",
                               "Optimize memory usage and prevent memory leaks")
        
        await page.close()
    
    async def test_error_handling(self, context):
        """Test error handling and resilience."""
        print("🛡️ Testing error handling...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Monitor console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        # Test with special characters
        special_queries = ["<script>alert('xss')</script>", "'; DROP TABLE users; --", "🚀🔍💻"]
        
        for query in special_queries:
            await page.fill("#searchInput", query)
            await page.wait_for_timeout(1000)
            
            # Check if page is still functional
            input_functional = await page.is_enabled("#searchInput")
            if not input_functional:
                self.add_finding("security", f"Input becomes non-functional with query: {query}", "high",
                               "Improve input sanitization and error handling")
        
        # Check for console errors
        if console_errors:
            self.add_finding("errors", f"Console errors detected: {len(console_errors)}", "medium",
                           "Fix JavaScript errors for better stability")
        
        await page.close()
    
    async def test_visual_feedback(self, context):
        """Test visual feedback and animations."""
        print("✨ Testing visual feedback...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test hover effects
        await page.hover("#settingsToggle")
        await page.wait_for_timeout(100)
        
        # Test focus visual feedback
        await page.focus("#searchInput")
        focused_styles = await page.evaluate("""
            getComputedStyle(document.querySelector('.search-box:focus-within')).boxShadow
        """)
        
        if not focused_styles or focused_styles == "none":
            self.add_improvement("ux", "Add visual focus indicators", "medium",
                               "Improve visual feedback for focused elements")
        
        # Test button interactions
        buttons = await page.query_selector_all("button")
        if len(buttons) == 0:
            self.add_improvement("ux", "Add interactive buttons for common actions", "low",
                               "Add quick action buttons for better UX")
        
        await page.close()
    
    async def test_user_experience(self, context):
        """Test overall user experience."""
        print("🎯 Testing user experience...")
        
        page = await context.new_page()
        await page.goto("chrome://newtab/")
        await page.wait_for_selector("#searchInput", timeout=10000)
        
        # Test common user workflows
        
        # 1. Search workflow
        await page.fill("#searchInput", "example search")
        await page.wait_for_timeout(1000)
        
        # Check if results are displayed nicely
        results_exist = await page.is_visible("#searchResults")
        if results_exist:
            result_cards = await page.query_selector_all(".result-card")
            if len(result_cards) == 0:
                self.add_improvement("ux", "No search results displayed for mock search", "low",
                                   "Ensure mock data is shown when backend is unavailable")
        
        # 2. Settings workflow
        await page.click("#settingsToggle")
        await page.wait_for_timeout(300)
        settings_smooth = await page.evaluate("""
            getComputedStyle(document.getElementById('settingsView')).transition
        """)
        
        if not settings_smooth or "transition" not in settings_smooth:
            self.add_improvement("ux", "Add smooth animations for settings panel", "low",
                               "Add CSS transitions for smoother interactions")
        
        # 3. Check for empty states
        stats_text = await page.text_content("#totalPages")
        if stats_text == "0":
            empty_state_guidance = await page.is_visible(".empty-state-help")
            if not empty_state_guidance:
                self.add_improvement("ux", "Add empty state guidance for new users", "medium",
                                   "Show helpful messages when no data is available")
        
        await page.close()
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE UI/UX TEST REPORT")
        print("="*60)
        
        # Summary
        total_findings = len(self.findings)
        total_improvements = len(self.improvements)
        
        high_priority = len([f for f in self.findings if f["severity"] == "high"])
        medium_priority = len([f for f in self.findings if f["severity"] == "medium"])
        low_priority = len([f for f in self.findings if f["severity"] == "low"])
        
        print(f"\n📈 SUMMARY:")
        print(f"   Issues Found: {total_findings}")
        print(f"   - High Priority: {high_priority}")
        print(f"   - Medium Priority: {medium_priority}")
        print(f"   - Low Priority: {low_priority}")
        print(f"   Improvement Opportunities: {total_improvements}")
        
        # Findings by category
        categories = {}
        for finding in self.findings:
            cat = finding["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(finding)
        
        print(f"\n🔍 ISSUES BY CATEGORY:")
        for category, issues in categories.items():
            print(f"\n   {category.upper()}:")
            for issue in issues:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                icon = priority_icon.get(issue["severity"], "⚪")
                print(f"   {icon} {issue['issue']}")
                if issue["suggestion"]:
                    print(f"      💡 {issue['suggestion']}")
        
        # Improvements by category
        imp_categories = {}
        for improvement in self.improvements:
            cat = improvement["category"]
            if cat not in imp_categories:
                imp_categories[cat] = []
            imp_categories[cat].append(improvement)
        
        print(f"\n🚀 IMPROVEMENT OPPORTUNITIES:")
        for category, improvements in imp_categories.items():
            print(f"\n   {category.upper()}:")
            for improvement in improvements:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                icon = priority_icon.get(improvement["priority"], "⚪")
                print(f"   {icon} {improvement['description']}")
                if improvement["implementation"]:
                    print(f"      🔧 {improvement['implementation']}")
        
        # Save detailed report
        report_data = {
            "test_date": datetime.now().isoformat(),
            "summary": {
                "total_findings": total_findings,
                "high_priority": high_priority,
                "medium_priority": medium_priority,
                "low_priority": low_priority,
                "total_improvements": total_improvements
            },
            "findings": self.findings,
            "improvements": self.improvements
        }
        
        report_path = Path(__file__).parent / "ui_test_report.json"
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        print("\n" + "="*60)


async def main():
    """Run the comprehensive test suite."""
    tester = ExtensionTester()
    findings, improvements = await tester.run_comprehensive_test()
    return findings, improvements


if __name__ == "__main__":
    asyncio.run(main())