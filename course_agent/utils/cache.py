"""
Simple caching layer for search results to improve performance.
"""
import hashlib
import time
from typing import Any, Optional, Dict
from functools import wraps
from ..utils.logger import logger


class SearchCache:
    """Simple in-memory cache for search results with TTL."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache with time-to-live.

        Args:
            ttl_seconds: Time-to-live for cached entries (default 5 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def _make_key(self, *args, **kwargs) -> str:
        """Create a cache key from function arguments."""
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if it exists and is not expired."""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() - entry["timestamp"] > self._ttl:
            # Entry expired, remove it
            del self._cache[key]
            return None

        logger.debug(f"Cache hit for key: {key[:8]}...")
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Set a cached value with current timestamp."""
        self._cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
        logger.debug(f"Cache set for key: {key[:8]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove all expired entries and return count removed."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry["timestamp"] > self._ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


# Global cache instance (5 minute TTL)
_search_cache = SearchCache(ttl_seconds=300)


def cached_search(func):
    """
    Decorator for caching async search functions.

    Usage:
        @cached_search
        async def search(self, query: SearchQuery):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Create cache key from arguments
        cache_key = _search_cache._make_key(func.__name__, *args[1:], **kwargs)

        # Try to get from cache
        cached_result = _search_cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Using cached results for {func.__name__}")
            return cached_result

        # Execute function
        result = await func(*args, **kwargs)

        # Cache the result
        _search_cache.set(cache_key, result)

        return result

    return wrapper


def get_cache() -> SearchCache:
    """Get the global cache instance."""
    return _search_cache
