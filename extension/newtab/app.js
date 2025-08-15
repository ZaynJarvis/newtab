// New tab page app
const BACKEND_URL = 'http://localhost:8000';
let currentSearchType = 'combined'; // Use combined search by default
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
  
  // Force focus on search input with delay to work around Chrome security
  setTimeout(() => {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
      searchInput.focus();
    }
  }, 100);
});

// Event Listeners
function initializeEventListeners() {
  // Search
  const searchInput = document.getElementById('searchInput');
  
  searchInput.addEventListener('input', debounce(handleSearch, 300));
  searchInput.addEventListener('keydown', handleKeyNavigation);
  
  // Settings
  document.getElementById('settingsToggle').addEventListener('click', openSettings);
  document.getElementById('closeSettings').addEventListener('click', closeSettings);
  document.getElementById('enableIndexing').addEventListener('change', handleIndexingToggle);
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
        window.open(link.href, '_blank');
      }
    }
  } else if (e.key === 'Escape') {
    selectedIndex = -1;
    updateSelection(resultCards);
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
    // Use service worker to search
    const response = await chrome.runtime.sendMessage({
      type: 'SEARCH',
      query: query,
      searchType: currentSearchType
    });
    
    if (response.success && response.results.length > 0) {
      searchResults = response.results;
      displayResults(response.results);
    } else if (response.success && response.results.length === 0) {
      searchResults = [];
      resultsContainer.innerHTML = `
        <div class="no-results">
          <h3>No results found</h3>
          <p>Try different keywords or use semantic search</p>
        </div>
      `;
    } else {
      throw new Error(response.error || 'Search failed');
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

// Display search results
function displayResults(results) {
  const resultsContainer = document.getElementById('searchResults');
  
  const html = results.map((result, index) => {
    const keywords = result.keywords ? result.keywords.split(',').slice(0, 5) : [];
    const faviconUrl = result.favicon_url || `https://www.google.com/s2/favicons?domain=${new URL(result.url).hostname}`;
    
    return `
      <div class="result-card" data-id="${result.id}" data-index="${index}">
        <div class="result-main" onclick="window.open('${result.url}', '_blank')">
          <div class="result-header">
            <img src="${faviconUrl}" alt="" class="result-favicon" onerror="this.style.display='none'">
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
        <button class="result-delete" onclick="deleteResult(${result.id})" title="Delete this entry">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3,6 5,6 21,6"></polyline>
            <path d="m19,6v14a2,2 0,0 1,-2,2H7a2,2 0,0 1,-2,-2V6m3,0V4a2,2 0,0 1,2,-2h4a2,2 0,0 1,2,2V6"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
          </svg>
        </button>
      </div>
    `;
  }).join('');
  
  resultsContainer.innerHTML = html;
  
  // Add click listeners to result cards for keyboard navigation support
  const resultCards = resultsContainer.querySelectorAll('.result-card');
  resultCards.forEach((card, index) => {
    card.addEventListener('mouseenter', () => {
      selectedIndex = index;
      updateSelection(resultCards);
    });
  });
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
}

async function loadSettings() {
  try {
    const storage = await chrome.storage.local.get('localWebMemory');
    const settings = storage.localWebMemory || {};
    
    document.getElementById('enableIndexing').checked = settings.indexingEnabled !== false;
    excludedDomains = settings.excludedDomains || [];
    
    updateExcludedDomainsList();
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

function updateExcludedDomainsList() {
  const container = document.getElementById('excludedDomains');
  
  if (excludedDomains.length === 0) {
    container.innerHTML = '<p class="settings-description">No domains excluded</p>';
    return;
  }
  
  container.innerHTML = excludedDomains.map(domain => `
    <div class="domain-item">
      <span>${escapeHtml(domain)}</span>
      <button class="remove-domain" onclick="removeDomain('${escapeHtml(domain)}')">×</button>
    </div>
  `).join('');
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
    
    document.getElementById('totalPages').textContent = stats.total_pages.toLocaleString();
    
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
        <span class="value">${stats.total_pages}</span>
      </div>
      <div class="stat-item">
        <span class="label">Vectors Stored</span>
        <span class="value">${stats.total_vectors}</span>
      </div>
      <div class="stat-item">
        <span class="label">Memory Usage</span>
        <span class="value">${stats.memory_usage_mb.toFixed(2)} MB</span>
      </div>
      <div class="stat-item">
        <span class="label">Vector Dimensions</span>
        <span class="value">${stats.vector_dimensions}</span>
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

// Make functions available globally for onclick handlers
window.deleteResult = deleteResult;
window.removeDomain = removeDomain;

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