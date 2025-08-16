"""Database operations with SQLite FTS5 for the Local Web Memory backend."""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from src.core.models import PageCreate, PageResponse

try:
    from arc.eviction import ARCEvictionPolicy, EvictionPolicy
except ImportError:
    # Fallback implementations if arc module not available
    from abc import ABC, abstractmethod
    from typing import List, Dict
    
    class EvictionPolicy(ABC):
        @abstractmethod
        def get_eviction_candidates(self, pages: List[Dict], count: int) -> List[int]:
            pass
    
    class ARCEvictionPolicy(EvictionPolicy):
        def __init__(self, max_age_days: int = 90, min_visit_threshold: int = 1):
            self.max_age_days = max_age_days
            self.min_visit_threshold = min_visit_threshold
        
        def get_eviction_candidates(self, pages: List[Dict], count: int) -> List[int]:
            # Simple LRU fallback
            return [page['id'] for page in sorted(pages, key=lambda x: x.get('last_accessed', ''))[:count]]


class Database:
    """SQLite database with FTS5 support for web page indexing."""
    
    def __init__(self, db_path: str = "web_memory.db", max_pages: int = 10000):
        """Initialize database connection and create tables."""
        self.db_path = db_path
        self.max_pages = max_pages
        self.eviction_policy = ARCEvictionPolicy()
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables and FTS5 index."""
        with self.get_connection() as conn:
            # Create main pages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    keywords TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    favicon_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vector_embedding TEXT,  -- JSON array of floats
                    -- New frequency tracking fields
                    visit_count INTEGER DEFAULT 0,
                    first_visited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_visited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_frequency REAL DEFAULT 0.0,
                    recency_score REAL DEFAULT 0.0,
                    arc_score REAL DEFAULT 0.0
                )
            """)
            
            # Create FTS5 virtual table for full-text search (simplified)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                    title, description, keywords, content
                )
            """)
            
            # Create trigger to keep FTS table in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS pages_fts_insert AFTER INSERT ON pages BEGIN
                    INSERT INTO pages_fts(rowid, title, description, keywords, content)
                    VALUES (new.id, new.title, new.description, new.keywords, new.content);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS pages_fts_update AFTER UPDATE ON pages BEGIN
                    UPDATE pages_fts SET 
                        title = new.title,
                        description = new.description,
                        keywords = new.keywords,
                        content = new.content
                    WHERE rowid = new.id;
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS pages_fts_delete AFTER DELETE ON pages BEGIN
                    DELETE FROM pages_fts WHERE rowid = old.id;
                END
            """)
            
            # Add new columns to existing database if they don't exist
            self._migrate_add_frequency_fields(conn)
            
            # Add indexes for frequency tracking (after columns are added)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_visit_tracking 
                ON pages(visit_count, last_visited, arc_score)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_arc_score 
                ON pages(arc_score DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pages_last_updated 
                ON pages(last_updated_at)
            """)
            
            conn.commit()
    
    def insert_page(self, page: PageCreate, description: str = "", keywords: str = "", 
                   vector_embedding: Optional[List[float]] = None) -> int:
        """Insert a new page into the database."""
        vector_json = json.dumps(vector_embedding) if vector_embedding else None
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO pages 
                (url, title, description, keywords, content, favicon_url, vector_embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                page.url, page.title, description, keywords, 
                page.content, page.favicon_url, vector_json
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_page_by_id(self, page_id: int) -> Optional[PageResponse]:
        """Get a single page by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM pages WHERE id = ?", (page_id,)
            ).fetchone()
            
            if row:
                return self._row_to_page_response(row)
            return None
    
    def get_page_embedding(self, page_id: int) -> Optional[List[float]]:
        """Get the stored embedding for a page by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT vector_embedding FROM pages WHERE id = ?", (page_id,)
            ).fetchone()
            
            if row and row['vector_embedding']:
                try:
                    import json
                    embedding = json.loads(row['vector_embedding'])
                    if isinstance(embedding, list) and len(embedding) > 0:
                        return embedding
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"Error parsing stored embedding for page {page_id}: {e}")
            
            return None
    
    def get_all_pages(self, limit: int = 100, offset: int = 0) -> List[PageResponse]:
        """Get all pages with pagination."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM pages 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            
            return [self._row_to_page_response(row) for row in rows]
    
    def search_keyword(self, query: str, limit: int = 10) -> Tuple[List[PageResponse], int]:
        """Search pages using FTS5 keyword search."""
        # Prepare FTS5 query - escape special characters and add wildcards
        fts_query = query.replace('"', '""')  # Escape quotes
        fts_query = f'"{fts_query}"*'  # Add wildcard for prefix matching
        
        with self.get_connection() as conn:
            # Get total count
            count_row = conn.execute("""
                SELECT COUNT(*) as total 
                FROM pages_fts 
                WHERE pages_fts MATCH ?
            """, (fts_query,)).fetchone()
            
            total_found = count_row['total'] if count_row else 0
            
            # Get results with ranking
            rows = conn.execute("""
                SELECT p.*, bm25(pages_fts) as rank 
                FROM pages p
                JOIN pages_fts ON p.id = pages_fts.rowid
                WHERE pages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit)).fetchall()
            
            results = [self._row_to_page_response(row) for row in rows]
            return results, total_found
    
    def delete_page(self, page_id: int) -> bool:
        """Delete a page by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_total_pages(self) -> int:
        """Get total number of pages in database."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as total FROM pages").fetchone()
            return row['total'] if row else 0
    
    def get_all_vectors(self) -> List[Tuple[int, List[float]]]:
        """Get all page IDs and their vector embeddings for vector search."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, vector_embedding 
                FROM pages 
                WHERE vector_embedding IS NOT NULL
            """).fetchall()
            
            result = []
            for row in rows:
                try:
                    vector = json.loads(row['vector_embedding'])
                    result.append((row['id'], vector))
                except (json.JSONDecodeError, TypeError):
                    continue  # Skip invalid vectors
            
            return result
    
    def _migrate_add_frequency_fields(self, conn):
        """Add frequency tracking fields to existing database."""
        # Check if columns already exist
        cursor = conn.execute("PRAGMA table_info(pages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ('visit_count', 'INTEGER DEFAULT 0'),
            ('first_visited', 'TIMESTAMP DEFAULT NULL'),
            ('last_visited', 'TIMESTAMP DEFAULT NULL'),
            ('indexed_at', 'TIMESTAMP DEFAULT NULL'),
            ('last_updated_at', 'TIMESTAMP DEFAULT NULL'),
            ('access_frequency', 'REAL DEFAULT 0.0'),
            ('recency_score', 'REAL DEFAULT 0.0'),
            ('arc_score', 'REAL DEFAULT 0.0')
        ]
        
        for col_name, col_def in new_columns:
            if col_name not in columns:
                try:
                    conn.execute(f"ALTER TABLE pages ADD COLUMN {col_name} {col_def}")
                    print(f"✅ Added column {col_name} to pages table")
                except sqlite3.OperationalError as e:
                    print(f"⚠️  Failed to add column {col_name}: {e}")
                    pass  # Column might already exist
        
        # Initialize existing pages with default values if needed
        # Check which columns exist now
        cursor = conn.execute("PRAGMA table_info(pages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Only update columns that exist
        update_parts = []
        if 'visit_count' in columns:
            update_parts.append("visit_count = COALESCE(visit_count, 0)")
        if 'first_visited' in columns:
            update_parts.append("first_visited = COALESCE(first_visited, created_at)")
        if 'last_visited' in columns:
            update_parts.append("last_visited = COALESCE(last_visited, created_at)")
        if 'indexed_at' in columns:
            update_parts.append("indexed_at = COALESCE(indexed_at, created_at)")
        if 'last_updated_at' in columns:
            update_parts.append("last_updated_at = COALESCE(last_updated_at, created_at)")
        
        if update_parts:
            update_sql = f"UPDATE pages SET {', '.join(update_parts)} WHERE id > 0"
            conn.execute(update_sql)
    
    def find_or_create_page_for_tracking(self, url: str) -> Optional[int]:
        """Find existing page or create minimal entry for tracking."""
        with self.get_connection() as conn:
            # Try to find existing page
            row = conn.execute("SELECT id FROM pages WHERE url = ?", (url,)).fetchone()
            
            if row:
                return row['id']
            
            # Create minimal page entry for tracking (will be indexed later)
            now = datetime.now()
            cursor = conn.execute("""
                INSERT INTO pages (url, title, content, first_visited, last_visited, 
                                   visit_count, indexed_at, last_updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (url, url, '', now, now, 0, now, now))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_visit_metrics(self, page_id: int, suppress_counts: bool = True) -> bool:
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
            if isinstance(first_visited, str):
                first_visited = datetime.fromisoformat(first_visited.replace('Z', '+00:00'))
            days_since_first = max((now - first_visited).days, 1)
            new_frequency = new_visit_count / days_since_first
            
            # Calculate recency score (exponential decay)
            time_decay = self._calculate_time_decay(now, row['last_visited'])
            
            # Calculate ARC score
            frequency_score = min(new_frequency / 5.0, 1.0)  # Cap at 5 visits/day = 1.0
            recency_score = time_decay
            arc_score = (frequency_score * 0.6) + (recency_score * 0.4)
            
            # Update database
            conn.execute("""
                UPDATE pages 
                SET visit_count = ?, 
                    last_visited = ?,
                    first_visited = COALESCE(first_visited, ?),
                    access_frequency = ?,
                    recency_score = ?,
                    arc_score = ?
                WHERE id = ?
            """, (new_visit_count, now, first_visited, new_frequency, 
                  recency_score, arc_score, page_id))
            
            conn.commit()
            
            # Check if we need to suppress counts (any page > 1 million visits)
            if suppress_counts and new_visit_count > 1000000:
                self._suppress_all_counts(conn)
            
            return True
    
    def _calculate_time_decay(self, current_time: datetime, last_visit) -> float:
        """Calculate time decay factor for recency scoring."""
        if not last_visit:
            return 1.0
        
        if isinstance(last_visit, str):
            last_visit = datetime.fromisoformat(last_visit.replace('Z', '+00:00'))
        
        hours_since_visit = (current_time - last_visit).total_seconds() / 3600
        
        # Exponential decay: score drops to 50% after 24 hours, 25% after 48 hours
        decay_factor = 0.5 ** (hours_since_visit / 24.0)
        return max(decay_factor, 0.01)  # Minimum score of 1%
    
    def _suppress_all_counts(self, conn):
        """Divide all visit counts by 2 when any page exceeds 1 million visits."""
        print("⚠️ Visit count exceeded 1 million, suppressing all counts by dividing by 2")
        
        # Divide all visit counts by 2
        conn.execute("""
            UPDATE pages 
            SET visit_count = visit_count / 2,
                access_frequency = access_frequency / 2
        """)
        
        # Recalculate ARC scores after suppression
        self._recalculate_all_arc_scores(conn)
        conn.commit()
    
    def _recalculate_all_arc_scores(self, conn):
        """Recalculate ARC scores for all pages."""
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
            frequency_score = min((row['access_frequency'] or 0) / 5.0, 1.0)
            
            # Calculate combined ARC score
            arc_score = (frequency_score * 0.6) + (recency_score * 0.4)
            
            # Update database
            conn.execute("""
                UPDATE pages 
                SET recency_score = ?, arc_score = ?
                WHERE id = ?
            """, (recency_score, arc_score, row['id']))
    
    def check_needs_reindex(self, url: str) -> Tuple[bool, Optional[int]]:
        """Check if a URL needs re-indexing (>3 days since last update)."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT id, last_updated_at 
                FROM pages 
                WHERE url = ?
            """, (url,)).fetchone()
            
            if not row:
                return False, None  # URL doesn't exist
            
            last_updated = row['last_updated_at']
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            
            # Check if more than 3 days old
            days_since_update = (datetime.now() - last_updated).days
            needs_reindex = days_since_update > 3
            
            return needs_reindex, row['id']
    
    def update_page_index_time(self, page_id: int):
        """Update the last_updated_at timestamp for a page."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE pages 
                SET last_updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (page_id,))
            conn.commit()
    
    def get_pages_with_visit_metrics(self, limit: int = 10) -> List[dict]:
        """Get pages with their visit metrics for analytics."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, url, title, visit_count, last_visited, 
                       access_frequency, recency_score, arc_score
                FROM pages
                WHERE visit_count > 0
                ORDER BY arc_score DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def check_and_evict_pages(self) -> Dict[str, int]:
        """Check if database needs eviction and perform if necessary."""
        total_pages = self.get_total_pages()
        
        if total_pages <= self.max_pages:
            return {'evicted_count': 0, 'total_pages': total_pages}
        
        # Calculate how many pages to evict (evict 10% when over limit)
        evict_count = max(1, int((total_pages - self.max_pages) * 1.1))
        
        # Get all pages with metadata for eviction analysis
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, url, title, content, visit_count, last_visited, 
                       first_visited, arc_score, created_at
                FROM pages
                ORDER BY id
            """).fetchall()
            
            pages_data = [dict(row) for row in rows]
        
        # Get eviction candidates
        candidates = self.eviction_policy.get_eviction_candidates(pages_data, evict_count)
        
        # Perform eviction
        evicted_count = 0
        for page_id in candidates:
            if self.delete_page(page_id):
                evicted_count += 1
        
        print(f"🗑️  Evicted {evicted_count} pages using ARC policy")
        
        return {
            'evicted_count': evicted_count,
            'total_pages': self.get_total_pages(),
            'candidates_found': len(candidates)
        }
    
    def set_eviction_policy(self, policy: EvictionPolicy):
        """Set the eviction policy."""
        self.eviction_policy = policy
    
    def get_eviction_candidates_preview(self, count: int = 10) -> List[Dict]:
        """Preview pages that would be evicted without actually evicting them."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, url, title, visit_count, last_visited, 
                       arc_score, created_at
                FROM pages
                ORDER BY id
            """).fetchall()
            
            pages_data = [dict(row) for row in rows]
        
        candidate_ids = self.eviction_policy.get_eviction_candidates(pages_data, count)
        
        # Get full details for candidates
        candidates = []
        for page in pages_data:
            if page['id'] in candidate_ids:
                candidates.append(page)
        
        return candidates
    
    def get_eviction_stats(self) -> Dict[str, Any]:
        """Get statistics about eviction policy and candidates."""
        total_pages = self.get_total_pages()
        
        with self.get_connection() as conn:
            # Get pages by visit count distribution
            visit_distribution = conn.execute("""
                SELECT 
                    CASE 
                        WHEN visit_count = 0 THEN 'never_visited'
                        WHEN visit_count <= 2 THEN 'low_visits'
                        WHEN visit_count <= 10 THEN 'medium_visits'
                        ELSE 'high_visits'
                    END as category,
                    COUNT(*) as count
                FROM pages
                GROUP BY category
            """).fetchall()
            
            # Get pages by age distribution
            age_distribution = conn.execute("""
                SELECT 
                    CASE 
                        WHEN julianday('now') - julianday(last_visited) <= 7 THEN 'recent'
                        WHEN julianday('now') - julianday(last_visited) <= 30 THEN 'medium_age'
                        WHEN julianday('now') - julianday(last_visited) <= 90 THEN 'old'
                        ELSE 'very_old'
                    END as category,
                    COUNT(*) as count
                FROM pages
                GROUP BY category
            """).fetchall()
            
            # Get ARC score distribution
            arc_distribution = conn.execute("""
                SELECT 
                    CASE 
                        WHEN arc_score = 0.0 THEN 'no_score'
                        WHEN arc_score <= 0.2 THEN 'low_relevance'
                        WHEN arc_score <= 0.5 THEN 'medium_relevance'
                        ELSE 'high_relevance'
                    END as category,
                    COUNT(*) as count
                FROM pages
                GROUP BY category
            """).fetchall()
        
        return {
            'total_pages': total_pages,
            'max_pages': self.max_pages,
            'pages_over_limit': max(0, total_pages - self.max_pages),
            'eviction_needed': total_pages > self.max_pages,
            'visit_distribution': {row['category']: row['count'] for row in visit_distribution},
            'age_distribution': {row['category']: row['count'] for row in age_distribution},
            'arc_distribution': {row['category']: row['count'] for row in arc_distribution}
        }
    
    def update_page_vector(self, page_id: int, vector_embedding: List[float]):
        """Update the vector embedding for a specific page."""
        vector_json = json.dumps(vector_embedding)
        
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE pages 
                SET vector_embedding = ? 
                WHERE id = ?
            """, (vector_json, page_id))
            conn.commit()
    
    def _row_to_page_response(self, row) -> PageResponse:
        """Convert database row to PageResponse model."""
        vector_embedding = None
        if row['vector_embedding']:
            try:
                vector_embedding = json.loads(row['vector_embedding'])
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as None if parsing fails
        
        # Helper function to parse datetime
        def parse_datetime(dt_value):
            if dt_value is None:
                return None
            if isinstance(dt_value, str):
                return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            return dt_value
        
        # Helper function to safely get column values
        def get_column_value(col_name, default=None):
            try:
                return row[col_name] if row[col_name] is not None else default
            except (IndexError, KeyError):
                return default
        
        return PageResponse(
            id=row['id'],
            url=row['url'],
            title=row['title'],
            description=row['description'],
            keywords=row['keywords'],
            content=row['content'],
            favicon_url=row['favicon_url'],
            created_at=parse_datetime(row['created_at']),
            vector_embedding=vector_embedding,
            # Frequency tracking fields (with safe column access)
            visit_count=get_column_value('visit_count', 0) or 0,
            first_visited=parse_datetime(get_column_value('first_visited')),
            last_visited=parse_datetime(get_column_value('last_visited')),
            indexed_at=parse_datetime(get_column_value('indexed_at')),
            last_updated_at=parse_datetime(get_column_value('last_updated_at')),
            access_frequency=get_column_value('access_frequency', 0.0) or 0.0,
            recency_score=get_column_value('recency_score', 0.0) or 0.0,
            arc_score=get_column_value('arc_score', 0.0) or 0.0
        )