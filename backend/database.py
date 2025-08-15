"""Database operations with SQLite FTS5 for the Local Web Memory backend."""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Tuple
from pathlib import Path

from models import PageCreate, PageResponse


class Database:
    """SQLite database with FTS5 support for web page indexing."""
    
    def __init__(self, db_path: str = "web_memory.db"):
        """Initialize database connection and create tables."""
        self.db_path = db_path
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
                    vector_embedding TEXT  -- JSON array of floats
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
            return cursor.rowchanges > 0
    
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
        
        return PageResponse(
            id=row['id'],
            url=row['url'],
            title=row['title'],
            description=row['description'],
            keywords=row['keywords'],
            content=row['content'],
            favicon_url=row['favicon_url'],
            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) 
                       if isinstance(row['created_at'], str) 
                       else row['created_at'],
            vector_embedding=vector_embedding
        )