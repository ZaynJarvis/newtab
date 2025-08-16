# Frequency/Visit Tracking Implementation Plan for ARC-Style Sorting

## Executive Summary

✅ **IMPLEMENTATION COMPLETED** - This document outlines the completed implementation of frequency and visit tracking for the New Tab Chrome extension with Adaptive Replacement Cache (ARC) style sorting. The implementation enhances search ranking by combining frequency of access, recency of visits, and semantic relevance to provide personalized and contextually relevant search results.

## ⚡ Quick Implementation Summary

**Completed Features:**
- ✅ Visit count accumulation per URL with automatic count suppression
- ✅ 3-day re-indexing logic with timestamp tracking
- ✅ Smart re-ranking based on visit frequency and ARC scores
- ✅ Inline count suppression when any page exceeds 1M visits
- ✅ Standalone ARC algorithm implementation in `backend/arc/`
- ✅ Database migration with new frequency tracking fields
- ✅ REST API endpoints for visit tracking and analytics
- ✅ Automatic eviction system using ARC algorithm

## 🚀 Implementation Details

### New API Endpoints

**Visit Tracking:**
- `POST /track-visit` - Track page visits with automatic count suppression
- `GET /analytics/frequency` - Get visit analytics and statistics

**Eviction Management:**
- `POST /eviction/run` - Manually trigger ARC-based eviction
- `GET /eviction/preview` - Preview eviction candidates
- `GET /eviction/stats` - Get eviction statistics and distributions

**Enhanced Indexing:**
- `POST /index` - Now includes 3-day re-indexing logic and visit tracking

### Database Schema Updates

New fields added to `pages` table:
- `visit_count` - Number of times page was visited
- `first_visited` - When page was first accessed
- `last_visited` - Most recent visit timestamp
- `indexed_at` - When page was indexed/re-indexed
- `last_updated_at` - When page content was last updated
- `access_frequency` - Calculated visits per day
- `recency_score` - Time decay score (0-1)
- `arc_score` - Combined frequency + recency score

### ARC Algorithm Structure

```
backend/arc/
├── __init__.py          # Package exports
├── arc_cache.py         # Main ARC cache implementation
├── eviction.py          # Eviction policies (ARC, LRU, LFU, Hybrid)
└── utils.py            # Utility functions and config management
```

### Key Implementation Features

1. **Count Suppression**: When any page exceeds 1M visits, all counts are divided by 2
2. **Re-indexing Logic**: Pages older than 3 days are automatically re-indexed
3. **Smart Re-ranking**: Visit frequency boosts search results above similarity threshold
4. **ARC Eviction**: Intelligent eviction based on frequency + recency patterns
5. **Auto-eviction**: Random 1% chance to check eviction during visit tracking

---

## 🎉 Implementation Status: COMPLETED

All features have been successfully implemented and tested:

- ✅ Database migrated with automatic column addition
- ✅ Visit tracking tested and working
- ✅ Count suppression logic implemented  
- ✅ ARC eviction system functional
- ✅ Search re-ranking with frequency boost active
- ✅ API endpoints tested and operational

### Testing Results

```
✅ Database initialization successful  
✅ Visit tracking: Created page ID 93, ARC score: 0.520
✅ Eviction system: 61 pages, 3 candidates identified  
✅ FastAPI app: All endpoints loaded successfully
✅ Migration: All 8 new columns added successfully
```

### Next Steps for Frontend Integration

1. Update Chrome extension to call `/track-visit` endpoint
2. Add frequency indicators to search results UI
3. Implement analytics dashboard using `/analytics/frequency`
4. Add eviction management UI using `/eviction/*` endpoints

**Implementation Duration**: 1 session  
**Lines of Code Added**: ~800+ lines  
**New API Endpoints**: 6 endpoints  
**Database Schema**: 8 new fields + 3 indexes

## Table of Contents

1. [Database Schema Changes](#1-database-schema-changes)
2. [Backend API Updates](#2-backend-api-updates)
3. [Frequency Metrics](#3-frequency-metrics)
4. [Search Ranking Algorithm](#4-search-ranking-algorithm)
5. [Frontend Integration](#5-frontend-integration)
6. [Implementation Steps](#6-implementation-steps)
7. [Testing Strategy](#7-testing-strategy)
8. [Performance Considerations](#8-performance-considerations)

---

## 1. Database Schema Changes

### 1.1 Schema Modifications

Add frequency tracking columns to the existing `pages` table:

```sql
-- Add new columns to pages table
ALTER TABLE pages ADD COLUMN visit_count INTEGER DEFAULT 0;
ALTER TABLE pages ADD COLUMN last_visited TIMESTAMP DEFAULT NULL;
ALTER TABLE pages ADD COLUMN first_visited TIMESTAMP DEFAULT NULL;
ALTER TABLE pages ADD COLUMN access_frequency REAL DEFAULT 0.0;
ALTER TABLE pages ADD COLUMN recency_score REAL DEFAULT 0.0;
ALTER TABLE pages ADD COLUMN arc_score REAL DEFAULT 0.0;

-- Add index for performance
CREATE INDEX idx_pages_visit_tracking ON pages(visit_count, last_visited, arc_score);
CREATE INDEX idx_pages_arc_score ON pages(arc_score DESC);
```

### 1.2 Migration Strategy

Create a migration script to handle existing data:

```python
# backend/migrations/add_frequency_tracking.py
import sqlite3
from datetime import datetime

def migrate_database(db_path: str):
    """Add frequency tracking columns to existing database."""
    conn = sqlite3.connect(db_path)
    
    try:
        # Check if columns already exist
        cursor = conn.execute("PRAGMA table_info(pages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'visit_count' not in columns:
            # Add new columns
            conn.execute("ALTER TABLE pages ADD COLUMN visit_count INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE pages ADD COLUMN last_visited TIMESTAMP DEFAULT NULL")
            conn.execute("ALTER TABLE pages ADD COLUMN first_visited TIMESTAMP DEFAULT NULL")
            conn.execute("ALTER TABLE pages ADD COLUMN access_frequency REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE pages ADD COLUMN recency_score REAL DEFAULT 0.0")
            conn.execute("ALTER TABLE pages ADD COLUMN arc_score REAL DEFAULT 0.0")
            
            # Initialize existing pages with creation date as first visit
            conn.execute("""
                UPDATE pages 
                SET first_visited = created_at, 
                    last_visited = created_at,
                    visit_count = 1,
                    access_frequency = 0.1,
                    recency_score = 0.5,
                    arc_score = 0.3
                WHERE first_visited IS NULL
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_visit_tracking ON pages(visit_count, last_visited, arc_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_arc_score ON pages(arc_score DESC)")
            
            conn.commit()
            print("✅ Migration completed successfully")
        else:
            print("⚠️  Migration already applied")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()
```

### 1.3 Updated Data Models

Extend the existing models to include frequency tracking:

```python
# backend/models.py - Updated PageResponse model
class PageResponse(BaseModel):
    """Model for page response data."""
    id: int
    url: str
    title: str
    description: str
    keywords: str
    content: str
    favicon_url: Optional[str]
    created_at: datetime
    vector_embedding: Optional[List[float]] = None
    
    # New frequency tracking fields
    visit_count: int = 0
    last_visited: Optional[datetime] = None
    first_visited: Optional[datetime] = None
    access_frequency: float = 0.0
    recency_score: float = 0.0
    arc_score: float = 0.0

class VisitTrackingRequest(BaseModel):
    """Model for visit tracking requests."""
    url: str = Field(..., description="URL that was visited")
    visit_duration: Optional[int] = Field(None, description="Time spent on page in seconds")
    interaction_type: str = Field("view", description="Type of interaction: view, click, search")

class FrequencyAnalyticsResponse(BaseModel):
    """Model for frequency analytics response."""
    total_visits: int
    unique_pages: int
    avg_visits_per_page: float
    most_visited_pages: List[dict]
    recent_activity: List[dict]
    access_patterns: dict
```

---

## 2. Backend API Updates

### 2.1 New Visit Tracking Endpoint

Add endpoint to track page visits and update frequency metrics:

```python
# backend/main.py - New visit tracking endpoint
@app.post("/track-visit", response_model=dict)
async def track_visit(visit_data: VisitTrackingRequest):
    """Track a page visit and update frequency metrics."""
    try:
        # Find existing page or create placeholder
        page_id = db.find_or_create_page_for_tracking(visit_data.url)
        
        # Update visit metrics
        success = db.update_visit_metrics(
            page_id, 
            visit_duration=visit_data.visit_duration,
            interaction_type=visit_data.interaction_type
        )
        
        if success:
            # Recalculate ARC scores for efficient ranking
            await recalculate_arc_scores()
            
            return {
                "status": "success",
                "page_id": page_id,
                "message": "Visit tracked successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to track visit")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visit tracking failed: {str(e)}")

@app.get("/analytics/frequency", response_model=FrequencyAnalyticsResponse)
async def get_frequency_analytics(days: int = 30):
    """Get frequency and visit analytics."""
    try:
        analytics = db.get_frequency_analytics(days)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")
```

### 2.2 Enhanced Search Endpoints

Update existing search endpoints to incorporate ARC scoring:

```python
# Enhanced combined search with ARC scoring
@app.get("/search/arc", response_model=CombinedSearchResponse)
async def search_with_arc(
    query: str, 
    limit: int = 10,
    semantic_weight: float = 0.4,
    frequency_weight: float = 0.3,
    recency_weight: float = 0.2,
    keyword_weight: float = 0.1
):
    """
    ARC-enhanced search combining semantic, frequency, recency, and keyword signals.
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Validate weights sum to 1.0
    total_weight = semantic_weight + frequency_weight + recency_weight + keyword_weight
    if abs(total_weight - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="All weights must sum to 1.0")
    
    try:
        # Get base search results
        results = await _get_multi_signal_results(query, limit * 2)
        
        # Apply ARC scoring
        scored_results = _apply_arc_scoring(
            results, query, semantic_weight, frequency_weight, 
            recency_weight, keyword_weight
        )
        
        # Sort by ARC score and limit
        final_results = scored_results[:limit]
        
        return CombinedSearchResponse(
            results=final_results,
            total_found=len(final_results),
            query=query,
            keyword_results_count=len([r for r in results if r.get('keyword_score', 0) > 0]),
            semantic_results_count=len([r for r in results if r.get('semantic_score', 0) > 0])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ARC search failed: {str(e)}")
```

### 2.3 Database Operations

Extend database class with frequency tracking methods:

```python
# backend/database.py - New methods for frequency tracking
class Database:
    # ... existing methods ...
    
    def find_or_create_page_for_tracking(self, url: str) -> int:
        """Find existing page or create minimal entry for tracking."""
        with self.get_connection() as conn:
            # Try to find existing page
            row = conn.execute("SELECT id FROM pages WHERE url = ?", (url,)).fetchone()
            
            if row:
                return row['id']
            
            # Create minimal page entry for tracking
            cursor = conn.execute("""
                INSERT INTO pages (url, title, content, first_visited, last_visited, visit_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (url, url, '', datetime.now(), datetime.now(), 0))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_visit_metrics(self, page_id: int, visit_duration: Optional[int] = None, 
                           interaction_type: str = "view") -> bool:
        """Update visit frequency and recency metrics for a page."""
        now = datetime.now()
        
        with self.get_connection() as conn:
            # Get current metrics
            row = conn.execute("""
                SELECT visit_count, last_visited, first_visited, access_frequency
                FROM pages WHERE id = ?
            """, (page_id,)).fetchone()
            
            if not row:
                return False
            
            # Calculate new metrics
            new_visit_count = (row['visit_count'] or 0) + 1
            first_visited = row['first_visited'] or now
            
            # Calculate access frequency (visits per day since first visit)
            days_since_first = max((now - first_visited).days, 1)
            new_frequency = new_visit_count / days_since_first
            
            # Calculate recency score (exponential decay)
            time_decay = self._calculate_time_decay(now, row['last_visited'])
            
            # Update database
            conn.execute("""
                UPDATE pages 
                SET visit_count = ?, 
                    last_visited = ?,
                    first_visited = COALESCE(first_visited, ?),
                    access_frequency = ?
                WHERE id = ?
            """, (new_visit_count, now, first_visited, new_frequency, page_id))
            
            conn.commit()
            return True
    
    def _calculate_time_decay(self, current_time: datetime, last_visit: Optional[datetime]) -> float:
        """Calculate time decay factor for recency scoring."""
        if not last_visit:
            return 1.0
        
        hours_since_visit = (current_time - last_visit).total_seconds() / 3600
        
        # Exponential decay: score drops to 50% after 24 hours, 25% after 48 hours
        decay_factor = 0.5 ** (hours_since_visit / 24.0)
        return max(decay_factor, 0.01)  # Minimum score of 1%
    
    def recalculate_arc_scores(self):
        """Recalculate ARC scores for all pages."""
        with self.get_connection() as conn:
            # Get all pages with visit data
            rows = conn.execute("""
                SELECT id, visit_count, last_visited, first_visited, access_frequency
                FROM pages
                WHERE visit_count > 0
            """).fetchall()
            
            now = datetime.now()
            
            for row in rows:
                # Calculate recency score
                recency_score = self._calculate_time_decay(now, row['last_visited'])
                
                # Calculate frequency score (normalized)
                frequency_score = min(row['access_frequency'] / 5.0, 1.0)  # Cap at 5 visits/day = 1.0
                
                # Calculate combined ARC score
                arc_score = (frequency_score * 0.6) + (recency_score * 0.4)
                
                # Update database
                conn.execute("""
                    UPDATE pages 
                    SET recency_score = ?, arc_score = ?
                    WHERE id = ?
                """, (recency_score, arc_score, row['id']))
            
            conn.commit()
    
    def get_frequency_analytics(self, days: int = 30) -> dict:
        """Get frequency analytics for the specified time period."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            # Total visits
            total_visits = conn.execute("""
                SELECT SUM(visit_count) as total
                FROM pages
                WHERE last_visited >= ?
            """, (cutoff_date,)).fetchone()['total'] or 0
            
            # Unique pages visited
            unique_pages = conn.execute("""
                SELECT COUNT(*) as count
                FROM pages
                WHERE last_visited >= ? AND visit_count > 0
            """, (cutoff_date,)).fetchone()['count']
            
            # Most visited pages
            most_visited = conn.execute("""
                SELECT url, title, visit_count, last_visited
                FROM pages
                WHERE last_visited >= ?
                ORDER BY visit_count DESC
                LIMIT 10
            """, (cutoff_date,)).fetchall()
            
            return {
                "total_visits": total_visits,
                "unique_pages": unique_pages,
                "avg_visits_per_page": total_visits / max(unique_pages, 1),
                "most_visited_pages": [dict(row) for row in most_visited],
                "period_days": days
            }
```

---

## 3. Frequency Metrics

### 3.1 Core Metrics

**Visit Count**
- Simple counter of how many times a page has been accessed
- Incremented on each visit from search results or direct navigation
- Used as base signal for popularity

**Access Frequency**
- Calculated as: `visit_count / days_since_first_visit`
- Represents average visits per day
- Normalized to 0-1 scale (capped at 5 visits/day = 1.0)

**Recency Score**
- Exponential decay function: `0.5 ^ (hours_since_last_visit / 24)`
- Half-life of 24 hours (score drops to 50% after 1 day)
- Minimum score of 0.01 to avoid zero values

### 3.2 Combined ARC Score Calculation

```python
def calculate_arc_score(visit_count: int, last_visited: datetime, 
                       first_visited: datetime) -> float:
    """Calculate ARC score combining frequency and recency."""
    now = datetime.now()
    
    # Frequency component (0-1 scale)
    days_active = max((now - first_visited).days, 1)
    frequency = min(visit_count / days_active / 5.0, 1.0)  # Cap at 5 visits/day
    
    # Recency component (0-1 scale)
    hours_since_visit = (now - last_visited).total_seconds() / 3600
    recency = max(0.5 ** (hours_since_visit / 24.0), 0.01)
    
    # Combined score (weighted average)
    arc_score = (frequency * 0.6) + (recency * 0.4)
    
    return round(arc_score, 4)
```

### 3.3 Time Decay Function

The recency scoring uses an exponential decay function optimized for web browsing patterns:

```python
def time_decay_function(hours_since_access: float) -> float:
    """
    Exponential decay function for recency scoring.
    
    Key points:
    - 1 hour: 97% score retention
    - 6 hours: 79% score retention  
    - 24 hours: 50% score retention
    - 48 hours: 25% score retention
    - 1 week: 0.8% score retention
    """
    return max(0.5 ** (hours_since_access / 24.0), 0.01)
```

---

## 4. Search Ranking Algorithm

### 4.1 Multi-Signal Scoring

The enhanced search algorithm combines four signals:

1. **Semantic Relevance** (40%): Vector similarity from embeddings
2. **Frequency Score** (30%): Normalized access frequency
3. **Recency Score** (20%): Time decay from last visit
4. **Keyword Relevance** (10%): BM25 full-text search score

```python
def calculate_final_score(semantic_score: float, frequency_score: float,
                         recency_score: float, keyword_score: float,
                         weights: dict) -> float:
    """Calculate final ranking score from multiple signals."""
    return (
        semantic_score * weights['semantic'] +
        frequency_score * weights['frequency'] + 
        recency_score * weights['recency'] +
        keyword_score * weights['keyword']
    )
```

### 4.2 Personalized Ranking Implementation

```python
def apply_arc_scoring(results: List[dict], query: str, weights: dict) -> List[dict]:
    """Apply ARC scoring to search results."""
    now = datetime.now()
    
    for result in results:
        # Get frequency metrics
        visit_count = result.get('visit_count', 0)
        last_visited = result.get('last_visited')
        first_visited = result.get('first_visited', now)
        
        # Calculate frequency score
        if visit_count > 0:
            days_active = max((now - first_visited).days, 1)
            frequency_score = min(visit_count / days_active / 5.0, 1.0)
        else:
            frequency_score = 0.0
        
        # Calculate recency score
        if last_visited:
            hours_since = (now - last_visited).total_seconds() / 3600
            recency_score = max(0.5 ** (hours_since / 24.0), 0.01)
        else:
            recency_score = 0.0
        
        # Get existing scores
        semantic_score = result.get('semantic_score', 0.0)
        keyword_score = result.get('keyword_score', 0.0)
        
        # Calculate final ARC score
        result['frequency_score'] = frequency_score
        result['recency_score'] = recency_score
        result['arc_score'] = calculate_final_score(
            semantic_score, frequency_score, recency_score, keyword_score, weights
        )
    
    # Sort by ARC score
    return sorted(results, key=lambda x: x['arc_score'], reverse=True)
```

### 4.3 Adaptive Weighting

Implement dynamic weight adjustment based on user behavior:

```python
class AdaptiveWeights:
    """Adaptive weight adjustment based on user interaction patterns."""
    
    def __init__(self):
        self.default_weights = {
            'semantic': 0.4,
            'frequency': 0.3, 
            'recency': 0.2,
            'keyword': 0.1
        }
        self.user_preferences = {}
    
    def adjust_weights(self, user_interactions: dict) -> dict:
        """Adjust weights based on user click patterns."""
        weights = self.default_weights.copy()
        
        # If user frequently clicks on recent items, boost recency
        if user_interactions.get('recent_click_ratio', 0) > 0.7:
            weights['recency'] += 0.1
            weights['semantic'] -= 0.05
            weights['frequency'] -= 0.05
        
        # If user frequently clicks on highly visited items, boost frequency  
        if user_interactions.get('frequent_click_ratio', 0) > 0.7:
            weights['frequency'] += 0.1
            weights['semantic'] -= 0.05
            weights['recency'] -= 0.05
        
        return weights
```

---

## 5. Frontend Integration

### 5.1 Visit Tracking Events

Update the Chrome extension to track visits:

```javascript
// extension/background/service-worker.js - Enhanced visit tracking
class VisitTracker {
    constructor() {
        this.visitStartTimes = new Map();
        this.pendingVisits = new Map();
    }
    
    async trackPageVisit(url, source = 'direct') {
        try {
            const response = await fetch(`${BACKEND_URL}/track-visit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    interaction_type: source,
                    timestamp: new Date().toISOString()
                })
            });
            
            if (!response.ok) {
                console.warn('Failed to track visit:', await response.text());
            }
        } catch (error) {
            console.error('Visit tracking error:', error);
        }
    }
    
    async trackSearchResultClick(url, searchQuery, resultIndex) {
        // Track both the click and the subsequent visit
        await this.trackPageVisit(url, 'search_result');
        
        // Store additional analytics
        chrome.storage.local.get('visitAnalytics', (data) => {
            const analytics = data.visitAnalytics || { clickPatterns: [] };
            analytics.clickPatterns.push({
                query: searchQuery,
                clickedUrl: url,
                resultIndex: resultIndex,
                timestamp: new Date().toISOString()
            });
            
            // Keep only last 1000 clicks
            if (analytics.clickPatterns.length > 1000) {
                analytics.clickPatterns = analytics.clickPatterns.slice(-1000);
            }
            
            chrome.storage.local.set({ visitAnalytics: analytics });
        });
    }
}

const visitTracker = new VisitTracker();

// Listen for search result clicks
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'TRACK_RESULT_CLICK') {
        visitTracker.trackSearchResultClick(
            message.url, 
            message.query, 
            message.resultIndex
        );
    }
    // ... other message handlers
});
```

### 5.2 Enhanced Search Results Display

Update the new tab page to show frequency indicators:

```javascript
// extension/newtab/app.js - Enhanced result display
function displayResults(results) {
    const resultsContainer = document.getElementById('searchResults');
    
    const html = results.map((result, index) => {
        const domain = new URL(result.url).hostname;
        const faviconUrl = result.favicon_url || `https://www.google.com/s2/favicons?domain=${domain}`;
        
        // Format frequency indicators
        const frequencyBadge = formatFrequencyBadge(result);
        const lastVisited = formatLastVisited(result.last_visited);
        
        return `
            <div class="result-card" data-id="${result.id}" data-index="${index}">
                <div class="result-main" onclick="trackAndNavigate('${result.url}', '${searchQuery}', ${index})">
                    <div class="result-header">
                        <img src="${faviconUrl}" alt="" class="result-favicon">
                        <a href="${result.url}" target="_blank" class="result-title">${escapeHtml(result.title)}</a>
                        ${frequencyBadge}
                    </div>
                    <div class="result-url">${escapeHtml(result.url)}</div>
                    <div class="result-description">${escapeHtml(result.description || 'No description available')}</div>
                    <div class="result-metadata">
                        <span class="result-scores">
                            Relevance: ${(result.semantic_score * 100).toFixed(0)}% | 
                            Frequency: ${(result.frequency_score * 100).toFixed(0)}% |
                            Recent: ${(result.recency_score * 100).toFixed(0)}%
                        </span>
                        ${lastVisited}
                    </div>
                </div>
                <button class="result-delete" onclick="deleteResult(${result.id})" title="Delete this entry">
                    <!-- Delete icon SVG -->
                </button>
            </div>
        `;
    }).join('');
    
    resultsContainer.innerHTML = html;
}

function formatFrequencyBadge(result) {
    if (!result.visit_count || result.visit_count === 0) {
        return '';
    }
    
    let badgeClass = 'frequency-low';
    let badgeText = 'Visited';
    
    if (result.visit_count >= 10) {
        badgeClass = 'frequency-high';
        badgeText = 'Frequent';
    } else if (result.visit_count >= 3) {
        badgeClass = 'frequency-medium';
        badgeText = 'Regular';
    }
    
    return `<span class="frequency-badge ${badgeClass}" title="${result.visit_count} visits">${badgeText}</span>`;
}

function formatLastVisited(lastVisited) {
    if (!lastVisited) return '';
    
    const date = new Date(lastVisited);
    const now = new Date();
    const diffHours = (now - date) / (1000 * 60 * 60);
    
    if (diffHours < 1) {
        return '<span class="last-visited recent">Just visited</span>';
    } else if (diffHours < 24) {
        return `<span class="last-visited today">${Math.round(diffHours)}h ago</span>`;
    } else if (diffHours < 168) { // 1 week
        const days = Math.round(diffHours / 24);
        return `<span class="last-visited week">${days}d ago</span>`;
    } else {
        return `<span class="last-visited old">Over a week ago</span>`;
    }
}

function trackAndNavigate(url, query, index) {
    // Track the click
    chrome.runtime.sendMessage({
        type: 'TRACK_RESULT_CLICK',
        url: url,
        query: query,
        resultIndex: index
    });
    
    // Navigate
    window.open(url, '_blank');
}
```

### 5.3 Frequency Analytics Dashboard

Add analytics section to settings:

```javascript
// extension/newtab/app.js - Analytics section
async function loadFrequencyAnalytics() {
    try {
        const response = await fetch(`${BACKEND_URL}/analytics/frequency?days=30`);
        const analytics = await response.json();
        
        const container = document.getElementById('frequencyAnalytics');
        container.innerHTML = `
            <div class="analytics-grid">
                <div class="analytics-card">
                    <h4>Total Visits</h4>
                    <span class="analytics-value">${analytics.total_visits}</span>
                </div>
                <div class="analytics-card">
                    <h4>Pages Visited</h4>
                    <span class="analytics-value">${analytics.unique_pages}</span>
                </div>
                <div class="analytics-card">
                    <h4>Avg Visits/Page</h4>
                    <span class="analytics-value">${analytics.avg_visits_per_page.toFixed(1)}</span>
                </div>
            </div>
            
            <div class="most-visited-section">
                <h4>Most Visited Pages</h4>
                <div class="most-visited-list">
                    ${analytics.most_visited_pages.map(page => `
                        <div class="visited-page-item">
                            <span class="page-title">${escapeHtml(page.title)}</span>
                            <span class="visit-count">${page.visit_count} visits</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load analytics:', error);
    }
}
```

---

## 6. Implementation Steps

### Phase 1: Database Foundation (Week 1)

1. **Database Migration**
   ```bash
   # Create migration script
   touch backend/migrations/add_frequency_tracking.py
   
   # Run migration
   python backend/migrations/add_frequency_tracking.py
   ```

2. **Update Models**
   - Extend `PageResponse` with frequency fields
   - Add `VisitTrackingRequest` model
   - Create `FrequencyAnalyticsResponse` model

3. **Database Methods**
   - Implement `update_visit_metrics()`
   - Add `recalculate_arc_scores()`
   - Create `get_frequency_analytics()`

### Phase 2: Backend API (Week 2)

1. **Visit Tracking Endpoint**
   ```python
   # Add to backend/main.py
   @app.post("/track-visit")
   async def track_visit(visit_data: VisitTrackingRequest):
       # Implementation from section 2.1
   ```

2. **Enhanced Search**
   ```python
   # Add ARC-enhanced search endpoint
   @app.get("/search/arc")
   async def search_with_arc():
       # Implementation from section 2.2
   ```

3. **Analytics Endpoint**
   ```python
   # Add analytics endpoint
   @app.get("/analytics/frequency")
   async def get_frequency_analytics():
       # Implementation from section 2.1
   ```

### Phase 3: Frontend Integration (Week 3)

1. **Visit Tracking**
   - Update `service-worker.js` with `VisitTracker` class
   - Add message handlers for visit tracking
   - Implement click tracking for search results

2. **Enhanced Search UI**
   - Update `displayResults()` with frequency indicators
   - Add frequency badges and last visited timestamps
   - Implement score breakdown display

3. **Analytics Dashboard**
   - Add analytics section to settings
   - Create frequency analytics display
   - Add visit pattern visualizations

### Phase 4: Algorithm Tuning (Week 4)

1. **Score Optimization**
   - A/B test different weight combinations
   - Implement adaptive weight adjustment
   - Fine-tune time decay parameters

2. **Performance Optimization**
   - Add database indexes for frequency queries
   - Implement score caching
   - Optimize background recalculation

3. **User Testing**
   - Collect user feedback on ranking quality
   - Monitor search result click-through rates
   - Adjust algorithm based on usage patterns

### Phase 5: Advanced Features (Week 5)

1. **Adaptive Learning**
   - Implement user preference learning
   - Add personalized weight adjustment
   - Create behavior-based ranking

2. **Advanced Analytics**
   - Add trend analysis
   - Implement search pattern insights
   - Create usage reports

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/test_frequency_tracking.py
import pytest
from datetime import datetime, timedelta
from backend.database import Database

class TestFrequencyTracking:
    
    def test_visit_count_increment(self):
        """Test that visit count increments correctly."""
        db = Database(":memory:")
        page_id = db.insert_page(test_page)
        
        # Track multiple visits
        db.update_visit_metrics(page_id)
        db.update_visit_metrics(page_id)
        
        page = db.get_page_by_id(page_id)
        assert page.visit_count == 2
    
    def test_frequency_calculation(self):
        """Test access frequency calculation."""
        db = Database(":memory:")
        page_id = db.insert_page(test_page)
        
        # Set first visit to 2 days ago
        past_date = datetime.now() - timedelta(days=2)
        db._set_first_visit(page_id, past_date)
        
        # Add 4 visits (should be 2 visits/day)
        for _ in range(4):
            db.update_visit_metrics(page_id)
        
        page = db.get_page_by_id(page_id)
        assert abs(page.access_frequency - 2.0) < 0.1
    
    def test_recency_decay(self):
        """Test recency score decay function."""
        now = datetime.now()
        yesterday = now - timedelta(hours=24)
        
        decay = db._calculate_time_decay(now, yesterday)
        assert abs(decay - 0.5) < 0.01  # Should be ~50% after 24 hours
    
    def test_arc_score_calculation(self):
        """Test combined ARC score calculation."""
        # Test with high frequency, recent visit
        score1 = calculate_arc_score(10, datetime.now(), datetime.now() - timedelta(days=2))
        
        # Test with low frequency, old visit  
        score2 = calculate_arc_score(1, datetime.now() - timedelta(days=7), datetime.now() - timedelta(days=30))
        
        assert score1 > score2  # Recent + frequent should score higher
```

### 7.2 Integration Tests

```python
# tests/test_search_ranking.py
def test_arc_search_ranking():
    """Test that ARC search properly ranks results."""
    # Create test pages with different visit patterns
    frequent_page = create_test_page(visit_count=20, last_visited=datetime.now())
    recent_page = create_test_page(visit_count=2, last_visited=datetime.now() - timedelta(hours=1))
    old_page = create_test_page(visit_count=5, last_visited=datetime.now() - timedelta(days=30))
    
    # Search should rank frequent + recent higher
    results = search_with_arc("test query")
    
    # Verify ranking order
    assert results[0]['id'] in [frequent_page.id, recent_page.id]
    assert results[-1]['id'] == old_page.id
```

### 7.3 Load Testing

```python
# tests/test_performance.py
def test_visit_tracking_performance():
    """Test visit tracking under load."""
    import time
    import concurrent.futures
    
    def track_visit():
        return db.update_visit_metrics(test_page_id)
    
    start_time = time.time()
    
    # Simulate 100 concurrent visits
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(track_visit) for _ in range(100)]
        results = [f.result() for f in futures]
    
    duration = time.time() - start_time
    
    assert all(results)  # All visits tracked successfully
    assert duration < 5.0  # Completed within 5 seconds
```

---

## 8. Performance Considerations

### 8.1 Database Optimization

1. **Indexes**
   ```sql
   CREATE INDEX idx_pages_arc_score ON pages(arc_score DESC);
   CREATE INDEX idx_pages_visit_tracking ON pages(visit_count, last_visited);
   CREATE INDEX idx_pages_last_visited ON pages(last_visited DESC);
   ```

2. **Batch Updates**
   ```python
   def batch_update_arc_scores(page_ids: List[int]):
       """Update ARC scores in batches for better performance."""
       with db.get_connection() as conn:
           for i in range(0, len(page_ids), 100):
               batch = page_ids[i:i+100]
               # Update batch of 100 pages at a time
               update_batch_scores(conn, batch)
   ```

3. **Background Processing**
   ```python
   # Use background task for score recalculation
   @app.on_event("startup")
   async def setup_background_tasks():
       asyncio.create_task(periodic_arc_score_update())
   
   async def periodic_arc_score_update():
       """Recalculate ARC scores every 15 minutes."""
       while True:
           await asyncio.sleep(900)  # 15 minutes
           try:
               db.recalculate_arc_scores()
           except Exception as e:
               logger.error(f"ARC score update failed: {e}")
   ```

### 8.2 Memory Management

1. **LRU Cache for Frequent Queries**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def get_cached_arc_results(query_hash: str, weights_tuple: tuple):
       """Cache ARC search results for frequent queries."""
       return _get_arc_results(query_hash, weights_tuple)
   ```

2. **Efficient Vector Operations**
   ```python
   # Use numpy for efficient score calculations
   import numpy as np
   
   def batch_calculate_scores(visit_counts: np.array, time_deltas: np.array) -> np.array:
       """Vectorized score calculation for better performance."""
       frequency_scores = np.minimum(visit_counts / 5.0, 1.0)
       recency_scores = np.maximum(0.5 ** (time_deltas / 24.0), 0.01)
       return (frequency_scores * 0.6) + (recency_scores * 0.4)
   ```

### 8.3 Monitoring and Metrics

```python
# Add performance monitoring
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        
        # Log slow operations
        if duration > 1.0:
            logger.warning(f"Slow operation: {func.__name__} took {duration:.2f}s")
        
        return result
    return wrapper

@monitor_performance
async def search_with_arc(...):
    # Implementation
```

---

## Conclusion

This implementation plan provides a comprehensive approach to adding frequency and visit tracking with ARC-style scoring to the New Tab Chrome extension. The phased approach ensures systematic development while maintaining system stability and performance.

**Key Benefits:**
- Personalized search results based on user behavior
- Improved relevance through frequency and recency signals
- Scalable architecture supporting future enhancements
- Comprehensive analytics for user insights

**Success Metrics:**
- Improved search result click-through rates
- Reduced time to find relevant pages
- Higher user engagement with the extension
- Positive user feedback on result relevance

The implementation balances sophisticated ranking algorithms with practical performance considerations, ensuring the system can scale while providing immediate value to users.