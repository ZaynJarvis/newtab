// Content script for extracting page content
(function() {
  'use strict';

  // Check if we should index this page
  function shouldIndexPage() {
    // Skip extension pages, chrome:// URLs, etc.
    const url = window.location.href;
    if (url.startsWith('chrome://') || 
        url.startsWith('chrome-extension://') || 
        url.startsWith('about:') ||
        url.startsWith('file://')) {
      return false;
    }
    
    // Skip if page has no meaningful content
    const bodyText = document.body?.innerText || '';
    if (bodyText.trim().length < 100) {
      return false;
    }
    
    return true;
  }

  // Extract main content from the page
  function extractPageContent() {
    // Try to find main content areas
    const contentSelectors = [
      'main',
      'article',
      '[role="main"]',
      '#content',
      '.content',
      '#main',
      '.main'
    ];
    
    let mainContent = '';
    
    // Try to find main content area
    for (const selector of contentSelectors) {
      const element = document.querySelector(selector);
      if (element) {
        mainContent = element.innerText || element.textContent || '';
        if (mainContent.length > 100) {
          break;
        }
      }
    }
    
    // Fallback to body content if no main area found
    if (!mainContent || mainContent.length < 100) {
      mainContent = document.body.innerText || document.body.textContent || '';
    }
    
    // Clean up the content
    mainContent = mainContent
      .replace(/\s+/g, ' ')  // Normalize whitespace
      .replace(/\n{3,}/g, '\n\n')  // Limit consecutive newlines
      .trim();
    
    // Limit content length to avoid overwhelming the API
    const MAX_CONTENT_LENGTH = 10000;
    if (mainContent.length > MAX_CONTENT_LENGTH) {
      mainContent = mainContent.substring(0, MAX_CONTENT_LENGTH) + '...';
    }
    
    return mainContent;
  }

  // Extract metadata
  function extractMetadata() {
    // Get page title
    const title = document.title || 
                  document.querySelector('h1')?.innerText || 
                  'Untitled Page';
    
    // Get meta description
    const metaDescription = document.querySelector('meta[name="description"]')?.content ||
                           document.querySelector('meta[property="og:description"]')?.content ||
                           '';
    
    // Get favicon URL
    let faviconUrl = '';
    const favicon = document.querySelector('link[rel="icon"]') || 
                   document.querySelector('link[rel="shortcut icon"]');
    if (favicon) {
      faviconUrl = new URL(favicon.href, window.location.origin).href;
    } else {
      faviconUrl = new URL('/favicon.ico', window.location.origin).href;
    }
    
    return {
      title,
      metaDescription,
      faviconUrl
    };
  }

  // Track visit duration to avoid indexing pages with short visits
  let pageStartTime = Date.now();
  let isProcessingScheduled = false;

  // Main function to process the page
  function processPage() {
    if (!shouldIndexPage()) {
      console.log('Page skipped: not eligible for indexing');
      return;
    }
    
    // Check if user has been on page for at least 5 seconds
    const visitDuration = Date.now() - pageStartTime;
    if (visitDuration < 5000) {
      console.log('Page skipped: visit duration too short');
      return;
    }
    
    const content = extractPageContent();
    const metadata = extractMetadata();
    
    // Send data to service worker
    chrome.runtime.sendMessage({
      type: 'INDEX_PAGE',
      data: {
        url: window.location.href,
        title: metadata.title,
        content: content,
        metaDescription: metadata.metaDescription,
        favicon_url: metadata.faviconUrl,
        timestamp: new Date().toISOString()
      }
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('Error sending page data:', chrome.runtime.lastError);
      } else if (response?.success) {
        console.log('Page indexed successfully:', response.message);
      } else if (response?.error) {
        console.error('Failed to index page:', response.error);
      }
    });
  }

  // Wait for page to fully load and check if user is still on page
  function schedulePageProcessing() {
    if (isProcessingScheduled) {
      return;
    }
    isProcessingScheduled = true;
    
    // Increased delay to 5 seconds to allow dynamic content to load
    // and ensure user is actively reading the page
    setTimeout(() => {
      // Check if user is still on the same page
      if (window.location.href === document.URL) {
        processPage();
      } else {
        console.log('Page skipped: user navigated away');
      }
      isProcessingScheduled = false;
    }, 5000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', schedulePageProcessing);
  } else {
    schedulePageProcessing();
  }
})();