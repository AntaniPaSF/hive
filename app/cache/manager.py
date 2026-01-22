"""
Response Caching Manager

Implements caching for expensive operations:
- RAG query responses
- Search results
- LRU eviction policy
- TTL (time-to-live) support
- Cache invalidation strategies
"""

import time
import hashlib
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    def touch(self):
        """Update last accessed time and increment counter."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CacheManager:
    """
    LRU cache with TTL support for caching expensive operations.
    
    Features:
    - Least Recently Used (LRU) eviction
    - Time-to-live (TTL) expiration
    - Automatic cleanup of expired entries
    - Cache statistics and monitoring
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            max_size: Maximum number of entries in cache
            default_ttl: Default TTL in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0
        
        logger.info(f"Cache initialized (max_size={max_size}, default_ttl={default_ttl}s)")
    
    def _make_key(self, *args, **kwargs) -> str:
        """
        Generate cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Hexadecimal hash string as cache key
        """
        # Create deterministic representation
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        
        # Hash it
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check expiration
        if entry.is_expired():
            self._remove(key, expired=True)
            self.misses += 1
            return None
        
        # Update access info
        entry.touch()
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        
        self.hits += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None uses default)
        """
        # Use default TTL if not specified
        if ttl is None:
            ttl = self.default_ttl
        
        # Check if we need to evict
        if key not in self.cache and len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=0,
            ttl_seconds=ttl
        )
        
        # Add to cache
        self.cache[key] = entry
        self.cache.move_to_end(key)
        
        logger.debug(f"Cached entry {key[:8]}... (ttl={ttl}s)")
    
    def _remove(self, key: str, expired: bool = False):
        """Remove entry from cache."""
        if key in self.cache:
            del self.cache[key]
            if expired:
                self.expirations += 1
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        # Remove first item (least recently used)
        key, entry = self.cache.popitem(last=False)
        self.evictions += 1
        logger.debug(f"Evicted LRU entry {key[:8]}...")
    
    def invalidate(self, key: str):
        """
        Manually invalidate a cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        self._remove(key)
        logger.debug(f"Invalidated entry {key[:8]}...")
    
    def clear(self):
        """Clear entire cache."""
        size = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared cache ({size} entries)")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self._remove(key, expired=True)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "usage_percent": len(self.cache) / self.max_size * 100,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "total_requests": total_requests,
        }
    
    def print_stats(self):
        """Print formatted cache statistics."""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("CACHE STATISTICS")
        print("="*60)
        print(f"Size: {stats['size']} / {stats['max_size']} ({stats['usage_percent']:.1f}%)")
        print(f"\nHits: {stats['hits']}")
        print(f"Misses: {stats['misses']}")
        print(f"Hit Rate: {stats['hit_rate']:.1%}")
        print(f"\nEvictions: {stats['evictions']}")
        print(f"Expirations: {stats['expirations']}")
        print("="*60)


class QueryCache(CacheManager):
    """
    Specialized cache for RAG query responses.
    
    Automatically generates keys from queries and caches responses.
    """
    
    def cache_query(
        self,
        question: str,
        provider: str,
        model: str,
        top_k: int,
        response: Any,
        ttl: Optional[int] = None
    ):
        """
        Cache a query response.
        
        Args:
            question: Question text
            provider: LLM provider
            model: Model name
            top_k: Number of sources
            response: RAGResponse object
            ttl: Time-to-live in seconds
        """
        key = self._make_key(question, provider, model, top_k)
        self.set(key, response, ttl=ttl)
    
    def get_query(
        self,
        question: str,
        provider: str,
        model: str,
        top_k: int
    ) -> Optional[Any]:
        """
        Get cached query response.
        
        Args:
            question: Question text
            provider: LLM provider
            model: Model name
            top_k: Number of sources
        
        Returns:
            Cached RAGResponse or None
        """
        key = self._make_key(question, provider, model, top_k)
        return self.get(key)
    
    def invalidate_provider(self, provider: str):
        """
        Invalidate all entries for a specific provider.
        
        Args:
            provider: Provider name to invalidate
        """
        # Note: This is a simple implementation
        # For production, consider storing provider metadata with entries
        self.clear()
        logger.info(f"Invalidated cache for provider: {provider}")


class SearchCache(CacheManager):
    """
    Specialized cache for search results.
    """
    
    def cache_search(
        self,
        query: str,
        top_k: int,
        metadata_filter: Optional[Dict] = None,
        results: Any = None,
        ttl: Optional[int] = None
    ):
        """
        Cache search results.
        
        Args:
            query: Search query
            top_k: Number of results
            metadata_filter: Optional metadata filter
            results: Search results
            ttl: Time-to-live in seconds
        """
        key = self._make_key(query, top_k, metadata_filter)
        self.set(key, results, ttl=ttl)
    
    def get_search(
        self,
        query: str,
        top_k: int,
        metadata_filter: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        Get cached search results.
        
        Args:
            query: Search query
            top_k: Number of results
            metadata_filter: Optional metadata filter
        
        Returns:
            Cached results or None
        """
        key = self._make_key(query, top_k, metadata_filter)
        return self.get(key)
    
    def invalidate_document(self, document_name: str):
        """
        Invalidate cache entries related to a document.
        
        Args:
            document_name: Name of document to invalidate
        """
        # For full implementation, would need to track document associations
        self.clear()
        logger.info(f"Invalidated cache for document: {document_name}")


# Global cache instances (can be initialized in app startup)
query_cache: Optional[QueryCache] = None
search_cache: Optional[SearchCache] = None


def init_caches(
    query_cache_size: int = 100,
    query_cache_ttl: int = 3600,
    search_cache_size: int = 200,
    search_cache_ttl: int = 1800
):
    """
    Initialize global cache instances.
    
    Args:
        query_cache_size: Max size for query cache
        query_cache_ttl: Default TTL for query cache
        search_cache_size: Max size for search cache
        search_cache_ttl: Default TTL for search cache
    """
    global query_cache, search_cache
    
    query_cache = QueryCache(max_size=query_cache_size, default_ttl=query_cache_ttl)
    search_cache = SearchCache(max_size=search_cache_size, default_ttl=search_cache_ttl)
    
    logger.info("Caches initialized")


def get_query_cache() -> QueryCache:
    """Get global query cache instance."""
    global query_cache
    if query_cache is None:
        query_cache = QueryCache()
    return query_cache


def get_search_cache() -> SearchCache:
    """Get global search cache instance."""
    global search_cache
    if search_cache is None:
        search_cache = SearchCache()
    return search_cache


# Decorator for caching function results
def cached(ttl: Optional[int] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
    
    Usage:
        @cached(ttl=3600)
        def expensive_function(arg1, arg2):
            # function code
    """
    def decorator(func):
        cache = CacheManager(max_size=100, default_ttl=ttl or 3600)
        
        def wrapper(*args, **kwargs):
            key = cache._make_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Execute function
            logger.debug(f"Cache miss for {func.__name__}, executing...")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(key, result, ttl=ttl)
            
            return result
        
        # Attach cache for inspection
        wrapper.cache = cache
        
        return wrapper
    
    return decorator


if __name__ == "__main__":
    # Example usage
    print("Testing CacheManager...")
    
    cache = CacheManager(max_size=3, default_ttl=5)
    
    # Set some values
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    # Get values
    print(f"key1: {cache.get('key1')}")
    print(f"key2: {cache.get('key2')}")
    
    # This should evict key3 (least recently used)
    cache.set("key4", "value4")
    
    print(f"key3 (should be None): {cache.get('key3')}")
    print(f"key4: {cache.get('key4')}")
    
    cache.print_stats()
    
    # Test TTL
    print("\nTesting TTL...")
    cache_ttl = CacheManager(max_size=10, default_ttl=2)
    cache_ttl.set("temp", "temporary value", ttl=2)
    print(f"Before expiration: {cache_ttl.get('temp')}")
    
    time.sleep(3)
    print(f"After expiration: {cache_ttl.get('temp')}")
    
    cache_ttl.print_stats()
