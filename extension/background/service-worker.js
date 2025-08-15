// Service worker for background processing
const BACKEND_URL = 'http://localhost:8000';
const STORAGE_KEY = 'localWebMemory';

// Initialize default settings
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    [STORAGE_KEY]: {
      excludedDomains: [],
      indexingEnabled: true,
      totalPagesIndexed: 0,
      lastIndexedUrl: null,
      lastIndexedTime: null,
      indexingStatus: 'idle'
    }
  });
  console.log('Local Web Memory extension installed');
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'INDEX_PAGE') {
    handlePageIndexing(request.data, sender.tab, sendResponse);
    return true; // Keep message channel open for async response
  } else if (request.type === 'GET_STATUS') {
    getIndexingStatus().then(sendResponse);
    return true;
  } else if (request.type === 'SEARCH') {
    handleSearch(request.query, request.searchType).then(sendResponse);
    return true;
  }
});

// Handle page indexing
async function handlePageIndexing(pageData, tab, sendResponse) {
  try {
    // Check if indexing is enabled
    const settings = await getSettings();
    if (!settings.indexingEnabled) {
      sendResponse({ success: false, error: 'Indexing disabled' });
      return;
    }
    
    // Check if domain is excluded
    const domain = new URL(pageData.url).hostname;
    if (settings.excludedDomains.includes(domain)) {
      sendResponse({ success: false, error: 'Domain excluded' });
      return;
    }
    
    // Update status to indexing
    await updateStatus('indexing', pageData.url);
    
    // Send to backend API
    const response = await fetch(`${BACKEND_URL}/index`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: pageData.url,
        title: pageData.title,
        content: pageData.content,
        favicon_url: pageData.favicon_url
      })
    });
    
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    
    const result = await response.json();
    
    // Update statistics
    await updateStatistics(pageData.url);
    
    // Update status to idle
    await updateStatus('idle');
    
    // Update extension badge
    updateBadge('✓', '#4CAF50');
    setTimeout(() => updateBadge('', ''), 3000);
    
    sendResponse({ 
      success: true, 
      message: 'Page indexed successfully',
      pageId: result.id 
    });
    
  } catch (error) {
    console.error('Error indexing page:', error);
    await updateStatus('error', null, error.message);
    
    // Update badge to show error
    updateBadge('!', '#F44336');
    setTimeout(() => updateBadge('', ''), 3000);
    
    sendResponse({ 
      success: false, 
      error: error.message 
    });
  }
}

// Handle search requests
async function handleSearch(query, searchType = 'combined') {
  try {
    // Use the new combined search endpoint which does weighted search (60% keyword, 40% semantic)
    const endpoint = 'search/combined';
    const response = await fetch(`${BACKEND_URL}/${endpoint}?query=${encodeURIComponent(query)}&limit=20`);
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.status}`);
    }
    
    const data = await response.json();
    return { success: true, results: data.results || [] };
    
  } catch (error) {
    console.error('Search error:', error);
    return { success: false, error: error.message, results: [] };
  }
}

// Get current settings
async function getSettings() {
  const data = await chrome.storage.local.get(STORAGE_KEY);
  return data[STORAGE_KEY] || {};
}

// Update settings
async function updateSettings(updates) {
  const current = await getSettings();
  const updated = { ...current, ...updates };
  await chrome.storage.local.set({ [STORAGE_KEY]: updated });
  return updated;
}

// Update indexing status
async function updateStatus(status, url = null, error = null) {
  const updates = {
    indexingStatus: status,
    lastIndexedUrl: url || (await getSettings()).lastIndexedUrl,
    lastIndexedTime: status === 'idle' ? new Date().toISOString() : null
  };
  
  if (error) {
    updates.lastError = error;
  }
  
  return updateSettings(updates);
}

// Update statistics
async function updateStatistics(url) {
  const settings = await getSettings();
  return updateSettings({
    totalPagesIndexed: (settings.totalPagesIndexed || 0) + 1,
    lastIndexedUrl: url,
    lastIndexedTime: new Date().toISOString()
  });
}

// Get indexing status
async function getIndexingStatus() {
  const settings = await getSettings();
  
  // Also check backend health
  let backendStatus = 'unknown';
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    backendStatus = response.ok ? 'healthy' : 'unhealthy';
  } catch (error) {
    backendStatus = 'offline';
  }
  
  return {
    indexingEnabled: settings.indexingEnabled,
    indexingStatus: settings.indexingStatus,
    totalPagesIndexed: settings.totalPagesIndexed || 0,
    lastIndexedUrl: settings.lastIndexedUrl,
    lastIndexedTime: settings.lastIndexedTime,
    backendStatus: backendStatus
  };
}

// Update extension badge
function updateBadge(text, color) {
  if (text) {
    chrome.action.setBadgeText({ text });
    chrome.action.setBadgeBackgroundColor({ color });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

// Handle extension icon click (for browsers that don't support popup)
chrome.action.onClicked.addListener((tab) => {
  chrome.tabs.create({ url: 'chrome://newtab' });
});

// Listen for tab updates to potentially re-index
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only process when page completes loading
  if (changeInfo.status === 'complete' && tab.url) {
    // Skip chrome:// and extension pages
    if (tab.url.startsWith('chrome://') || 
        tab.url.startsWith('chrome-extension://')) {
      return;
    }
    
    // Content script will handle indexing
    console.log('Tab loaded:', tab.url);
  }
});

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    handlePageIndexing,
    handleSearch,
    getSettings,
    updateSettings
  };
}