// Service worker for background processing
const BACKEND_URL = 'http://localhost:8000';
const STORAGE_KEY = 'localWebMemory';

// Initialize default settings and probe current tab
chrome.runtime.onInstalled.addListener(async () => {
  // Only set defaults if no existing settings exist
  const existing = await chrome.storage.local.get(STORAGE_KEY);
  if (!existing[STORAGE_KEY]) {
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
    console.log('✅ SW: New Tab extension installed with default settings');
  } else {
    console.log('✅ SW: New Tab extension installed, preserving existing settings');
  }
  
  // Probe the currently active tab on startup
  await probeCurrentActiveTab();
});

// Probe the currently active tab
async function probeCurrentActiveTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('chrome-extension://')) {
      console.log('🔍 SW: Extension startup: probing current tab:', tab.url);
      await proactivelyProbeTab(tab.url);
    }
  } catch (error) {
    console.warn('⚠️ SW: Error probing current tab on startup:', error);
  }
}

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('🔄 SW: Received message:', request.type);
  
  // Handle each message type with proper async pattern
  if (request.type === 'GET_STATUS') {
    getIndexingStatus()
      .then(status => {
        console.log('📤 SW: Sending status response:', status);
        sendResponse(status);
      })
      .catch(error => {
        console.error('❌ SW: GET_STATUS error:', error);
        sendResponse({ error: error.message });
      });
    return true; // Keep message channel open
    
  } else if (request.type === 'GET_CACHED_PROBE') {
    handleGetCachedProbeSync(request.url)
      .then(result => {
        console.log('📤 SW: Sending cached probe response:', result);
        sendResponse(result);
      })
      .catch(error => {
        console.error('❌ SW: GET_CACHED_PROBE error:', error);
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep message channel open
    
  } else if (request.type === 'GET_PAGE_STATUS') {
    getPageStatus(request.url)
      .then(status => {
        console.log('Sending page status response:', status);
        sendResponse(status);
      })
      .catch(error => {
        console.error('GET_PAGE_STATUS error:', error);
        sendResponse({ error: error.message });
      });
    return true; // Keep message channel open
    
  } else if (request.type === 'INDEX_PAGE') {
    console.log('INDEX_PAGE request received');
    handlePageIndexing(request.data, sender.tab, sendResponse);
    return true; // Keep message channel open
    
  } else if (request.type === 'PROBE_PAGE') {
    handlePageProbe(request.url)
      .then(result => {
        console.log('📤 SW: Sending probe response:', result);
        sendResponse(result);
      })
      .catch(error => {
        console.error('❌ SW: PROBE_PAGE error:', error);
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep message channel open
    
  } else if (request.type === 'SEARCH') {
    handleSearch(request.query)
      .then(result => {
        console.log('Sending search response:', result);
        sendResponse(result);
      })
      .catch(error => {
        console.error('SEARCH error:', error);
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep message channel open
    
  } else if (request.type === 'INVALIDATE_CACHE') {
    console.log('🗑️ SW: Received INVALIDATE_CACHE for:', request.url);
    invalidatePageCache(request.url)
      .then(() => {
        console.log('✅ SW: Cache invalidated successfully');
        sendResponse({ success: true });
      })
      .catch(error => {
        console.error('❌ SW: Failed to invalidate cache:', error);
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep message channel open
    
  } else if (request.type === 'PING') {
    console.log('🏓 SW: Ping received, responding immediately');
    sendResponse({ success: true, message: 'Service worker alive', timestamp: Date.now() });
    return false; // Synchronous response
    
  } else {
    console.warn('⚠️ SW: Unknown message type:', request.type);
    sendResponse({ success: false, error: 'Unknown request type' });
    return false; // Synchronous response
  }
});

// Handle page probe to check if already indexed
async function handlePageProbe(url) {
  try {
    
    // Check if indexing is enabled
    const settings = await getSettings();
    if (!settings.indexingEnabled) {
      return { success: false, error: 'Indexing disabled' };
    }
    
    // Check if domain is excluded
    const domain = new URL(url).hostname;
    const isExcluded = settings.excludedDomains.some(excludedDomain => {
      return domain === excludedDomain || 
             (domain.endsWith('.' + excludedDomain) && domain.length > excludedDomain.length);
    });
    
    if (isExcluded) {
      return { success: false, error: 'Domain excluded' };
    }
    
    // First check cached probe result for instant response
    const cachedResult = await getCachedProbeResult(url);
    if (cachedResult) {
      return { 
        success: true,
        indexed: cachedResult.indexed,
        pageId: cachedResult.page_id,
        needsReindex: cachedResult.needs_reindex,
        lastUpdated: cachedResult.last_updated,
        fromCache: true
      };
    }
    
    // No cache hit, call probe API
    const response = await fetch(`${BACKEND_URL}/probe?url=${encodeURIComponent(url)}`);
    
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    
    const result = await response.json();
    
    // Cache the probe result
    await cacheProbeResult(url, result);
    
    return { 
      success: true,
      indexed: result.indexed,
      pageId: result.page_id,
      needsReindex: result.needs_reindex,
      lastUpdated: result.last_updated,
      fromCache: false
    };
    
  } catch (error) {
    console.error('Error probing page:', error);
    return { 
      success: false, 
      error: error.message 
    };
  }
}

// Handle page indexing
async function handlePageIndexing(pageData, tab, sendResponse) {
  try {
    console.log('Indexing page:', pageData.url);
    
    // Check if indexing is enabled
    const settings = await getSettings();
    if (!settings.indexingEnabled) {
      sendResponse({ success: false, error: 'Indexing disabled' });
      return;
    }
    
    // Check if domain is excluded (using suffix matching)
    const domain = new URL(pageData.url).hostname;
    const isExcluded = settings.excludedDomains.some(excludedDomain => {
      // Exact match or suffix match (for subdomains)
      return domain === excludedDomain || 
             (domain.endsWith('.' + excludedDomain) && domain.length > excludedDomain.length);
    });
    
    if (isExcluded) {
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
    console.log('Page indexed successfully:', result.status);
    
    // Store the indexing status for this URL
    await storePageStatus(pageData.url, result.status);
    
    // Update probe cache with new indexed status
    const newProbeResult = {
      indexed: true,
      page_id: result.id,
      needs_reindex: false,
      last_updated: new Date().toISOString()
    };
    await cacheProbeResult(pageData.url, newProbeResult);
    
    // Update statistics only for new pages
    if (result.status === 'indexed') {
      await updateStatistics(pageData.url);
    }
    
    // Update status to idle
    await updateStatus('idle');
    
    // Update extension badge based on status
    if (result.status === 'already_indexed') {
      updateBadge('✓', '#3b82f6'); // Blue for already indexed
    } else {
      updateBadge('✓', '#4CAF50'); // Green for newly indexed
    }
    setTimeout(() => updateBadge('', ''), 3000);
    
    sendResponse({ 
      success: true, 
      message: result.message,
      pageId: result.id,
      status: result.status
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
async function handleSearch(query) {
  try {
    // Use the new unified search endpoint with server-controlled logic
    const response = await fetch(`${BACKEND_URL}/search?q=${encodeURIComponent(query)}`);
    
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

// Store page indexing status
async function storePageStatus(url, status) {
  const data = await chrome.storage.local.get('pageStatuses');
  const pageStatuses = data.pageStatuses || {};
  
  // Store with timestamp to expire old entries
  pageStatuses[url] = {
    status: status,
    timestamp: Date.now()
  };
  
  // Clean up old entries (older than 24 hours)
  const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
  Object.keys(pageStatuses).forEach(pageUrl => {
    if (pageStatuses[pageUrl].timestamp < oneDayAgo) {
      delete pageStatuses[pageUrl];
    }
  });
  
  await chrome.storage.local.set({ pageStatuses });
}

// Cache probe result for reuse
async function cacheProbeResult(url, probeResult) {
  const data = await chrome.storage.local.get('probeCache');
  const probeCache = data.probeCache || {};
  
  // Store probe result with timestamp
  probeCache[url] = {
    result: probeResult,
    timestamp: Date.now()
  };
  
  // Clean up old entries (older than 1 hour)
  const oneHourAgo = Date.now() - (60 * 60 * 1000);
  Object.keys(probeCache).forEach(pageUrl => {
    if (probeCache[pageUrl].timestamp < oneHourAgo) {
      delete probeCache[pageUrl];
    }
  });
  
  await chrome.storage.local.set({ probeCache });
}

// Get cached probe result
async function getCachedProbeResult(url) {
  const data = await chrome.storage.local.get('probeCache');
  const probeCache = data.probeCache || {};
  const cachedResult = probeCache[url];
  
  // Return cached result if recent (within 5 minutes)
  if (cachedResult && (Date.now() - cachedResult.timestamp) < (5 * 60 * 1000)) {
    return cachedResult.result;
  }
  
  return null;
}

// Get page indexing status (updated to use probe cache)
async function getPageStatus(url) {
  // First check probe cache
  const cachedProbe = await getCachedProbeResult(url);
  if (cachedProbe) {
    if (cachedProbe.indexed && !cachedProbe.needs_reindex) {
      return 'indexed';
    } else if (cachedProbe.indexed && cachedProbe.needs_reindex) {
      return 'needs_reindex';
    } else {
      return 'not_indexed';
    }
  }
  
  // Fallback to old storage method
  const data = await chrome.storage.local.get('pageStatuses');
  const pageStatuses = data.pageStatuses || {};
  const pageStatus = pageStatuses[url];
  
  // Return status if recent (within 24 hours)
  if (pageStatus && (Date.now() - pageStatus.timestamp) < (24 * 60 * 60 * 1000)) {
    return pageStatus.status;
  }
  
  return null;
}

// Get indexing status (settings only, no health check)
async function getIndexingStatus() {
  const settings = await getSettings();
  
  // Return only extension settings - no backend health check
  return {
    indexingEnabled: settings.indexingEnabled,
    indexingStatus: settings.indexingStatus,
    totalPagesIndexed: settings.totalPagesIndexed || 0,
    lastIndexedUrl: settings.lastIndexedUrl,
    lastIndexedTime: settings.lastIndexedTime
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

// Listen for tab updates to proactively probe pages
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  // Only process when page completes loading
  if (changeInfo.status === 'complete' && tab.url) {
    // Skip chrome:// and extension pages
    if (tab.url.startsWith('chrome://') || 
        tab.url.startsWith('chrome-extension://')) {
      return;
    }
    
    console.log('🔍 SW: Tab loaded, proactively probing:', tab.url);
    
    // Proactively probe the page to cache the result
    await proactivelyProbeTab(tab.url);
  }
});

// Listen for tab activation to probe the newly active tab
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('chrome-extension://')) {
      console.log('🔍 SW: Tab activated, proactively probing:', tab.url);
      await proactivelyProbeTab(tab.url);
    }
  } catch (error) {
    console.warn('⚠️ SW: Error probing activated tab:', error);
  }
});

// Handle request for cached probe result (instant response for popup) - Sync version
async function handleGetCachedProbeSync(url) {
  try {
    // Check if indexing is enabled
    const settings = await getSettings();
    if (!settings.indexingEnabled) {
      return { success: false, error: 'Indexing disabled' };
    }
    
    // Check if domain is excluded
    const domain = new URL(url).hostname;
    const isExcluded = settings.excludedDomains.some(excludedDomain => {
      return domain === excludedDomain || 
             (domain.endsWith('.' + excludedDomain) && domain.length > excludedDomain.length);
    });
    
    if (isExcluded) {
      return { success: false, error: 'Domain excluded' };
    }
    
    // Only check cache, don't trigger new probe
    const cachedResult = await getCachedProbeResult(url);
    if (cachedResult) {
      return { 
        success: true,
        indexed: cachedResult.indexed,
        pageId: cachedResult.page_id,
        needsReindex: cachedResult.needs_reindex,
        lastUpdated: cachedResult.last_updated,
        fromCache: true,
        instant: true
      };
    }
    
    // No cache available - trigger proactive probe for next time but return default state
    console.log('No cache for popup, triggering proactive probe for:', url);
    proactivelyProbeTab(url); // Don't await - do in background
    
    // Return default state immediately
    return { 
      success: true,
      indexed: false,
      pageId: null,
      needsReindex: false,
      lastUpdated: null,
      fromCache: false,
      instant: true,
      defaultState: true
    };
    
  } catch (error) {
    console.error('Error getting cached probe:', error);
    return { 
      success: false, 
      error: error.message,
      instant: true
    };
  }
}

// Invalidate cache for a specific page (when deleted)
async function invalidatePageCache(url) {
  try {
    console.log('Invalidating cache for:', url);
    
    // Remove from probe cache
    const probeData = await chrome.storage.local.get('probeCache');
    const probeCache = probeData.probeCache || {};
    if (probeCache[url]) {
      delete probeCache[url];
      await chrome.storage.local.set({ probeCache });
    }
    
    // Remove from page statuses
    const statusData = await chrome.storage.local.get('pageStatuses');
    const pageStatuses = statusData.pageStatuses || {};
    if (pageStatuses[url]) {
      delete pageStatuses[url];
      await chrome.storage.local.set({ pageStatuses });
    }
    
    console.log('Page cache invalidated successfully');
  } catch (error) {
    console.error('Error invalidating page cache:', error);
    throw error;
  }
}

// Proactively probe a tab's URL to cache the result
async function proactivelyProbeTab(url) {
  try {
    // Check if indexing is enabled
    const settings = await getSettings();
    if (!settings.indexingEnabled) {
      return;
    }
    
    // Check if domain is excluded
    const domain = new URL(url).hostname;
    const isExcluded = settings.excludedDomains.some(excludedDomain => {
      return domain === excludedDomain || 
             (domain.endsWith('.' + excludedDomain) && domain.length > excludedDomain.length);
    });
    
    if (isExcluded) {
      return;
    }
    
    // Check if we already have fresh cache (within 5 minutes)
    const cachedResult = await getCachedProbeResult(url);
    if (cachedResult) {
      console.log('Using cached probe result for:', url);
      return;
    }
    
    console.log('Proactively probing:', url);
    
    // Call probe API and cache the result
    const response = await fetch(`${BACKEND_URL}/probe?url=${encodeURIComponent(url)}`);
    
    if (!response.ok) {
      console.warn(`Proactive probe failed for ${url}: ${response.status}`);
      return;
    }
    
    const result = await response.json();
    
    // Cache the probe result for popup to use
    await cacheProbeResult(url, result);
    
    console.log('Cached probe result for:', url);
    
  } catch (error) {
    console.warn('Error in proactive probe:', error);
  }
}

// Export functions for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    handlePageIndexing,
    handleSearch,
    getSettings,
    updateSettings
  };
}