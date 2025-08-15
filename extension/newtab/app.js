// New tab page app
const BACKEND_URL = 'http://localhost:8000';
// Removed currentSearchType - server now controls all search logic
let excludedDomains = [];
let selectedIndex = -1;
let searchResults = [];

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
  initializeEventListeners();
  loadSettings();
  loadStatistics();
  checkBackendStatus();
  
  // Check for settings hash in URL
  if (window.location.hash === '#settings') {
    openSettings();
  }
  
  // Robust focus implementation to handle Chrome's security restrictions
  focusSearchInput();
});

// Robust focus implementation with multiple strategies
function focusSearchInput() {
  const searchInput = document.getElementById('searchInput');
  if (!searchInput) return;

  let focusAttempts = 0;
  const maxAttempts = 10;
  const focusTimeouts = [0, 10, 50, 100, 200, 300, 500, 750, 1000, 1500];

  function attemptFocus() {
    if (focusAttempts >= maxAttempts) return;
    
    try {
      // Only attempt focus if the input is not already focused
      if (document.activeElement !== searchInput) {
        searchInput.focus();
        
        // Verify focus was successful
        if (document.activeElement === searchInput) {
          console.log(`Search input focused successfully on attempt ${focusAttempts + 1}`);
          return; // Success, stop attempting
        }
      } else {
        // Already focused
        return;
      }
    } catch (error) {
      console.warn(`Focus attempt ${focusAttempts + 1} failed:`, error);
    }
    
    focusAttempts++;
    
    // Schedule next attempt if we haven't exceeded max attempts
    if (focusAttempts < maxAttempts) {
      setTimeout(attemptFocus, focusTimeouts[focusAttempts]);
    }
  }

  // Start first attempt immediately
  attemptFocus();

  // Use Page Visibility API to detect when tab becomes active
  function handleVisibilityChange() {
    if (!document.hidden && document.visibilityState === 'visible') {
      // Reset attempts counter when tab becomes visible
      focusAttempts = 0;
      setTimeout(() => {
        if (document.activeElement !== searchInput && !isSettingsOpen()) {
          attemptFocus();
        }
      }, 50);
    }
  }

  // Listen for visibility changes
  document.addEventListener('visibilitychange', handleVisibilityChange);

  // Also listen for window focus events as a fallback
  window.addEventListener('focus', () => {
    setTimeout(() => {
      if (document.activeElement !== searchInput && !isSettingsOpen()) {
        focusAttempts = 0;
        attemptFocus();
      }
    }, 50);
  });

  // Handle page show event (when navigating back to the tab)
  window.addEventListener('pageshow', () => {
    setTimeout(() => {
      if (document.activeElement !== searchInput && !isSettingsOpen()) {
        focusAttempts = 0;
        attemptFocus();
      }
    }, 50);
  });

  // Handle browser back/forward navigation
  window.addEventListener('popstate', () => {
    setTimeout(() => {
      if (document.activeElement !== searchInput && !isSettingsOpen()) {
        focusAttempts = 0;
        attemptFocus();
      }
    }, 50);
  });

  // Additional safety net: check focus periodically if document becomes active
  let focusCheckInterval;
  
  function startFocusCheck() {
    if (focusCheckInterval) clearInterval(focusCheckInterval);
    
    focusCheckInterval = setInterval(() => {
      // Only check if document is visible and settings are not open
      if (!document.hidden && 
          document.visibilityState === 'visible' && 
          !isSettingsOpen() && 
          document.activeElement !== searchInput &&
          document.activeElement.tagName !== 'INPUT' && 
          document.activeElement.tagName !== 'TEXTAREA') {
        
        focusAttempts = 0;
        attemptFocus();
        clearInterval(focusCheckInterval); // Stop checking once we attempt to focus
      }
    }, 1000);
    
    // Clear interval after 10 seconds to avoid running indefinitely
    setTimeout(() => {
      if (focusCheckInterval) {
        clearInterval(focusCheckInterval);
        focusCheckInterval = null;
      }
    }, 10000);
  }

  // Start focus checking when page becomes visible
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && document.visibilityState === 'visible') {
      startFocusCheck();
    } else if (focusCheckInterval) {
      clearInterval(focusCheckInterval);
      focusCheckInterval = null;
    }
  });
}

// Helper function to check if settings panel is open
function isSettingsOpen() {
  const settingsView = document.getElementById('settingsView');
  return settingsView && settingsView.classList.contains('open');
}

// Event Listeners
function initializeEventListeners() {
  // Search
  const searchInput = document.getElementById('searchInput');
  
  searchInput.addEventListener('input', debounce(handleSearch, 300));
  searchInput.addEventListener('keydown', handleKeyNavigation);
  
  // Focus search input when clicking on empty areas of the page
  document.addEventListener('click', (e) => {
    // Only refocus if not clicking on interactive elements and settings are closed
    const isInteractiveElement = e.target.matches('button, a, input, textarea, select, [role="button"], [tabindex]') ||
                                 e.target.closest('button, a, input, textarea, select, [role="button"], [tabindex]');
    
    if (!isInteractiveElement && !isSettingsOpen()) {
      setTimeout(() => {
        if (!isSettingsOpen() && document.activeElement !== searchInput) {
          searchInput.focus();
        }
      }, 10);
    }
  });
  
  // Focus search input on key press (except when typing in other inputs)
  document.addEventListener('keydown', (e) => {
    // Don't interfere if user is typing in an input field or settings are open
    if (document.activeElement.tagName === 'INPUT' || 
        document.activeElement.tagName === 'TEXTAREA' ||
        isSettingsOpen()) {
      return;
    }
    
    // Focus search input for alphanumeric keys, space, and backspace
    if ((e.key.length === 1 && e.key.match(/[\w\s]/)) || e.key === 'Backspace') {
      searchInput.focus();
      
      // For backspace, also clear the last character if search has content
      if (e.key === 'Backspace' && searchInput.value.length > 0) {
        e.preventDefault();
        searchInput.value = searchInput.value.slice(0, -1);
        handleSearch(); // Trigger search with updated value
      }
    }
  });
  
  // Settings
  document.getElementById('settingsToggle').addEventListener('click', openSettings);
  document.getElementById('closeSettings').addEventListener('click', closeSettings);
  document.getElementById('enableIndexing').addEventListener('change', handleIndexingToggle);
  document.getElementById('showMetadata').addEventListener('change', handleMetadataToggle);
  document.getElementById('addDomain').addEventListener('click', addExcludedDomain);
  document.getElementById('newDomain').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      addExcludedDomain();
    }
  });
  document.getElementById('clearAllData').addEventListener('click', clearAllData);
  document.getElementById('exportData').addEventListener('click', exportData);
}

// Keyboard Navigation
function handleKeyNavigation(e) {
  const resultsContainer = document.getElementById('searchResults');
  const resultCards = resultsContainer.querySelectorAll('.result-card');
  
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    selectedIndex = Math.min(selectedIndex + 1, resultCards.length - 1);
    updateSelection(resultCards);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    selectedIndex = Math.max(selectedIndex - 1, -1);
    updateSelection(resultCards);
  } else if (e.key === 'Enter' && selectedIndex >= 0) {
    e.preventDefault();
    const selectedCard = resultCards[selectedIndex];
    if (selectedCard) {
      const link = selectedCard.querySelector('.result-title');
      if (link) {
        if (e.metaKey || e.ctrlKey) {
          // Cmd/Ctrl+Enter: open in new tab
          window.open(link.href, '_blank');
        } else {
          // Regular Enter: open in current tab
          window.location.href = link.href;
        }
      }
    }
  } else if (e.key === 'Escape') {
    selectedIndex = -1;
    updateSelection(resultCards);
    // Ensure search input stays focused after escape
    if (document.activeElement !== e.target) {
      e.target.focus();
    }
  }
}

function updateSelection(resultCards) {
  resultCards.forEach((card, index) => {
    if (index === selectedIndex) {
      card.classList.add('selected');
      card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } else {
      card.classList.remove('selected');
    }
  });
}

// Search Functionality
async function handleSearch() {
  const query = document.getElementById('searchInput').value.trim();
  const resultsContainer = document.getElementById('searchResults');
  
  // Reset selection when search changes
  selectedIndex = -1;
  
  if (!query) {
    resultsContainer.innerHTML = '';
    searchResults = [];
    return;
  }
  
  // Show loading state
  resultsContainer.innerHTML = `
    <div class="loading">
      <div class="loading-spinner"></div>
      <p>Searching...</p>
    </div>
  `;
  
  try {
    let response;
    
    // Try Chrome extension API first, fallback to direct backend call for debugging
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      response = await chrome.runtime.sendMessage({
        type: 'SEARCH',
        query: query
      });
    } else {
      // Fallback for debugging - try backend call, fallback to mock data
      try {
        const backendResponse = await fetch(`${BACKEND_URL}/search?q=${encodeURIComponent(query)}`);
        if (backendResponse.ok) {
          const data = await backendResponse.json();
          response = { success: true, results: data.results || [] };
        } else {
          throw new Error('Backend not available');
        }
      } catch (backendError) {
        // Use mock data for debugging metadata display
        response = {
          success: true,
          results: [
            {
              id: 1,
              title: `Mock Result for "${query}"`,
              url: `https://example.com/result1?q=${encodeURIComponent(query)}`,
              description: `This is a mock search result for testing metadata display with query: ${query}`,
              keywords: 'python,programming,code,test',
              favicon_url: 'https://www.google.com/s2/favicons?domain=example.com',
              metadata: {
                vector_score: 0.856,
                keyword_score: 0.743,
                access_count: 15,
                final_score: 0.799
              }
            },
            {
              id: 2,
              title: `Another ${query} Example`,
              url: `https://docs.example.com/${query.toLowerCase()}`,
              description: `Documentation page about ${query} with detailed examples and tutorials`,
              keywords: `${query},documentation,tutorial,examples`,
              favicon_url: 'https://www.google.com/s2/favicons?domain=docs.example.com',
              metadata: {
                vector_score: 0.923,
                keyword_score: 0.891,
                access_count: 42,
                final_score: 0.907
              }
            }
          ]
        };
      }
    }
    
    if (response && response.success && response.results && response.results.length > 0) {
      searchResults = response.results;
      displayResults(response.results);
    } else if (response && response.success && response.results && response.results.length === 0) {
      searchResults = [];
      resultsContainer.innerHTML = `
        <div class="no-results">
          <h3>No results found</h3>
          <p>Try different keywords or use semantic search</p>
        </div>
      `;
    } else {
      throw new Error(response?.error || 'Search failed');
    }
  } catch (error) {
    console.error('Search error:', error);
    resultsContainer.innerHTML = `
      <div class="no-results">
        <h3>Search failed</h3>
        <p>${error.message}</p>
      </div>
    `;
  }
}


// Favicon fallback handling with proper infinite loop prevention
function handleFaviconError(imgElement) {
  // Clear any existing error handler
  imgElement.onerror = null;
  
  // Use a base64 encoded default icon to avoid any loading issues
  const defaultIconBase64 = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiByeD0iMyIgZmlsbD0iIzM3NDAzZiIvPgo8cGF0aCBkPSJNOCA0QzUuNzkgNCA0IDUuNzkgNCA4czEuNzkgNCA0IDQgNC0xLjc5IDQtNC0xLjc5LTQtNC00em0wIDZjLTEuMSAwLTItLjktMi0yczAuOS0yIDItMiAyIDAuOSAyIDItMC45IDItMiAyeiIgZmlsbD0iI2ZmZiIvPgo8L3N2Zz4K';
  imgElement.src = defaultIconBase64;
  imgElement.classList.add('default-favicon');
  imgElement.alt = 'Default favicon';
}


// Display search results
function displayResults(results) {
  const resultsContainer = document.getElementById('searchResults');
  
  const html = results.map((result, index) => {
    const keywords = result.keywords ? result.keywords.split(',').slice(0, 5) : [];
    const domain = new URL(result.url).hostname;
    let faviconUrl = result.favicon_url || `https://www.google.com/s2/favicons?domain=${domain}`;
    
    return `
      <div class="result-card" data-id="${result.id}" data-index="${index}" data-url="${escapeHtml(result.url)}">
        <div class="result-main">
          <div class="result-header">
            <img src="${faviconUrl}" alt="" class="result-favicon">
            <a href="${result.url}" target="_blank" class="result-title">${escapeHtml(result.title)}</a>
          </div>
          <div class="result-url">${escapeHtml(result.url)}</div>
          <div class="result-description">${escapeHtml(result.description || 'No description available')}</div>
          ${keywords.length > 0 ? `
            <div class="result-keywords">
              ${keywords.map(k => `<span class="keyword-tag">${escapeHtml(k.trim())}</span>`).join('')}
            </div>
          ` : ''}
        </div>
        ${result.metadata ? `
          <div class="metadata-panel">
            <div class="metadata-item" data-label="Vector Score:"><span>${parseFloat(result.metadata.vector_score).toFixed(3)}</span></div>
            <div class="metadata-item" data-label="Keyword Score:"><span>${parseFloat(result.metadata.keyword_score).toFixed(3)}</span></div>
            <div class="metadata-item" data-label="Access Count:"><span>${result.metadata.access_count}</span></div>
            <div class="metadata-item" data-label="Final Score:"><span>${parseFloat(result.metadata.final_score).toFixed(3)}</span></div>
          </div>
        ` : ''}
        <button class="result-delete" data-id="${result.id}" title="Delete this entry">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3,6 5,6 21,6"></polyline>
            <path d="m19,6v14a2,2 0,0 1,-2,2H7a2,2 0,0 1,-2,2V6m3,0V4a2,2 0,0 1,2,-2h4a2,2 0,0 1,2,2V6"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
          </svg>
        </button>
      </div>
    `;
  }).join('');
  
  resultsContainer.innerHTML = html;
  
  // Auto-focus the first result when results appear
  if (results.length > 0) {
    selectedIndex = 0;
    const resultCards = resultsContainer.querySelectorAll('.result-card');
    updateSelection(resultCards);
    
    // Add event listeners to result cards
    resultCards.forEach((card, index) => {
      // Mouse hover for keyboard navigation support
      card.addEventListener('mouseenter', () => {
        selectedIndex = index;
        updateSelection(resultCards);
      });
      
      // Click handler for result main area
      const mainArea = card.querySelector('.result-main');
      mainArea.addEventListener('click', (e) => {
        e.preventDefault();
        const url = card.dataset.url;
        window.open(url, '_blank');
      });
      
      // Delete button click handler
      const deleteBtn = card.querySelector('.result-delete');
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = parseInt(deleteBtn.dataset.id);
        deleteResult(id);
      });
      
      // Favicon error handler
      const favicon = card.querySelector('.result-favicon');
      favicon.addEventListener('error', () => {
        handleFaviconError(favicon);
      });
    });
  }
}

// Delete a result
async function deleteResult(id) {
  if (!confirm('Are you sure you want to delete this entry?')) {
    return;
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/pages/${id}`, {
      method: 'DELETE'
    });
    
    if (response.ok) {
      // Remove the card from UI
      const card = document.querySelector(`.result-card[data-id="${id}"]`);
      if (card) {
        card.style.animation = 'fadeOut 0.3s';
        setTimeout(() => card.remove(), 300);
      }
      
      // Update statistics
      loadStatistics();
    } else {
      alert('Failed to delete entry');
    }
  } catch (error) {
    console.error('Delete error:', error);
    alert('Failed to delete entry: ' + error.message);
  }
}

// Settings Functions
function openSettings() {
  document.getElementById('settingsView').classList.add('open');
  window.location.hash = 'settings';
  loadDetailedStatistics();
}

function closeSettings() {
  document.getElementById('settingsView').classList.remove('open');
  window.location.hash = '';
  
  // Refocus search input after closing settings
  setTimeout(() => {
    focusSearchInput();
  }, 100);
}

async function loadSettings() {
  try {
    let settings = {};
    
    // Try Chrome storage first, fallback to localStorage for debugging
    if (typeof chrome !== 'undefined' && chrome.storage) {
      const storage = await chrome.storage.local.get('localWebMemory');
      settings = storage.localWebMemory || {};
    } else {
      // Fallback for debugging outside Chrome extension
      const localSettings = localStorage.getItem('localWebMemory');
      settings = localSettings ? JSON.parse(localSettings) : {};
    }
    
    document.getElementById('enableIndexing').checked = settings.indexingEnabled !== false;
    document.getElementById('showMetadata').checked = settings.showMetadata === true;
    excludedDomains = settings.excludedDomains || [];
    
    updateExcludedDomainsList();
    updateMetadataDisplay(settings.showMetadata === true);
  } catch (error) {
    console.error('Error loading settings:', error);
  }
}

async function handleIndexingToggle(e) {
  const enabled = e.target.checked;
  
  try {
    const storage = await chrome.storage.local.get('localWebMemory');
    const settings = storage.localWebMemory || {};
    settings.indexingEnabled = enabled;
    await chrome.storage.local.set({ localWebMemory: settings });
  } catch (error) {
    console.error('Error updating settings:', error);
    e.target.checked = !enabled; // Revert on error
  }
}

async function handleMetadataToggle(e) {
  const enabled = e.target.checked;
  
  try {
    let settings = {};
    
    // Try Chrome storage first, fallback to localStorage for debugging
    if (typeof chrome !== 'undefined' && chrome.storage) {
      const storage = await chrome.storage.local.get('localWebMemory');
      settings = storage.localWebMemory || {};
      settings.showMetadata = enabled;
      await chrome.storage.local.set({ localWebMemory: settings });
    } else {
      // Fallback for debugging outside Chrome extension
      const localSettings = localStorage.getItem('localWebMemory');
      settings = localSettings ? JSON.parse(localSettings) : {};
      settings.showMetadata = enabled;
      localStorage.setItem('localWebMemory', JSON.stringify(settings));
    }
    
    updateMetadataDisplay(enabled);
  } catch (error) {
    console.error('Error updating metadata settings:', error);
    e.target.checked = !enabled; // Revert on error
  }
}

function updateMetadataDisplay(showMetadata) {
  const searchView = document.getElementById('searchView');
  if (showMetadata) {
    searchView.classList.add('debug-mode');
  } else {
    searchView.classList.remove('debug-mode');
  }
}

function updateExcludedDomainsList() {
  const container = document.getElementById('excludedDomains');
  
  if (excludedDomains.length === 0) {
    container.innerHTML = '<p class="settings-description">No domains excluded</p>';
    return;
  }
  
  container.innerHTML = excludedDomains.map(domain => `
    <div class="domain-item">
      <span>${escapeHtml(domain)}</span>
      <button class="remove-domain" data-domain="${escapeHtml(domain)}">×</button>
    </div>
  `).join('');
  
  // Add event listeners for remove buttons
  container.querySelectorAll('.remove-domain').forEach(btn => {
    btn.addEventListener('click', () => {
      const domain = btn.dataset.domain;
      removeDomain(domain);
    });
  });
}

async function addExcludedDomain() {
  const input = document.getElementById('newDomain');
  const domain = input.value.trim().toLowerCase();
  
  if (!domain) return;
  
  // Validate domain format
  if (!/^[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,}$/i.test(domain)) {
    alert('Please enter a valid domain (e.g., example.com)');
    return;
  }
  
  if (excludedDomains.includes(domain)) {
    alert('Domain already excluded');
    return;
  }
  
  excludedDomains.push(domain);
  
  try {
    const storage = await chrome.storage.local.get('localWebMemory');
    const settings = storage.localWebMemory || {};
    settings.excludedDomains = excludedDomains;
    await chrome.storage.local.set({ localWebMemory: settings });
    
    updateExcludedDomainsList();
    input.value = '';
  } catch (error) {
    console.error('Error saving settings:', error);
    excludedDomains.pop(); // Revert on error
  }
}

async function removeDomain(domain) {
  excludedDomains = excludedDomains.filter(d => d !== domain);
  
  try {
    const storage = await chrome.storage.local.get('localWebMemory');
    const settings = storage.localWebMemory || {};
    settings.excludedDomains = excludedDomains;
    await chrome.storage.local.set({ localWebMemory: settings });
    
    updateExcludedDomainsList();
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}

// Data Management
async function clearAllData() {
  if (!confirm('This will delete all indexed pages. Are you sure?')) {
    return;
  }
  
  try {
    // Clear all pages from backend
    const response = await fetch(`${BACKEND_URL}/pages`);
    const data = await response.json();
    
    for (const page of data.pages) {
      await fetch(`${BACKEND_URL}/pages/${page.id}`, { method: 'DELETE' });
    }
    
    // Clear statistics from storage
    const storage = await chrome.storage.local.get('localWebMemory');
    const settings = storage.localWebMemory || {};
    settings.totalPagesIndexed = 0;
    settings.lastIndexedUrl = null;
    settings.lastIndexedTime = null;
    await chrome.storage.local.set({ localWebMemory: settings });
    
    alert('All data cleared successfully');
    loadStatistics();
    loadDetailedStatistics();
    
    // Clear search results if any
    document.getElementById('searchResults').innerHTML = '';
    
  } catch (error) {
    console.error('Error clearing data:', error);
    alert('Failed to clear data: ' + error.message);
  }
}

async function exportData() {
  try {
    const response = await fetch(`${BACKEND_URL}/pages?limit=1000`);
    const data = await response.json();
    
    const exportData = {
      version: '1.0',
      exportDate: new Date().toISOString(),
      totalPages: data.total,
      pages: data.pages,
      settings: {
        excludedDomains: excludedDomains
      }
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `local-web-memory-export-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
  } catch (error) {
    console.error('Error exporting data:', error);
    alert('Failed to export data: ' + error.message);
  }
}

// Statistics
async function loadStatistics() {
  try {
    const response = await fetch(`${BACKEND_URL}/stats`);
    const stats = await response.json();
    
    document.getElementById('totalPages').textContent = (stats.database?.total_pages || stats.total_pages || 0).toLocaleString();
    
  } catch (error) {
    console.error('Error loading statistics:', error);
    document.getElementById('totalPages').textContent = '0';
  }
}

async function loadDetailedStatistics() {
  try {
    const response = await fetch(`${BACKEND_URL}/stats`);
    const stats = await response.json();
    
    const container = document.getElementById('detailedStats');
    container.innerHTML = `
      <div class="stat-item">
        <span class="label">Total Pages</span>
        <span class="value">${stats.database?.total_pages || stats.total_pages || 0}</span>
      </div>
      <div class="stat-item">
        <span class="label">Vectors Stored</span>
        <span class="value">${stats.vector_store?.total_vectors || stats.total_vectors || 0}</span>
      </div>
      <div class="stat-item">
        <span class="label">Memory Usage</span>
        <span class="value">${(stats.vector_store?.memory_usage_mb || stats.memory_usage_mb || 0).toFixed(2)} MB</span>
      </div>
      <div class="stat-item">
        <span class="label">Vector Dimensions</span>
        <span class="value">${stats.vector_store?.dimension || stats.vector_dimensions || 0}</span>
      </div>
    `;
    
  } catch (error) {
    console.error('Error loading detailed statistics:', error);
  }
}

async function checkBackendStatus() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    const status = response.ok ? 'Online' : 'Offline';
    document.getElementById('backendStatus').textContent = status;
    document.getElementById('backendStatus').style.color = response.ok ? '#10b981' : '#ef4444';
  } catch (error) {
    document.getElementById('backendStatus').textContent = 'Offline';
    document.getElementById('backendStatus').style.color = '#ef4444';
  }
}

// Utility Functions
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// Functions no longer need to be global since we use proper event listeners

// Add fade out animation
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeOut {
    from {
      opacity: 1;
      transform: translateX(0);
    }
    to {
      opacity: 0;
      transform: translateX(20px);
    }
  }
`;
document.head.appendChild(style);