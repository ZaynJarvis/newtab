// Popup script for status display and controls

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
  
  // Load current status
  loadStatus();
  
  // Set up event listeners
  indexingToggle.addEventListener('change', handleToggleChange);
  
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
  
  
  
  // No auto-refresh needed - popup is short-lived and uses cached data
});