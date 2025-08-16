"""ARC (Adaptive Replacement Cache) algorithm implementation for New Tab."""

from .arc_cache import ARCCache
from .eviction import EvictionPolicy

__all__ = ['ARCCache', 'EvictionPolicy']