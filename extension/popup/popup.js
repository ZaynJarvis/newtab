// Popup script for status display and controls
document.addEventListener('DOMContentLoaded', () => {
  // Get DOM elements
  const indexingToggle = document.getElementById('indexingToggle');
  const toggleLabel = document.getElementById('toggleLabel');
  const backendStatus = document.getElementById('backendStatus');
  const pagesIndexed = document.getElementById('pagesIndexed');
  const indexingStatus = document.getElementById('indexingStatus');
  const lastIndexedInfo = document.getElementById('lastIndexedInfo');
  const openNewTabBtn = document.getElementById('openNewTab');
  const openSettingsBtn = document.getElementById('openSettings');
  
  // Load current status
  loadStatus();
  
  // Set up event listeners
  indexingToggle.addEventListener('change', handleToggleChange);
  openNewTabBtn.addEventListener('click', openNewTab);
  openSettingsBtn.addEventListener('click', openSettings);
  
  // Load status from service worker
  async function loadStatus() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
      
      // Update toggle
      indexingToggle.checked = response.indexingEnabled;
      toggleLabel.textContent = response.indexingEnabled ? 'Indexing Enabled' : 'Indexing Disabled';
      
      // Update backend status
      backendStatus.textContent = capitalizeFirst(response.backendStatus);
      backendStatus.className = 'value ' + response.backendStatus;
      
      // Update pages indexed
      pagesIndexed.textContent = response.totalPagesIndexed.toLocaleString();
      
      // Update indexing status
      const statusText = response.indexingStatus === 'indexing' ? 'Indexing...' : capitalizeFirst(response.indexingStatus);
      indexingStatus.textContent = statusText;
      indexingStatus.className = 'value ' + response.indexingStatus;
      
      // Update last indexed info
      if (response.lastIndexedUrl) {
        const timeAgo = response.lastIndexedTime ? formatTimeAgo(new Date(response.lastIndexedTime)) : 'Unknown';
        lastIndexedInfo.innerHTML = `
          <div class="url" title="${response.lastIndexedUrl}">${truncateUrl(response.lastIndexedUrl)}</div>
          <div class="time">${timeAgo}</div>
        `;
      } else {
        lastIndexedInfo.innerHTML = '<p class="no-data">No pages indexed yet</p>';
      }
      
    } catch (error) {
      console.error('Error loading status:', error);
      backendStatus.textContent = 'Error';
      backendStatus.className = 'value offline';
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
    
    // Show feedback
    if (!enabled) {
      indexingStatus.textContent = 'Disabled';
      indexingStatus.className = 'value';
    }
  }
  
  // Open new tab for search
  function openNewTab() {
    chrome.tabs.create({ url: 'chrome://newtab' });
    window.close();
  }
  
  // Open settings (will be in new tab)
  function openSettings() {
    chrome.tabs.create({ url: 'chrome://newtab#settings' });
    window.close();
  }
  
  // Utility functions
  function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
  
  function truncateUrl(url) {
    if (!url) return '';
    try {
      const urlObj = new URL(url);
      const path = urlObj.pathname + urlObj.search;
      const maxLength = 40;
      
      if (url.length <= maxLength) {
        return url;
      }
      
      const domain = urlObj.hostname;
      if (domain.length >= maxLength - 3) {
        return domain.substring(0, maxLength - 3) + '...';
      }
      
      const remainingLength = maxLength - domain.length - 3;
      if (path.length > remainingLength) {
        return domain + path.substring(0, remainingLength) + '...';
      }
      
      return domain + path;
    } catch (e) {
      return url.substring(0, 40) + '...';
    }
  }
  
  function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) {
      return 'Just now';
    }
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
      return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
    }
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
      return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    }
    
    const days = Math.floor(hours / 24);
    return `${days} day${days === 1 ? '' : 's'} ago`;
  }
  
  // Refresh status every 5 seconds if popup stays open
  setInterval(loadStatus, 5000);
});