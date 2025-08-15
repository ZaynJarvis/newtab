"""
Adaptive Replacement Cache (ARC) implementation.

ARC dynamically balances between recency (LRU) and frequency (LFU) 
by maintaining separate lists and adapting their sizes based on workload.
"""

from typing import Dict, Optional, Any, Tuple, List
from collections import OrderedDict
from datetime import datetime
import time


class ARCCache:
    """
    Adaptive Replacement Cache implementation.
    
    ARC maintains four lists:
    - T1: Recent cache misses (recency list)
    - T2: Recent cache hits (frequency list) 
    - B1: Ghost entries evicted from T1
    - B2: Ghost entries evicted from T2
    
    The cache adapts the sizes of T1 and T2 based on the workload pattern.
    """
    
    def __init__(self, capacity: int = 1000):
        """Initialize ARC cache with given capacity."""
        self.capacity = max(1, capacity)
        self.p = 0  # Target size for T1 (adaptive parameter)
        
        # The four lists
        self.T1 = OrderedDict()  # Recent cache misses
        self.T2 = OrderedDict()  # Recent cache hits (frequent)
        self.B1 = OrderedDict()  # Ghost entries from T1
        self.B2 = OrderedDict()  # Ghost entries from T2
        
        # Metadata for pages
        self.metadata = {}
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _hit_in_T1(self, key: Any, value: Any) -> Any:
        """Handle cache hit in T1."""
        self.T1.pop(key)
        self.T2[key] = value
        return value
    
    def _hit_in_T2(self, key: Any, value: Any) -> Any:
        """Handle cache hit in T2."""
        self.T2.move_to_end(key)
        return value
    
    def _hit_in_B1(self, key: Any, value: Any):
        """Handle hit in B1 ghost list."""
        # Increase p (favor recency)
        delta1 = 1 if len(self.B1) >= len(self.B2) else len(self.B2) // len(self.B1)
        self.p = min(self.capacity, self.p + delta1)
        
        # Replace in cache
        self._replace(key, in_B2=False)
        
        # Remove from B1 and add to T2
        self.B1.pop(key)
        self.T2[key] = value
    
    def _hit_in_B2(self, key: Any, value: Any):
        """Handle hit in B2 ghost list."""
        # Decrease p (favor frequency)
        delta2 = 1 if len(self.B2) >= len(self.B1) else len(self.B1) // len(self.B2)
        self.p = max(0, self.p - delta2)
        
        # Replace in cache
        self._replace(key, in_B2=True)
        
        # Remove from B2 and add to T2
        self.B2.pop(key)
        self.T2[key] = value
    
    def _miss(self, key: Any, value: Any):
        """Handle cache miss."""
        L1_size = len(self.T1) + len(self.B1)
        L2_size = len(self.T2) + len(self.B2)
        
        if L1_size == self.capacity:
            # Case A: L1 is full
            if len(self.T1) < self.capacity:
                # Delete LRU page in B1
                self.B1.popitem(last=False)
                self._replace(key, in_B2=False)
            else:
                # Delete LRU page in T1
                evicted_key, evicted_value = self.T1.popitem(last=False)
                self.evictions += 1
        elif L1_size < self.capacity and (L1_size + L2_size) >= self.capacity:
            # Case B: L1 is not full but L1 + L2 >= capacity
            if (L1_size + L2_size) == 2 * self.capacity:
                # Delete LRU page in B2
                self.B2.popitem(last=False)
            self._replace(key, in_B2=False)
        
        # Add new page to T1
        self.T1[key] = value
    
    def _replace(self, key: Any, in_B2: bool):
        """Replace pages according to ARC policy."""
        if len(self.T1) >= 1 and ((key in self.B2 and len(self.T1) == self.p) or len(self.T1) > self.p):
            # Move LRU page from T1 to B1
            evicted_key, evicted_value = self.T1.popitem(last=False)
            self.B1[evicted_key] = None  # Ghost entry
            self.evictions += 1
        else:
            # Move LRU page from T2 to B2
            if self.T2:
                evicted_key, evicted_value = self.T2.popitem(last=False)
                self.B2[evicted_key] = None  # Ghost entry
                self.evictions += 1
    
    def get(self, key: Any) -> Optional[Any]:
        """Get value from cache."""
        # Check T1 and T2 (actual cache)
        if key in self.T1:
            self.hits += 1
            return self._hit_in_T1(key, self.T1[key])
        
        if key in self.T2:
            self.hits += 1
            return self._hit_in_T2(key, self.T2[key])
        
        # Cache miss
        self.misses += 1
        return None
    
    def put(self, key: Any, value: Any):
        """Put key-value pair in cache."""
        # Update metadata
        self.metadata[key] = {
            'access_time': datetime.now(),
            'access_count': self.metadata.get(key, {}).get('access_count', 0) + 1
        }
        
        # Check if it's in ghost lists
        if key in self.B1:
            self._hit_in_B1(key, value)
            return
        
        if key in self.B2:
            self._hit_in_B2(key, value)
            return
        
        # Check if already in cache
        if key in self.T1:
            self.T1[key] = value
            self._hit_in_T1(key, value)
            return
        
        if key in self.T2:
            self.T2[key] = value
            self._hit_in_T2(key, value)
            return
        
        # Cache miss - add new entry
        self._miss(key, value)
    
    def delete(self, key: Any) -> bool:
        """Delete key from cache."""
        if key in self.T1:
            del self.T1[key]
            self.metadata.pop(key, None)
            return True
        
        if key in self.T2:
            del self.T2[key]
            self.metadata.pop(key, None)
            return True
        
        if key in self.B1:
            del self.B1[key]
            self.metadata.pop(key, None)
            return True
        
        if key in self.B2:
            del self.B2[key]
            self.metadata.pop(key, None)
            return True
        
        return False
    
    def get_eviction_candidates(self, count: int = 10) -> List[Tuple[Any, float]]:
        """Get candidates for eviction based on ARC algorithm."""
        candidates = []
        
        # Get LRU items from T1 (lowest priority)
        t1_items = list(self.T1.items())
        for i, (key, value) in enumerate(t1_items):
            if i >= count:
                break
            # Lower score = higher eviction priority
            score = 0.1 - (i * 0.01)  # T1 items have very low scores
            candidates.append((key, score))
        
        # Get LRU items from T2 if we need more candidates
        if len(candidates) < count and self.T2:
            t2_items = list(self.T2.items())
            remaining = count - len(candidates)
            
            for i, (key, value) in enumerate(t2_items):
                if i >= remaining:
                    break
                # T2 items have higher scores than T1 but still evictable
                score = 0.3 - (i * 0.01)
                candidates.append((key, score))
        
        # Sort by eviction priority (lowest score first)
        candidates.sort(key=lambda x: x[1])
        
        return candidates[:count]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            'capacity': self.capacity,
            'size': len(self.T1) + len(self.T2),
            'T1_size': len(self.T1),
            'T2_size': len(self.T2),
            'B1_size': len(self.B1),
            'B2_size': len(self.B2),
            'p': self.p,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': round(hit_rate, 3),
            'total_requests': total_requests
        }
    
    def clear(self):
        """Clear all cache data."""
        self.T1.clear()
        self.T2.clear()
        self.B1.clear()
        self.B2.clear()
        self.metadata.clear()
        self.p = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0