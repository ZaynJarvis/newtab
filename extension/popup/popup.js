// Popup script for status display and controls

// Real-time connection to background script for status updates
let statusUpdatePort = null;

// Current page data for delete functionality
let currentPageData = {
  url: null,
  pageId: null,
  indexed: false
};

// Utility function to send messages with timeout to prevent blocking
function sendMessageWithTimeout(message, timeoutMs = 2000) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error(`Message timeout after ${timeoutMs}ms`));
    }, timeoutMs);
    
    chrome.runtime.sendMessage(message, (response) => {
      clearTimeout(timeout);
      
      // Check for runtime errors
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      
      resolve(response);
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // Get DOM elements
  const indexingToggle = document.getElementById('indexingToggle');
  const toggleLabel = document.getElementById('toggleLabel');
  const indexingStatus = document.getElementById('indexingStatus');
  
  // Set up real-time status updates
  setupStatusUpdateConnection();
  
  // Load current status
  loadStatus();
  
  // Set up event listeners
  indexingToggle.addEventListener('change', handleToggleChange);
  
  // Set up delete button
  const deletePageBtn = document.getElementById('deletePageBtn');
  if (deletePageBtn) {
    deletePageBtn.addEventListener('click', handleDeletePage);
  }
  
  // Load status from service worker and backend
  async function loadStatus() {
    try {
      const response = await sendMessageWithTimeout({ type: 'GET_STATUS' }, 3000); // Increased timeout for health check
      
      // Update toggle
      indexingToggle.checked = response.indexingEnabled;
      toggleLabel.textContent = response.indexingEnabled ? 'Indexing Enabled' : 'Indexing Disabled';
      
      // Update indexing status (probe API will determine backend health)
      await updateIndexingStatus(response.indexingEnabled);
      
      
    } catch (error) {
      console.error('Error loading status:', error);
      
      // Show fallback state - assume enabled by default (better UX)
      indexingToggle.checked = true; // Default to enabled when communication fails
      toggleLabel.textContent = 'Indexing Enabled';
      
      // Show minimal "Ready" status instead of "Failed" to avoid confusion
      const statusElement = document.getElementById('indexingStatus');
      statusElement.textContent = 'Ready';
      statusElement.className = 'status-value healthy';
      
      console.warn('Using fallback UI state due to communication error');
    }
  }
  
  
  // Handle indexing toggle change
  async function handleToggleChange(e) {
    const enabled = e.target.checked;
    toggleLabel.textContent = enabled ? 'Indexing Enabled' : 'Indexing Disabled';
    
    // Update settings in storage
    const storage = await chrome.storage.local.get('localWebMemory');
    const settings = storage.localWebMemory || {};
    settings.indexingEnabled = enabled;
    await chrome.storage.local.set({ localWebMemory: settings });
    
    // Reload status when indexing is toggled
    setTimeout(() => loadStatus(), 100);
  }
  
  // Update indexing status display (probe API determines everything)
  async function updateIndexingStatus(indexingEnabled) {
    const statusElement = indexingStatus;
    let displayText = '';
    let statusClass = '';
    
    if (!indexingEnabled) {
      displayText = 'Disabled';
      statusClass = 'status-value disabled';
    } else {
      // Check current page status using probe API for immediate results
      try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('chrome-extension://')) {
          // Request cached probe result for instant response with timeout
          try {
            const probeResponse = await sendMessageWithTimeout({
              type: 'GET_CACHED_PROBE',
              url: tab.url
            }, 1000); // 1 second timeout
            
            if (probeResponse?.success) {
              if (probeResponse.indexed && !probeResponse.needsReindex) {
                displayText = 'Indexed';
                statusClass = 'status-value healthy';
              } else if (probeResponse.indexed && probeResponse.needsReindex) {
                displayText = 'Needs Update';
                statusClass = 'status-value indexing';
              } else {
                displayText = 'Ready';
                statusClass = 'status-value healthy';
              }
              
              // Cache usage handled silently
            } else {
              displayText = 'Ready';
              statusClass = 'status-value healthy';
            }
          } catch (probeError) {
            console.warn('Cached probe request failed:', probeError);
            
            // Determine status based on probe API failure type
            if (probeError.message.includes('timeout') || probeError.message.includes('port closed')) {
              // Communication issue with extension - show Ready (assume backend is fine)
              displayText = 'Ready';
              statusClass = 'status-value healthy';
            } else {
              // Unknown error - show Ready as fallback
              displayText = 'Ready';
              statusClass = 'status-value healthy';
            }
          }
        } else {
          displayText = 'Ready';
          statusClass = 'status-value healthy';
        }
      } catch (error) {
        console.error('Error checking page status:', error);
        // Always show Ready as fallback when probe fails
        displayText = 'Ready';
        statusClass = 'status-value healthy';
      }
    }
    
    statusElement.textContent = displayText;
    statusElement.className = statusClass;
  }
  

  // Utility functions
  function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
  
  
  
  // Setup real-time status update connection
  function setupStatusUpdateConnection() {
    try {
      // Create long-lived connection for real-time updates
      statusUpdatePort = chrome.runtime.connect({ name: 'popup-status-updates' });
      
      // Listen for status updates from background script
      statusUpdatePort.onMessage.addListener(async (message) => {
        console.log('📨 Popup: Received status update:', message);
        
        if (message.type === 'STATUS_UPDATE') {
          // Only update if this is for the current active tab
          try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tab && tab.url === message.url) {
              // Update popup status immediately (like React useState)
              updatePopupStatus(message.data, message.url);
            }
          } catch (error) {
            console.warn('Error checking current tab for status update:', error);
          }
        }
      });
      
      // Handle connection disconnect
      statusUpdatePort.onDisconnect.addListener(() => {
        console.log('🔌 Popup: Status update connection disconnected');
        statusUpdatePort = null;
      });
      
      // Request current status for the active tab
      requestCurrentTabStatus();
      
    } catch (error) {
      console.error('❌ Popup: Failed to setup status connection:', error);
    }
  }
  
  // Request current tab status via the connection
  async function requestCurrentTabStatus() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.url && statusUpdatePort) {
        statusUpdatePort.postMessage({
          type: 'REQUEST_TAB_STATUS',
          url: tab.url
        });
      }
    } catch (error) {
      console.error('❌ Popup: Failed to request tab status:', error);
    }
  }
  
  // Update popup status immediately (like React useState)
  function updatePopupStatus(statusData, url = null) {
    const statusElement = document.getElementById('indexingStatus');
    const deleteBtn = document.getElementById('deletePageBtn');
    if (!statusElement) return;
    
    let displayText = 'Ready';
    let statusClass = 'status-value healthy';
    
    // Update current page data
    if (url) currentPageData.url = url;
    currentPageData.indexed = statusData.indexed || false;
    currentPageData.pageId = statusData.pageId || null;
    
    if (statusData.indexed && !statusData.needsReindex) {
      displayText = 'Indexed';
      statusClass = 'status-value healthy';
    } else if (statusData.indexed && statusData.needsReindex) {
      displayText = 'Needs Update';
      statusClass = 'status-value indexing';
    } else if (statusData.indexing) {
      displayText = 'Indexing...';
      statusClass = 'status-value indexing';
    }
    
    statusElement.textContent = displayText;
    statusElement.className = statusClass;
    
    // Show/hide delete button based on indexed status
    if (deleteBtn) {
      if (currentPageData.indexed && currentPageData.pageId) {
        deleteBtn.style.display = 'flex';
      } else {
        deleteBtn.style.display = 'none';
      }
    }
    
    console.log('✅ Popup: Status updated to:', displayText, 'Delete button:', currentPageData.indexed ? 'visible' : 'hidden');
  }
  
  // Handle delete page button click
  async function handleDeletePage() {
    if (!currentPageData.pageId || !currentPageData.indexed) {
      console.warn('No page to delete or page not indexed');
      return;
    }
    
    try {
      console.log('Deleting page with ID:', currentPageData.pageId);
      
      // Use same API as newtab page
      const response = await fetch(`http://localhost:8000/pages/${currentPageData.pageId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        console.log('Page deleted successfully, ID:', currentPageData.pageId);
        
        // Invalidate extension cache for this page and update badge
        if (currentPageData.url) {
          try {
            await chrome.runtime.sendMessage({
              type: 'INVALIDATE_CACHE',
              url: currentPageData.url
            });
            console.log('Extension cache invalidated for:', currentPageData.url);
            
            // Trigger badge update for current tab
            await chrome.runtime.sendMessage({
              type: 'UPDATE_BADGE',
              url: currentPageData.url
            });
            console.log('Badge update requested for:', currentPageData.url);
          } catch (error) {
            console.warn('Failed to invalidate extension cache or update badge:', error);
          }
        }
        
        // Update UI immediately
        currentPageData.indexed = false;
        currentPageData.pageId = null;
        updatePopupStatus({ indexed: false, needsReindex: false, indexing: false });
        
        // Show success feedback
        const statusElement = document.getElementById('indexingStatus');
        const originalText = statusElement.textContent;
        const originalClass = statusElement.className;
        
        statusElement.textContent = 'Deleted';
        statusElement.className = 'status-value';
        statusElement.style.color = '#dc2626';
        
        setTimeout(() => {
          statusElement.textContent = originalText;
          statusElement.className = originalClass;
          statusElement.style.color = '';
        }, 2000);
        
      } else {
        const errorText = await response.text();
        console.error('Delete failed:', response.status, errorText);
        alert('Failed to delete page');
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete page: ' + error.message);
    }
  }
  
  // Cleanup connection when popup closes
  window.addEventListener('beforeunload', () => {
    if (statusUpdatePort) {
      statusUpdatePort.disconnect();
    }
  });
  
});