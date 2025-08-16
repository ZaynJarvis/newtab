"""Unit tests for QueryEmbeddingCache."""

import os
import time
import tempfile
import threading
from pathlib import Path
from unittest import TestCase
from src.cache.query_embedding_cache import QueryEmbeddingCache


class TestQueryEmbeddingCache(TestCase):
    """Test cases for QueryEmbeddingCache functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary cache file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = Path(self.temp_dir) / "test_cache.json"
        
        # Create cache with small capacity for testing
        self.cache = QueryEmbeddingCache(
            capacity=3,
            cache_file=str(self.cache_file),
            ttl_days=1
        )
        
        # Sample embeddings for testing
        self.sample_embedding_1 = [0.1, 0.2, 0.3, 0.4]
        self.sample_embedding_2 = [0.5, 0.6, 0.7, 0.8]
        self.sample_embedding_3 = [0.9, 0.1, 0.2, 0.3]
        self.sample_embedding_4 = [0.4, 0.5, 0.6, 0.7]
    
    def tearDown(self):
        """Clean up test environment."""
        # Remove temp files
        if self.cache_file.exists():
            self.cache_file.unlink()
        Path(self.temp_dir).rmdir()
    
    def test_basic_put_get(self):
        """Test basic put and get operations."""
        # Test put and get
        self.assertTrue(self.cache.put("test query", self.sample_embedding_1))
        result = self.cache.get("test query")
        self.assertEqual(result, self.sample_embedding_1)
        
        # Test cache hit statistics
        self.assertEqual(self.cache.hits, 1)
        self.assertEqual(self.cache.misses, 0)
    
    def test_cache_miss(self):
        """Test cache miss behavior."""
        result = self.cache.get("nonexistent query")
        self.assertIsNone(result)
        
        # Test cache miss statistics
        self.assertEqual(self.cache.hits, 0)
        self.assertEqual(self.cache.misses, 1)
    
    def test_query_normalization(self):
        """Test query normalization (case insensitive, trimmed)."""
        self.cache.put("  TEST Query  ", self.sample_embedding_1)
        
        # These should all return the same cached embedding
        self.assertEqual(self.cache.get("test query"), self.sample_embedding_1)
        self.assertEqual(self.cache.get("TEST QUERY"), self.sample_embedding_1)
        self.assertEqual(self.cache.get("  test query  "), self.sample_embedding_1)
    
    def test_lru_eviction(self):
        """Test LRU eviction when capacity is exceeded."""
        # Fill cache to capacity
        self.cache.put("query1", self.sample_embedding_1)
        self.cache.put("query2", self.sample_embedding_2)
        self.cache.put("query3", self.sample_embedding_3)
        
        # All should be cached
        self.assertIsNotNone(self.cache.get("query1"))
        self.assertIsNotNone(self.cache.get("query2"))
        self.assertIsNotNone(self.cache.get("query3"))
        
        # Add one more (should evict query1 as it's least recently used)
        self.cache.put("query4", self.sample_embedding_4)
        
        # query1 should be evicted, others should remain
        self.assertIsNone(self.cache.get("query1"))
        self.assertIsNotNone(self.cache.get("query2"))
        self.assertIsNotNone(self.cache.get("query3"))
        self.assertIsNotNone(self.cache.get("query4"))
    
    def test_lru_ordering(self):
        """Test that accessing items updates LRU order."""
        # Fill cache
        self.cache.put("query1", self.sample_embedding_1)
        self.cache.put("query2", self.sample_embedding_2)
        self.cache.put("query3", self.sample_embedding_3)
        
        # Access query1 to make it most recent
        self.cache.get("query1")
        
        # Add query4 (should evict query2, not query1)
        self.cache.put("query4", self.sample_embedding_4)
        
        # query1 should still be cached (was accessed recently)
        # query2 should be evicted (least recently used)
        self.assertIsNotNone(self.cache.get("query1"))
        self.assertIsNone(self.cache.get("query2"))
        self.assertIsNotNone(self.cache.get("query3"))
        self.assertIsNotNone(self.cache.get("query4"))
    
    def test_update_existing(self):
        """Test updating existing cache entries."""
        # Add initial entry
        self.cache.put("query1", self.sample_embedding_1)
        self.assertEqual(self.cache.get("query1"), self.sample_embedding_1)
        
        # Update with new embedding
        self.cache.put("query1", self.sample_embedding_2)
        self.assertEqual(self.cache.get("query1"), self.sample_embedding_2)
        
        # Should still be only 1 entry in cache
        stats = self.cache.get_stats()
        self.assertEqual(stats['size'], 1)
    
    def test_delete(self):
        """Test deletion of cache entries."""
        # Add entry
        self.cache.put("query1", self.sample_embedding_1)
        self.assertIsNotNone(self.cache.get("query1"))
        
        # Delete entry
        self.assertTrue(self.cache.delete("query1"))
        self.assertIsNone(self.cache.get("query1"))
        
        # Delete non-existent entry
        self.assertFalse(self.cache.delete("nonexistent"))
    
    def test_clear(self):
        """Test clearing all cache entries."""
        # Add multiple entries
        self.cache.put("query1", self.sample_embedding_1)
        self.cache.put("query2", self.sample_embedding_2)
        
        # Verify they exist
        self.assertIsNotNone(self.cache.get("query1"))
        self.assertIsNotNone(self.cache.get("query2"))
        
        # Clear cache
        self.cache.clear()
        
        # Verify all entries are gone
        self.assertIsNone(self.cache.get("query1"))
        self.assertIsNone(self.cache.get("query2"))
        
        stats = self.cache.get_stats()
        self.assertEqual(stats['size'], 0)
        self.assertEqual(stats['hits'], 0)
        self.assertEqual(stats['misses'], 0)
    
    def test_statistics(self):
        """Test cache statistics calculation."""
        # Test initial stats
        stats = self.cache.get_stats()
        self.assertEqual(stats['capacity'], 3)
        self.assertEqual(stats['size'], 0)
        self.assertEqual(stats['hit_rate'], 0.0)
        
        # Add entries and access them
        self.cache.put("query1", self.sample_embedding_1)
        self.cache.get("query1")  # Hit
        self.cache.get("query2")  # Miss
        
        stats = self.cache.get_stats()
        self.assertEqual(stats['size'], 1)
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['hit_rate'], 0.5)
    
    def test_persistence_save_load(self):
        """Test saving and loading cache from disk."""
        # Add entries to cache
        self.cache.put("query1", self.sample_embedding_1)
        self.cache.put("query2", self.sample_embedding_2)
        
        # Force save to disk
        self.assertTrue(self.cache.force_save())
        self.assertTrue(self.cache_file.exists())
        
        # Create new cache instance from same file
        new_cache = QueryEmbeddingCache(
            capacity=3,
            cache_file=str(self.cache_file),
            ttl_days=1
        )
        
        # Verify data was loaded
        self.assertEqual(new_cache.get("query1"), self.sample_embedding_1)
        self.assertEqual(new_cache.get("query2"), self.sample_embedding_2)
        
        stats = new_cache.get_stats()
        self.assertEqual(stats['size'], 2)
    
    def test_ttl_expiration(self):
        """Test TTL-based expiration of cache entries."""
        # Create cache with very short TTL for testing
        short_ttl_cache = QueryEmbeddingCache(
            capacity=10,
            cache_file=str(self.cache_file.with_suffix('.short_ttl.json')),
            ttl_days=0.0001  # Very short TTL (~8.6 seconds)
        )
        
        # Add entry
        short_ttl_cache.put("query1", self.sample_embedding_1)
        self.assertIsNotNone(short_ttl_cache.get("query1"))
        
        # Wait for expiration
        time.sleep(0.01)  # Wait 10ms
        
        # Entry should be expired now
        self.assertIsNone(short_ttl_cache.get("query1"))
        
        # Clean up
        temp_file = self.cache_file.with_suffix('.short_ttl.json')
        if temp_file.exists():
            temp_file.unlink()
    
    def test_top_queries(self):
        """Test getting top queries by access count."""
        # Add queries with different access patterns
        self.cache.put("popular", self.sample_embedding_1)
        self.cache.put("medium", self.sample_embedding_2)
        self.cache.put("rare", self.sample_embedding_3)
        
        # Access them different numbers of times
        for _ in range(5):
            self.cache.get("popular")
        for _ in range(2):
            self.cache.get("medium")
        self.cache.get("rare")
        
        # Get top queries
        top_queries = self.cache.get_top_queries(3)
        
        # Should be ordered by access count
        self.assertEqual(len(top_queries), 3)
        self.assertEqual(top_queries[0]['query'], 'popular')
        self.assertEqual(top_queries[1]['query'], 'medium') 
        self.assertEqual(top_queries[2]['query'], 'rare')
        
        # Check access counts
        self.assertTrue(top_queries[0]['access_count'] > top_queries[1]['access_count'])
        self.assertTrue(top_queries[1]['access_count'] > top_queries[2]['access_count'])
    
    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        import concurrent.futures
        
        # Function to put and get from different threads
        def cache_operations(thread_id):
            for i in range(10):
                query = f"thread_{thread_id}_query_{i}"
                embedding = [float(thread_id), float(i), 0.0, 0.0]
                self.cache.put(query, embedding)
                result = self.cache.get(query)
                self.assertEqual(result, embedding)
        
        # Run operations from multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(cache_operations, i) for i in range(3)]
            for future in concurrent.futures.as_completed(futures):
                future.result()  # This will raise any exceptions
        
        # Verify cache still works after concurrent access
        stats = self.cache.get_stats()
        self.assertGreater(stats['size'], 0)
    
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs."""
        # Test invalid embeddings
        self.assertFalse(self.cache.put("query1", None))
        self.assertFalse(self.cache.put("query2", []))
        self.assertFalse(self.cache.put("query3", "not a list"))
        
        # Test empty queries
        self.assertTrue(self.cache.put("", self.sample_embedding_1))
        self.assertEqual(self.cache.get(""), self.sample_embedding_1)


if __name__ == '__main__':
    import unittest
    unittest.main()