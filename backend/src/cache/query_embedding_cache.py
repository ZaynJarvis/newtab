"""LRU Cache for Query Embeddings to improve offline resilience."""

import json
import time
from typing import List, Optional, Dict, Any
from collections import OrderedDict
from pathlib import Path
from datetime import datetime, timedelta
import threading
from src.core.logging import get_logger


class QueryEmbeddingCache:
    """
    LRU Cache for query embeddings with disk persistence.
    
    Features:
    - LRU eviction policy with configurable capacity (default 1000)
    - Disk persistence with auto-save every 20 operations
    - TTL-based expiration (7 days default)
    - Thread-safe operations
    - Cache statistics tracking
    """
    
    def __init__(self, capacity: int = 1000, cache_file: str = "query_embeddings_cache.json", ttl_days: int = 7):
        """
        Initialize the query embedding cache.
        
        Args:
            capacity: Maximum number of queries to cache
            cache_file: File path for cache persistence
            ttl_days: Time-to-live in days for cached embeddings
        """
        self.logger = get_logger(__name__)
        self.capacity = max(1, capacity)
        self.cache_file = Path(cache_file)
        self.ttl_seconds = ttl_days * 24 * 3600
        
        # LRU cache using OrderedDict
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.operations_count = 0
        
        # Auto-save configuration
        self.auto_save_interval = 20
        
        # Load existing cache from disk
        self._load_from_disk()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query string for consistent caching."""
        return query.lower().strip()
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if a cache entry has expired."""
        if 'timestamp' not in cache_entry:
            return True
        
        timestamp = cache_entry['timestamp']
        return (time.time() - timestamp) > self.ttl_seconds
    
    def _evict_expired(self) -> int:
        """Remove expired entries from cache. Returns number of evicted entries."""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def _evict_lru(self) -> Optional[str]:
        """Evict least recently used entry. Returns evicted key or None."""
        with self._lock:
            if self._cache:
                evicted_key, _ = self._cache.popitem(last=False)
                return evicted_key
            return None
    
    def get(self, query: str) -> Optional[List[float]]:
        """
        Get cached embedding for a query.
        
        Args:
            query: Search query string
            
        Returns:
            Embedding vector if found and not expired, None otherwise
        """
        normalized_query = self._normalize_query(query)
        
        with self._lock:
            if normalized_query in self._cache:
                entry = self._cache[normalized_query]
                
                # Check if expired
                if self._is_expired(entry):
                    del self._cache[normalized_query]
                    self.misses += 1
                    return None
                
                # Move to end (mark as recently used)
                self._cache.move_to_end(normalized_query)
                entry['access_count'] = entry.get('access_count', 0) + 1
                entry['last_accessed'] = time.time()
                
                self.hits += 1
                return entry['embedding']
            
            self.misses += 1
            return None
    
    def put(self, query: str, embedding: List[float]) -> bool:
        """
        Cache an embedding for a query.
        
        Args:
            query: Search query string
            embedding: Embedding vector
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not embedding or not isinstance(embedding, list):
            return False
        
        normalized_query = self._normalize_query(query)
        
        with self._lock:
            # Remove expired entries first
            self._evict_expired()
            
            # Evict LRU if at capacity
            while len(self._cache) >= self.capacity:
                evicted_key = self._evict_lru()
                if evicted_key is None:
                    break
            
            # Add/update entry
            entry = {
                'embedding': embedding,
                'timestamp': time.time(),
                'access_count': 1,
                'last_accessed': time.time(),
                'query_length': len(query),
                'created_at': datetime.now().isoformat()
            }
            
            self._cache[normalized_query] = entry
            self.operations_count += 1
            
            # Auto-save every 20 operations
            if self.operations_count % self.auto_save_interval == 0:
                self._persist_to_disk()
            
            return True
    
    def delete(self, query: str) -> bool:
        """
        Delete a cached embedding.
        
        Args:
            query: Search query string
            
        Returns:
            True if found and deleted, False otherwise
        """
        normalized_query = self._normalize_query(query)
        
        with self._lock:
            if normalized_query in self._cache:
                del self._cache[normalized_query]
                self.operations_count += 1
                
                # Auto-save
                if self.operations_count % self.auto_save_interval == 0:
                    self._persist_to_disk()
                
                return True
            return False
    
    def clear(self):
        """Clear all cached embeddings."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
            self.operations_count = 0
            self._persist_to_disk()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            
            # Calculate storage efficiency
            active_entries = len(self._cache)
            expired_count = self._evict_expired()
            
            return {
                'capacity': self.capacity,
                'size': active_entries,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 3),
                'total_requests': total_requests,
                'operations_count': self.operations_count,
                'expired_evicted': expired_count,
                'cache_file': str(self.cache_file),
                'ttl_days': self.ttl_seconds / (24 * 3600),
                'auto_save_interval': self.auto_save_interval
            }
    
    def _persist_to_disk(self) -> bool:
        """Save cache to disk. Returns True if successful."""
        try:
            with self._lock:
                # Prepare data for serialization
                cache_data = {
                    'metadata': {
                        'version': '1.0',
                        'created_at': datetime.now().isoformat(),
                        'capacity': self.capacity,
                        'ttl_seconds': self.ttl_seconds,
                        'hits': self.hits,
                        'misses': self.misses,
                        'operations_count': self.operations_count
                    },
                    'entries': dict(self._cache)
                }
                
                # Write to temporary file first, then rename (atomic operation)
                temp_file = self.cache_file.with_suffix('.tmp')
                with temp_file.open('w') as f:
                    json.dump(cache_data, f, indent=2)
                
                # Atomic rename
                temp_file.rename(self.cache_file)
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to persist query embedding cache",
                extra={
                    "error": str(e),
                    "cache_file": str(self.cache_file),
                    "event": "cache_persist_failed"
                },
                exc_info=True
            )
            return False
    
    def _load_from_disk(self) -> bool:
        """Load cache from disk. Returns True if successful."""
        if not self.cache_file.exists():
            return False
        
        try:
            with self.cache_file.open('r') as f:
                cache_data = json.load(f)
            
            # Restore metadata
            metadata = cache_data.get('metadata', {})
            self.hits = metadata.get('hits', 0)
            self.misses = metadata.get('misses', 0)
            self.operations_count = metadata.get('operations_count', 0)
            
            # Restore entries (filtering expired ones)
            entries = cache_data.get('entries', {})
            current_time = time.time()
            
            with self._lock:
                self._cache.clear()
                
                for query, entry in entries.items():
                    # Skip expired entries
                    if 'timestamp' in entry:
                        if (current_time - entry['timestamp']) <= self.ttl_seconds:
                            self._cache[query] = entry
                
            self.logger.info(
                "Loaded query embeddings from cache",
                extra={
                    "entries_loaded": len(self._cache),
                    "cache_file": str(self.cache_file),
                    "event": "cache_loaded"
                }
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to load query embedding cache",
                extra={
                    "error": str(e),
                    "cache_file": str(self.cache_file),
                    "event": "cache_load_failed"
                },
                exc_info=True
            )
            return False
    
    def force_save(self) -> bool:
        """Force save cache to disk regardless of auto-save interval."""
        return self._persist_to_disk()
    
    def cleanup_expired(self) -> int:
        """Manually clean up expired entries. Returns number of removed entries."""
        return self._evict_expired()
    
    def get_top_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently accessed queries for debugging/analytics."""
        with self._lock:
            # Sort by access count
            sorted_queries = sorted(
                self._cache.items(),
                key=lambda x: x[1].get('access_count', 0),
                reverse=True
            )
            
            result = []
            for query, entry in sorted_queries[:limit]:
                result.append({
                    'query': query,
                    'access_count': entry.get('access_count', 0),
                    'last_accessed': datetime.fromtimestamp(
                        entry.get('last_accessed', 0)
                    ).isoformat(),
                    'created_at': entry.get('created_at', 'unknown')
                })
            
            return result