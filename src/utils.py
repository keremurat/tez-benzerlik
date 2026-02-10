"""
Utility functions for YÖK Tez MCP Server

Includes rate limiting, caching, logging configuration, and helper functions.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Dict
from datetime import datetime, timedelta

# Type variable for generic functions
T = TypeVar('T')

# Configure logging (Vercel-compatible: no file logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Only console logging for Vercel
    ]
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter to prevent overwhelming the YÖK server.
    Enforces a minimum delay between consecutive requests.
    """

    def __init__(self, min_delay: float = 1.5):
        """
        Initialize rate limiter.

        Args:
            min_delay: Minimum delay in seconds between requests (default: 1.5)
        """
        self.min_delay = min_delay
        self.last_request_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        async with self._lock:
            if self.last_request_time is not None:
                elapsed = time.time() - self.last_request_time
                if elapsed < self.min_delay:
                    wait_time = self.min_delay - elapsed
                    logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            self.last_request_time = time.time()


class SimpleCache:
    """
    Simple TTL-based in-memory cache for caching search results.
    In production, consider using Redis or similar.
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    logger.debug(f"Cache hit: {key}")
                    return value
                else:
                    # Remove expired entry
                    del self._cache[key]
                    logger.debug(f"Cache expired: {key}")

            logger.debug(f"Cache miss: {key}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        async with self._lock:
            expiry = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            self._cache[key] = (value, expiry)
            logger.debug(f"Cache set: {key} (TTL: {ttl or self.default_ttl}s)")

    async def clear(self) -> None:
        """Clear all cached items."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    async def cleanup_expired(self) -> None:
        """Remove all expired entries from cache."""
        async with self._lock:
            now = datetime.now()
            expired_keys = [k for k, (_, expiry) in self._cache.items() if now >= expiry]
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


def rate_limited(rate_limiter: RateLimiter) -> Callable:
    """
    Decorator to apply rate limiting to async functions.

    Args:
        rate_limiter: RateLimiter instance to use

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await rate_limiter.wait()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def normalize_turkish_text(text: str) -> str:
    """
    Normalize Turkish text by trimming and handling special characters.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Trim whitespace
    text = text.strip()

    # Replace multiple spaces with single space
    text = ' '.join(text.split())

    return text


def parse_year(year_str: str) -> Optional[int]:
    """
    Parse year from string, handling various formats.

    Args:
        year_str: Year as string

    Returns:
        Year as integer or None if parsing fails
    """
    if not year_str:
        return None

    try:
        # Remove any non-digit characters
        year_digits = ''.join(filter(str.isdigit, year_str))
        if year_digits:
            year = int(year_digits)
            # Sanity check (thesis system started around 1980)
            if 1980 <= year <= 2030:
                return year
    except (ValueError, TypeError):
        pass

    return None


def build_cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Build a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Create a string representation of all arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
    return ":".join(key_parts)


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base


async def retry_async(
    func: Callable,
    config: RetryConfig = RetryConfig(),
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        config: Retry configuration
        *args: Function positional arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if attempt < config.max_attempts - 1:
                # Calculate delay with exponential backoff
                delay = min(
                    config.initial_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )

                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"All {config.max_attempts} attempts failed. Last error: {str(e)}"
                )

    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    else:
        raise RuntimeError("Retry failed with no exception (should not happen)")
