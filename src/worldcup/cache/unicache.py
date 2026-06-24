"""UniCache - Abstract base class for three-tier caching.

Provides unified interface for L1 (Memory) → L2 (Redis) → L3 (SQLite) caching.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Wrapper for cached values with metadata."""

    key: str
    value: T
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 0
    source: str = "unknown"  # 'l1', 'l2', 'l3', 'api'

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry has expired based on given TTL."""
        if ttl_seconds <= 0:
            return False
        elapsed = (datetime.now() - self.updated_at).total_seconds()
        return elapsed > ttl_seconds


@dataclass
class L1Entry(Generic[T]):
    """L1 memory cache entry with timestamp."""

    value: T
    timestamp: datetime = field(default_factory=datetime.now)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if L1 entry has expired."""
        if ttl_seconds <= 0:
            return False
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed > ttl_seconds


class UniCache(ABC, Generic[T]):
    """Abstract base class for three-tier caching.

    Subclasses must implement:
    - _l3_get: Load from database
    - _l3_set: Save to database
    - _fetch_from_api: Fetch fresh data from external API
    - _serialize / _deserialize: Convert between T and Redis-compatible format

    The base class provides:
    - L1 in-memory caching with TTL
    - L2 Redis caching with TTL
    - Unified get/set/refresh interface
    - Trading-time aware behavior
    """

    # Default TTLs (can be overridden by subclasses)
    L1_TTL_SECONDS: int = 600  # 10 minutes
    L1_TTL_TRADING: int = 30  # 30 seconds during trading
    L2_TTL_SECONDS: int = 3600  # 1 hour
    REDIS_KEY_PREFIX: str = "worldcup:cache"

    def __init__(
        self,
        redis_client=None,
        db_session_factory=None,
        trading_checker=None,
    ):
        """Initialize UniCache.

        Args:
            redis_client: Redis async client (optional, L2 disabled if None)
            db_session_factory: SQLAlchemy async session factory for L3
            trading_checker: ATradingTimeChecker instance
        """
        self._redis = redis_client
        self._db_session_factory = db_session_factory
        self._trading_checker = trading_checker

        # L1 in-memory cache (class-level for sharing across instances)
        self._l1_cache: dict[str, L1Entry[T]] = {}

    def _get_l1_ttl(self) -> int:
        """Get L1 TTL based on trading time."""
        if self._trading_checker and self._trading_checker.is_trading_time():
            return self.L1_TTL_TRADING
        return self.L1_TTL_SECONDS

    def _redis_key(self, key: str) -> str:
        """Generate Redis key with prefix."""
        return f"{self.REDIS_KEY_PREFIX}:{key}"

    # ==================== L1 Operations ====================

    def _l1_get(self, key: str) -> Optional[T]:
        """Get value from L1 memory cache."""
        entry = self._l1_cache.get(key)
        if entry is None:
            return None

        ttl = self._get_l1_ttl()
        if entry.is_expired(ttl):
            del self._l1_cache[key]
            return None

        return entry.value

    def _l1_set(self, key: str, value: T) -> None:
        """Set value in L1 memory cache."""
        self._l1_cache[key] = L1Entry(value=value, timestamp=datetime.now())

    def _l1_delete(self, key: str) -> None:
        """Delete value from L1 cache."""
        self._l1_cache.pop(key, None)

    # ==================== L2 Operations ====================

    async def _l2_get(self, key: str) -> Optional[T]:
        """Get value from L2 Redis cache."""
        if self._redis is None:
            return None

        try:
            data = await self._redis.get(self._redis_key(key))
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            print(f"L2 get error for {key}: {e}")
            return None

    async def _l2_set(self, key: str, value: T) -> None:
        """Set value in L2 Redis cache with TTL."""
        if self._redis is None:
            return

        try:
            data = self._serialize(value)
            await self._redis.setex(
                self._redis_key(key),
                self.L2_TTL_SECONDS,
                data,
            )
        except Exception as e:
            print(f"L2 set error for {key}: {e}")

    async def _l2_delete(self, key: str) -> None:
        """Delete value from L2 cache."""
        if self._redis is None:
            return

        try:
            await self._redis.delete(self._redis_key(key))
        except Exception as e:
            print(f"L2 delete error for {key}: {e}")

    # ==================== Abstract Methods ====================

    @abstractmethod
    async def _l3_get(self, key: str) -> Optional[T]:
        """Load value from L3 database.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def _l3_set(self, key: str, value: T) -> None:
        """Save value to L3 database.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def _fetch_from_api(self, key: str) -> Optional[T]:
        """Fetch fresh value from external API.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def _serialize(self, value: T) -> str:
        """Serialize value for Redis storage.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def _deserialize(self, data: str) -> T:
        """Deserialize value from Redis storage.

        Must be implemented by subclasses.
        """
        pass

    # ==================== Public Interface ====================

    async def get(self, key: str) -> Optional[CacheEntry[T]]:
        """Get value with three-tier cache lookup.

        Lookup order depends on trading time:
        - Trading hours: L1 → L2 → API → L3 (fallback)
        - Non-trading hours: L1 → L2 → L3 → API

        Args:
            key: Cache key (typically ticker symbol)

        Returns:
            CacheEntry with value and metadata, or None if not found
        """
        is_trading = (
            self._trading_checker.is_trading_time()
            if self._trading_checker
            else False
        )

        # L1 check
        value = self._l1_get(key)
        if value is not None:
            return CacheEntry(key=key, value=value, source="l1")

        # L2 check
        value = await self._l2_get(key)
        if value is not None:
            self._l1_set(key, value)
            return CacheEntry(key=key, value=value, source="l2")

        if is_trading:
            # Trading hours: API first, L3 as fallback
            value = await self._fetch_from_api(key)
            if value is not None:
                await self._write_through(key, value)
                return CacheEntry(key=key, value=value, source="api")

            # API failed, try L3 as fallback
            value = await self._l3_get(key)
            if value is not None:
                self._l1_set(key, value)
                await self._l2_set(key, value)
                return CacheEntry(key=key, value=value, source="l3")
        else:
            # Non-trading hours: L3 first, then API
            value = await self._l3_get(key)
            if value is not None:
                self._l1_set(key, value)
                await self._l2_set(key, value)
                return CacheEntry(key=key, value=value, source="l3")

            # L3 miss, try API
            value = await self._fetch_from_api(key)
            if value is not None:
                await self._write_through(key, value)
                return CacheEntry(key=key, value=value, source="api")

        return None

    async def get_batch(self, keys: list[str]) -> dict[str, Optional[CacheEntry[T]]]:
        """Batch get multiple keys.

        Args:
            keys: List of cache keys

        Returns:
            Dict mapping keys to CacheEntry or None
        """
        results = {}
        for key in keys:
            results[key] = await self.get(key)
        return results

    async def set(self, key: str, value: T, write_through: bool = True) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            write_through: If True, write to all tiers; if False, only L1/L2
        """
        self._l1_set(key, value)
        await self._l2_set(key, value)

        if write_through:
            await self._l3_set(key, value)

    async def refresh(self, key: str) -> Optional[CacheEntry[T]]:
        """Force refresh from API, bypassing cache.

        Args:
            key: Cache key

        Returns:
            Fresh CacheEntry from API, or None if fetch failed
        """
        value = await self._fetch_from_api(key)
        if value is not None:
            await self._write_through(key, value)
            return CacheEntry(key=key, value=value, source="api")

        return None

    async def invalidate(self, key: str) -> None:
        """Invalidate cache entry from all tiers.

        Args:
            key: Cache key to invalidate
        """
        self._l1_delete(key)
        await self._l2_delete(key)
        # Note: L3 is not deleted (permanent storage)

    async def _write_through(self, key: str, value: T) -> None:
        """Write value to all cache tiers."""
        self._l1_set(key, value)
        await self._l2_set(key, value)
        await self._l3_set(key, value)
