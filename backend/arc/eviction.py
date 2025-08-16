"""
Eviction policies for the New Tab system.

This module provides different eviction strategies that can work
with the ARC cache or standalone.
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import math


class EvictionPolicy(ABC):
    """Base class for eviction policies."""
    
    @abstractmethod
    def get_eviction_candidates(self, pages: List[Dict], count: int) -> List[int]:
        """Get page IDs that should be evicted."""
        pass


class ARCEvictionPolicy(EvictionPolicy):
    """ARC-based eviction policy using frequency and recency."""
    
    def __init__(self, max_age_days: int = 90, min_visit_threshold: int = 1):
        """
        Initialize ARC eviction policy.
        
        Args:
            max_age_days: Maximum age in days before considering eviction
            min_visit_threshold: Minimum visits required to avoid eviction
        """
        self.max_age_days = max_age_days
        self.min_visit_threshold = min_visit_threshold
    
    def get_eviction_candidates(self, pages: List[Dict], count: int) -> List[int]:
        """
        Get eviction candidates using ARC scoring.
        
        Prioritizes eviction of pages with:
        - Low visit counts
        - Old last visit dates
        - Low ARC scores
        
        Args:
            pages: List of page dictionaries with metadata
            count: Number of candidates to return
            
        Returns:
            List of page IDs sorted by eviction priority (highest first)
        """
        if not pages:
            return []
        
        candidates = []
        now = datetime.now()
        cutoff_date = now - timedelta(days=self.max_age_days)
        
        for page in pages:
            page_id = page.get('id')
            if not page_id:
                continue
            
            # Get page metrics
            visit_count = page.get('visit_count', 0)
            last_visited = page.get('last_visited')
            arc_score = page.get('arc_score', 0.0)
            
            # Parse last visited date
            if isinstance(last_visited, str):
                try:
                    last_visited = datetime.fromisoformat(last_visited.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    last_visited = now  # Default to now if parsing fails
            elif not isinstance(last_visited, datetime):
                last_visited = now
            
            # Calculate eviction score (higher = more likely to be evicted)
            eviction_score = self._calculate_eviction_score(
                visit_count, last_visited, arc_score, now, cutoff_date
            )
            
            candidates.append((page_id, eviction_score, {
                'visit_count': visit_count,
                'last_visited': last_visited,
                'arc_score': arc_score,
                'url': page.get('url', ''),
                'title': page.get('title', '')
            }))
        
        # Sort by eviction score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return only page IDs
        return [candidate[0] for candidate in candidates[:count]]
    
    def _calculate_eviction_score(self, visit_count: int, last_visited: datetime, 
                                arc_score: float, now: datetime, cutoff_date: datetime) -> float:
        """Calculate eviction score for a page."""
        
        # Base score starts at 1.0
        score = 1.0
        
        # Age factor (older pages get higher eviction scores)
        days_since_visit = (now - last_visited).days
        if days_since_visit > self.max_age_days:
            # Very old pages get high eviction scores
            age_multiplier = 2.0 + (days_since_visit - self.max_age_days) / 30.0
            score *= age_multiplier
        elif days_since_visit > 30:
            # Moderately old pages get medium eviction scores
            score *= 1.0 + (days_since_visit - 30) / 60.0
        else:
            # Recent pages get lower eviction scores
            score *= 0.5
        
        # Visit count factor (fewer visits = higher eviction score)
        if visit_count == 0:
            score *= 3.0  # Never visited pages are prime eviction candidates
        elif visit_count < self.min_visit_threshold:
            score *= 2.0  # Low visit pages
        elif visit_count < 5:
            score *= 1.2  # Moderate visit pages
        else:
            # Frequently visited pages get lower eviction scores
            score *= max(0.1, 1.0 / math.log10(visit_count + 1))
        
        # ARC score factor (lower ARC scores = higher eviction scores)
        if arc_score == 0.0:
            score *= 1.5  # No ARC score available
        else:
            # Invert ARC score for eviction (lower ARC = higher eviction priority)
            score *= (2.0 - arc_score)  # ARC score is 0-1, so this gives 2.0-1.0 range
        
        return round(score, 4)
    
    def get_eviction_explanation(self, pages: List[Dict], page_id: int) -> str:
        """Get human-readable explanation for why a page would be evicted."""
        page = next((p for p in pages if p.get('id') == page_id), None)
        if not page:
            return "Page not found"
        
        visit_count = page.get('visit_count', 0)
        last_visited = page.get('last_visited')
        arc_score = page.get('arc_score', 0.0)
        
        reasons = []
        
        if visit_count == 0:
            reasons.append("never visited")
        elif visit_count < self.min_visit_threshold:
            reasons.append(f"low visit count ({visit_count})")
        
        if isinstance(last_visited, (str, datetime)):
            if isinstance(last_visited, str):
                try:
                    last_visited = datetime.fromisoformat(last_visited.replace('Z', '+00:00'))
                except:
                    last_visited = None
            
            if last_visited:
                days_old = (datetime.now() - last_visited).days
                if days_old > self.max_age_days:
                    reasons.append(f"very old ({days_old} days since last visit)")
                elif days_old > 30:
                    reasons.append(f"moderately old ({days_old} days since last visit)")
        
        if arc_score < 0.2:
            reasons.append(f"low relevance score ({arc_score:.2f})")
        
        if not reasons:
            reasons.append("lowest priority among candidates")
        
        return f"Eviction candidate: {', '.join(reasons)}"


class LRUEvictionPolicy(EvictionPolicy):
    """Simple LRU eviction policy."""
    
    def get_eviction_candidates(self, pages: List[Dict], count: int) -> List[int]:
        """Get LRU eviction candidates."""
        if not pages:
            return []
        
        # Sort by last_visited (oldest first)
        sorted_pages = sorted(pages, key=lambda p: p.get('last_visited', ''), reverse=False)
        
        return [page['id'] for page in sorted_pages[:count] if 'id' in page]


class LFUEvictionPolicy(EvictionPolicy):
    """Simple LFU eviction policy."""
    
    def get_eviction_candidates(self, pages: List[Dict], count: int) -> List[int]:
        """Get LFU eviction candidates."""
        if not pages:
            return []
        
        # Sort by visit_count (lowest first)
        sorted_pages = sorted(pages, key=lambda p: p.get('visit_count', 0))
        
        return [page['id'] for page in sorted_pages[:count] if 'id' in page]


class HybridEvictionPolicy(EvictionPolicy):
    """Hybrid eviction policy combining multiple factors."""
    
    def __init__(self, recency_weight: float = 0.4, frequency_weight: float = 0.3, 
                 size_weight: float = 0.2, relevance_weight: float = 0.1):
        """Initialize hybrid eviction policy with configurable weights."""
        total = recency_weight + frequency_weight + size_weight + relevance_weight
        self.recency_weight = recency_weight / total
        self.frequency_weight = frequency_weight / total
        self.size_weight = size_weight / total
        self.relevance_weight = relevance_weight / total
    
    def get_eviction_candidates(self, pages: List[Dict], count: int) -> List[int]:
        """Get eviction candidates using hybrid scoring."""
        if not pages:
            return []
        
        candidates = []
        now = datetime.now()
        
        # Get normalization values
        max_visits = max((p.get('visit_count', 0) for p in pages), default=1)
        max_size = max((len(p.get('content', '')) for p in pages), default=1)
        
        for page in pages:
            page_id = page.get('id')
            if not page_id:
                continue
            
            # Calculate component scores (higher = more likely to evict)
            recency_score = self._calculate_recency_score(page.get('last_visited'), now)
            frequency_score = self._calculate_frequency_score(page.get('visit_count', 0), max_visits)
            size_score = self._calculate_size_score(len(page.get('content', '')), max_size)
            relevance_score = self._calculate_relevance_score(page.get('arc_score', 0.0))
            
            # Combine scores
            combined_score = (
                recency_score * self.recency_weight +
                frequency_score * self.frequency_weight +
                size_score * self.size_weight +
                relevance_score * self.relevance_weight
            )
            
            candidates.append((page_id, combined_score))
        
        # Sort by combined score (highest first = most likely to evict)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [candidate[0] for candidate in candidates[:count]]
    
    def _calculate_recency_score(self, last_visited, now: datetime) -> float:
        """Calculate recency score (higher = older = more evictable)."""
        if not last_visited:
            return 1.0  # No visit data = high eviction score
        
        if isinstance(last_visited, str):
            try:
                last_visited = datetime.fromisoformat(last_visited.replace('Z', '+00:00'))
            except:
                return 1.0
        
        days_old = (now - last_visited).days
        # Normalize to 0-1 scale, with 30+ days = 1.0
        return min(days_old / 30.0, 1.0)
    
    def _calculate_frequency_score(self, visit_count: int, max_visits: int) -> float:
        """Calculate frequency score (higher = less frequent = more evictable)."""
        if max_visits == 0:
            return 1.0
        # Invert frequency (less frequent = higher eviction score)
        return 1.0 - (visit_count / max_visits)
    
    def _calculate_size_score(self, content_size: int, max_size: int) -> float:
        """Calculate size score (higher = larger = more evictable)."""
        if max_size == 0:
            return 0.0
        # Larger content gets higher eviction score
        return content_size / max_size
    
    def _calculate_relevance_score(self, arc_score: float) -> float:
        """Calculate relevance score (higher = less relevant = more evictable)."""
        # Invert ARC score (lower relevance = higher eviction score)
        return 1.0 - arc_score