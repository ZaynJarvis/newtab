"""
Utility functions for ARC cache and eviction policies.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import logging


def calculate_arc_score(visit_count: int, last_visited: Optional[datetime], 
                       first_visited: Optional[datetime]) -> float:
    """
    Calculate ARC score combining frequency and recency.
    
    Args:
        visit_count: Number of times page was visited
        last_visited: When page was last visited
        first_visited: When page was first visited
        
    Returns:
        ARC score between 0.0 and 1.0
    """
    if not last_visited or not first_visited:
        return 0.0
    
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


def time_decay_function(hours_since_access: float) -> float:
    """
    Exponential decay function for recency scoring.
    
    Key points:
    - 1 hour: 97% score retention
    - 6 hours: 79% score retention  
    - 24 hours: 50% score retention
    - 48 hours: 25% score retention
    - 1 week: 0.8% score retention
    
    Args:
        hours_since_access: Hours since last access
        
    Returns:
        Decay factor between 0.01 and 1.0
    """
    return max(0.5 ** (hours_since_access / 24.0), 0.01)


def normalize_scores(scores: List[float]) -> List[float]:
    """
    Normalize a list of scores to 0-1 range.
    
    Args:
        scores: List of raw scores
        
    Returns:
        List of normalized scores
    """
    if not scores:
        return scores
    
    min_score = min(scores)
    max_score = max(scores)
    
    if max_score == min_score:
        return [0.5] * len(scores)  # All scores are equal
    
    range_score = max_score - min_score
    return [(score - min_score) / range_score for score in scores]


def format_cache_stats(stats: Dict[str, Any]) -> str:
    """
    Format cache statistics for human-readable output.
    
    Args:
        stats: Statistics dictionary from ARCCache.get_stats()
        
    Returns:
        Formatted statistics string
    """
    return f"""
ARC Cache Statistics:
━━━━━━━━━━━━━━━━━━━━
Capacity: {stats['capacity']:,}
Current Size: {stats['size']:,} ({stats['size']/stats['capacity']*100:.1f}% full)

Cache Lists:
- T1 (Recent): {stats['T1_size']:,}
- T2 (Frequent): {stats['T2_size']:,} 
- B1 (Ghost Recent): {stats['B1_size']:,}
- B2 (Ghost Frequent): {stats['B2_size']:,}
- Target T1 size (p): {stats['p']}

Performance:
- Hit Rate: {stats['hit_rate']*100:.1f}%
- Total Requests: {stats['total_requests']:,}
- Hits: {stats['hits']:,}
- Misses: {stats['misses']:,}
- Evictions: {stats['evictions']:,}
"""


def estimate_memory_usage(pages: List[Dict]) -> Dict[str, int]:
    """
    Estimate memory usage of cached pages.
    
    Args:
        pages: List of page dictionaries
        
    Returns:
        Dictionary with memory usage estimates in bytes
    """
    total_content = 0
    total_metadata = 0
    vector_data = 0
    
    for page in pages:
        # Content size
        content = page.get('content', '')
        if isinstance(content, str):
            total_content += len(content.encode('utf-8'))
        
        # Metadata size (approximate)
        metadata_fields = ['title', 'description', 'keywords', 'url']
        for field in metadata_fields:
            value = page.get(field, '')
            if isinstance(value, str):
                total_metadata += len(value.encode('utf-8'))
        
        # Vector embedding size
        vector = page.get('vector_embedding')
        if vector and isinstance(vector, list):
            vector_data += len(vector) * 8  # Assume 8 bytes per float
    
    return {
        'total_bytes': total_content + total_metadata + vector_data,
        'content_bytes': total_content,
        'metadata_bytes': total_metadata,
        'vector_bytes': vector_data,
        'total_mb': round((total_content + total_metadata + vector_data) / 1024 / 1024, 2)
    }


def get_eviction_summary(policy_name: str, evicted_pages: List[Dict]) -> str:
    """
    Generate summary of evicted pages.
    
    Args:
        policy_name: Name of eviction policy used
        evicted_pages: List of evicted page dictionaries
        
    Returns:
        Human-readable summary
    """
    if not evicted_pages:
        return f"No pages evicted using {policy_name} policy."
    
    total_visits = sum(p.get('visit_count', 0) for p in evicted_pages)
    avg_visits = total_visits / len(evicted_pages) if evicted_pages else 0
    
    # Get age statistics
    now = datetime.now()
    ages = []
    
    for page in evicted_pages:
        last_visited = page.get('last_visited')
        if isinstance(last_visited, str):
            try:
                last_visited = datetime.fromisoformat(last_visited.replace('Z', '+00:00'))
                ages.append((now - last_visited).days)
            except:
                pass
        elif isinstance(last_visited, datetime):
            ages.append((now - last_visited).days)
    
    avg_age = sum(ages) / len(ages) if ages else 0
    
    return f"""
Eviction Summary ({policy_name}):
━━━━━━━━━━━━━━━━━━━━━━━━━━
Pages Evicted: {len(evicted_pages)}
Total Visits Lost: {total_visits:,}
Average Visits per Page: {avg_visits:.1f}
Average Age: {avg_age:.1f} days
"""


class ARCConfigManager:
    """Configuration manager for ARC cache settings."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        self.default_config = {
            'cache_capacity': 1000,
            'eviction_policy': 'arc',
            'max_age_days': 90,
            'min_visit_threshold': 1,
            'frequency_weight': 0.6,
            'recency_weight': 0.4,
            'auto_eviction_enabled': True,
            'eviction_batch_size': 50,
            'stats_logging_enabled': True
        }
        self.config = self.default_config.copy()
        
        if config_file:
            self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        except (FileNotFoundError, json.JSONDecodeError):
            # Use defaults if file doesn't exist or is invalid
            pass
    
    def save_config(self):
        """Save current configuration to file."""
        if not self.config_file:
            return
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save ARC configuration", extra={
                "config_file": self.config_file,
                "error": str(e),
                "event": "arc_config_save_failed"
            }, exc_info=True)
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value
        if self.config_file:
            self.save_config()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = self.default_config.copy()
        if self.config_file:
            self.save_config()