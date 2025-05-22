from functools import wraps
from typing import Callable, Dict, Optional
import os
from fastapi import HTTPException, Request
from limits.aio.storage import RedisStorage, MemoryStorage
from limits.aio.strategies import (
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)
from limits import parse

# API Keys (temporary storage, will be moved to Redis later)
API_KEYS: Dict[str, Dict] = {
    "test_key_1": {"name": "Test Client 1", "rate_limit": "5/minute"},
    "test_key_2": {"name": "Test Client 2", "rate_limit": "10/minute"},
}

# Rate limit strategies mapping
RATE_LIMIT_STRATEGIES = {
    "fixed": FixedWindowRateLimiter,
    "moving": MovingWindowRateLimiter,
    "sliding": SlidingWindowCounterRateLimiter,
}


def get_redis_storage():
    """Create and return a Redis storage instance using a URI.

    The function prioritizes explicit configuration via environment variables:
    - REDIS_URI: Direct Redis URI (redis://host:port/db)
    - REDIS_HOST, REDIS_PORT, REDIS_DB: Individual components

    If running in Docker (detected via /proc/self/cgroup), it defaults to the service name "redis".
    If running locally, it tries to connect to "localhost" by default.
    Uses the standard redis client for better Docker compatibility.
    """
    # Check for direct URI configuration
    redis_uri = os.environ.get("REDIS_URI")
    if redis_uri:
        return RedisStorage(redis_uri)

    # Check if we're running in Docker
    in_docker = False
    try:
        with open("/proc/self/cgroup", "r") as f:
            in_docker = any("docker" in line for line in f)
    except:
        pass

    # Get individual components with sensible defaults based on environment
    default_host = "redis" if in_docker else "localhost"
    host = os.environ.get("REDIS_HOST", default_host)
    port = os.environ.get("REDIS_PORT", "6379")
    db = os.environ.get("REDIS_DB", "0")

    # Build and return standard Redis URI
    redis_uri = f"redis://{host}:{port}/{db}"
    return RedisStorage(redis_uri)


def validate_api_key(api_key: str) -> Dict:
    """Validate the API key and return its configuration."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required. Please provide it in the X-API-Key header.",
        )

    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Please check your credentials.",
        )

    return API_KEYS[api_key]


def rate_limit(
    strategy: str = "sliding", rate: Optional[str] = None, storage_backend=None
):
    """
    Rate limiter decorator that checks API key validity and enforces rate limits.

    Args:
        strategy (str): Rate limiting strategy to use ('fixed', 'moving', or 'sliding')
        rate (str, optional): Rate limit string (e.g., "5/minute"). If not provided,
                            will use the rate limit from the API key configuration.
        storage_backend: Optional storage backend instance (for testing)
    """
    if strategy not in RATE_LIMIT_STRATEGIES:
        raise ValueError(
            f"Invalid strategy. Must be one of: {list(RATE_LIMIT_STRATEGIES.keys())}"
        )

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Look for Request in args or kwargs
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if not request:
                request = next(
                    (v for v in kwargs.values() if isinstance(v, Request)), None
                )
            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Request object not found in function arguments",
                )

            # Get and validate API key
            api_key = request.headers.get("X-API-Key")
            key_config = validate_api_key(api_key)

            # Use provided rate or fall back to API key configuration
            rate_limit_str = rate or key_config["rate_limit"]
            try:
                rate_limit_item = parse(rate_limit_str)
            except ValueError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid rate limit format: {str(e)}",
                )

            # Use injected storage backend for testing, else default to Redis
            storage = (
                storage_backend if storage_backend is not None else get_redis_storage()
            )
            strategy_cls = RATE_LIMIT_STRATEGIES[strategy]
            limiter = strategy_cls(storage)

            # Check rate limit
            if not await limiter.hit(rate_limit_item, api_key):
                # Get window stats for better error message
                window = await limiter.get_window_stats(rate_limit_item, api_key)
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "reset_time": window.reset_time,
                        "remaining": window.remaining,
                    },
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
