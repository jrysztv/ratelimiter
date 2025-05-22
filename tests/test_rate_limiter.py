import os
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from limits import parse
from limits.aio.storage import MemoryStorage, RedisStorage
from limits.aio.strategies import (
    FixedWindowRateLimiter,
    MovingWindowRateLimiter,
    SlidingWindowCounterRateLimiter,
)

from propcorn_ratelimiter.rate_limiter.limiter import (
    rate_limit,
    validate_api_key,
    API_KEYS,
    get_redis_storage,
)

import asyncio
import time
from typing import List, Callable, Any, Optional
import statistics

# Create a test app
app = FastAPI()

client = TestClient(app)


def test_validate_api_key():
    # Test valid API key
    result = validate_api_key("test_key_1")
    assert result == API_KEYS["test_key_1"]

    # Test missing API key
    with pytest.raises(Exception) as exc_info:
        validate_api_key("")
    assert exc_info.value.status_code == 401

    # Test invalid API key
    with pytest.raises(Exception) as exc_info:
        validate_api_key("invalid_key")
    assert exc_info.value.status_code == 401


def test_get_redis_storage():
    # Test with direct URI
    os.environ["REDIS_URI"] = "redis://localhost:6379/0"
    storage = get_redis_storage()
    assert isinstance(storage, RedisStorage)

    # Test with individual components
    del os.environ["REDIS_URI"]
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_DB"] = "1"
    storage = get_redis_storage()
    assert isinstance(storage, RedisStorage)


def test_invalid_strategy():
    with pytest.raises(ValueError) as exc_info:

        @rate_limit(strategy="invalid")
        async def test_endpoint(request: Request):
            return {"message": "success"}

    assert "Invalid strategy" in str(exc_info.value)


def test_invalid_rate_limit():
    @app.get("/test-invalid-rate")
    @rate_limit(strategy="sliding", rate="invalid")
    async def test_endpoint(request: Request):
        return {"message": "success"}

    response = client.get("/test-invalid-rate", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 500
    assert "Invalid rate limit format" in response.json()["detail"]


def test_missing_request():
    @app.get("/test-missing-request")
    @rate_limit(strategy="sliding")
    async def test_endpoint():  # No request parameter
        return {"message": "success"}

    response = client.get("/test-missing-request", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 500
    assert "Request object not found" in response.json()["detail"]


def test_api_key_default_rate():
    storage = MemoryStorage()

    @app.get("/test-default-rate")
    @rate_limit(strategy="sliding", storage_backend=storage)  # No rate parameter
    async def test_endpoint(request: Request):
        return {"message": "success"}

    # Should use API_KEYS["test_key_1"]["rate_limit"] which is "5/minute"
    for _ in range(5):
        response = client.get("/test-default-rate", headers={"X-API-Key": "test_key_1"})
        assert response.status_code == 200
    response = client.get("/test-default-rate", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_decorator():
    storage = MemoryStorage()

    @app.get("/test-decorator")
    @rate_limit(strategy="sliding", rate="2/minute", storage_backend=storage)
    async def test_endpoint(request: Request):
        return {"message": "success"}

    response = client.get("/test-decorator", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 200
    assert response.json() == {"message": "success"}
    response = client.get("/test-decorator")
    assert response.status_code == 401
    response = client.get("/test-decorator", headers={"X-API-Key": "invalid_key"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    storage = MemoryStorage()

    @app.get("/test-exceeded")
    @rate_limit(strategy="sliding", rate="2/minute", storage_backend=storage)
    async def test_endpoint(request: Request):
        return {"message": "success"}

    for _ in range(2):
        response = client.get("/test-exceeded", headers={"X-API-Key": "test_key_1"})
        assert response.status_code == 200
    response = client.get("/test-exceeded", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 429
    detail = response.json()["detail"]
    assert "error" in detail
    assert "reset_time" in detail
    assert "remaining" in detail


@pytest.mark.asyncio
async def test_different_rate_limits():
    storage = MemoryStorage()

    @app.get("/test-custom")
    @rate_limit(strategy="sliding", rate="1/minute", storage_backend=storage)
    async def test_custom_endpoint(request: Request):
        return {"message": "success"}

    response = client.get("/test-custom", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 200
    response = client.get("/test-custom", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_different_strategies():
    for strategy, url in zip(
        ["fixed", "moving", "sliding"], ["/test-fixed", "/test-moving", "/test-sliding"]
    ):
        storage = MemoryStorage()

        @app.get(url)
        @rate_limit(strategy=strategy, rate="2/minute", storage_backend=storage)
        async def endpoint(request: Request):
            return {"message": "success"}

        for _ in range(2):
            response = client.get(url, headers={"X-API-Key": "test_key_1"})
            assert response.status_code == 200
        response = client.get(url, headers={"X-API-Key": "test_key_1"})
        assert response.status_code == 429


@pytest.mark.asyncio
@pytest.mark.parametrize("rate_limit_value,lower,higher", [("10/second", 8, 16)])
async def test_high_frequency_sliding_memory(
    rate_limit_value: str, lower: int, higher: int
):
    """
    Test sliding window rate limiting with MemoryStorage.
    Makes requests at 30/second for 5 seconds and verifies proper rate limiting.
    Note: MemoryStorage has slightly higher tolerance due to in-memory nature.
    """
    await _test_high_frequency_rate_limiting(
        rate_limit_value,
        lower,
        higher,
        "sliding",
        lambda: MemoryStorage(),
        "test_key_sliding_memory",
        "Test Client Sliding Memory",
        "/test-high-frequency-sliding-memory",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("rate_limit_value,lower,higher", [("10/second", 8, 14)])
async def test_high_frequency_sliding_redis(
    rate_limit_value: str, lower: int, higher: int
):
    """
    Test sliding window rate limiting with RedisStorage.
    Makes requests at 30/second for 5 seconds and verifies proper rate limiting.
    """
    await _test_high_frequency_rate_limiting(
        rate_limit_value,
        lower,
        higher,
        "sliding",
        configure_redis_for_environment,
        "test_key_sliding_redis",
        "Test Client Sliding Redis",
        "/test-high-frequency-sliding-redis",
        setup_redis_env=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("rate_limit_value,lower,higher", [("10/second", 8, 16)])
async def test_high_frequency_fixed_memory(
    rate_limit_value: str, lower: int, higher: int
):
    """
    Test fixed window rate limiting with MemoryStorage.
    Makes requests at 30/second for 5 seconds and verifies proper rate limiting.
    """
    await _test_high_frequency_rate_limiting(
        rate_limit_value,
        lower,
        higher,
        "fixed",
        lambda: MemoryStorage(),
        "test_key_fixed_memory",
        "Test Client Fixed Memory",
        "/test-high-frequency-fixed-memory",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("rate_limit_value,lower,higher", [("10/second", 8, 14)])
async def test_high_frequency_fixed_redis(
    rate_limit_value: str, lower: int, higher: int
):
    """
    Test fixed window rate limiting with RedisStorage.
    Makes requests at 30/second for 5 seconds and verifies proper rate limiting.
    """
    await _test_high_frequency_rate_limiting(
        rate_limit_value,
        lower,
        higher,
        "fixed",
        configure_redis_for_environment,
        "test_key_fixed_redis",
        "Test Client Fixed Redis",
        "/test-high-frequency-fixed-redis",
        setup_redis_env=True,
    )


def configure_redis_for_environment():
    """
    Configure Redis connection based on environment:
    - Local dev: localhost:6379
    - Container: redis:6379 (service name in docker-compose)
    - GitHub Actions: Using the service container exposed on localhost

    Returns the appropriate RedisStorage instance.
    """
    # Check if the REDIS_URI environment variable is already set
    if "REDIS_URI" in os.environ:
        return get_redis_storage()

    # Try connecting to Redis service (container environment)
    if "CI" in os.environ:
        # GitHub Actions - the service is exposed on localhost
        os.environ["REDIS_HOST"] = "localhost"
    else:
        # Try the Docker service name first, if that fails fall back to localhost
        try:
            import socket

            socket.gethostbyname("redis")
            os.environ["REDIS_HOST"] = "redis"
        except socket.gaierror:
            # Fall back to localhost
            os.environ["REDIS_HOST"] = "localhost"

    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_DB"] = "0"

    return get_redis_storage()


async def _test_high_frequency_rate_limiting(
    rate_limit_value: str,
    lower: int,
    higher: int,
    strategy: str,
    get_storage_fn: Callable[[], Any],
    test_key: str,
    test_key_name: str,
    endpoint_path: str,
    setup_redis_env: bool = False,
):
    """
    Shared implementation for high frequency rate limiting tests.

    Args:
        rate_limit_value: The rate limit string (e.g. "10/second")
        lower: Lower bound for expected requests in any window
        higher: Upper bound for expected requests in any window
        strategy: Rate limiting strategy to use
        get_storage_fn: Function to get storage backend
        test_key: API key to create for testing
        test_key_name: Name for the API key
        endpoint_path: Path for the test endpoint
        setup_redis_env: Whether to set up Redis environment variables
    """
    # Create a new test key specifically for this test
    API_KEYS[test_key] = {
        "name": test_key_name,
        "rate_limit": "5/minute",  # Default rate limit
    }

    # Store original environment variables to restore them later
    original_env = {}
    if setup_redis_env:
        for var in ["REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_URI"]:
            if var in os.environ:
                original_env[var] = os.environ[var]

    try:
        storage = get_storage_fn()

        # Parameters for the test - reduced for Docker compatibility
        test_duration = 2  # seconds
        target_request_rate = 30  # requests per second - less aggressive
        total_requests = test_duration * target_request_rate

        @app.get(endpoint_path)
        @rate_limit(strategy=strategy, rate=rate_limit_value, storage_backend=storage)
        async def test_endpoint(request: Request):
            return {"message": "success"}

        successful_requests: List[float] = []
        start_time = time.time()

        # Use async client for Redis tests to avoid deadlocks in Docker
        use_async_client = setup_redis_env

        if use_async_client:
            # Import here to avoid circular imports
            import httpx
            from httpx import ASGITransport

            async def make_request():
                try:
                    async with httpx.AsyncClient(
                        transport=ASGITransport(app=app), base_url="http://test"
                    ) as async_client:
                        response = await async_client.get(
                            endpoint_path, headers={"X-API-Key": test_key}
                        )
                        if response.status_code == 200:
                            successful_requests.append(time.time())
                except Exception:
                    pass
        else:

            async def make_request():
                try:
                    response = client.get(
                        endpoint_path, headers={"X-API-Key": test_key}
                    )
                    if response.status_code == 200:
                        successful_requests.append(time.time())
                except Exception:
                    pass

        # Run requests with a smaller batch size to avoid timeout issues
        batch_size = 10
        for i in range(0, total_requests, batch_size):
            tasks = []
            for _ in range(min(batch_size, total_requests - i)):
                tasks.append(asyncio.create_task(make_request()))
                await asyncio.sleep(1 / target_request_rate)

            await asyncio.gather(*tasks)

        end_time = time.time()

        actual_duration = end_time - start_time
        actual_rate = len(successful_requests) / actual_duration

        window_rates = []
        for i in range(int(actual_duration)):
            window_start = start_time + i
            window_end = window_start + 1
            window_requests = sum(
                1 for t in successful_requests if window_start <= t < window_end
            )
            window_rates.append(window_requests)

        expected_rate = int(rate_limit_value.split("/")[0])

        # Verify rate limiting is working
        total_successful = len(successful_requests)
        assert total_successful > 0, "No successful requests were made"
        assert total_successful <= expected_rate * actual_duration * 1.2, (
            f"Got {total_successful} successful requests, which exceeds the expected limit of "
            f"{expected_rate * actual_duration * 1.2} over {actual_duration:.1f} seconds"
        )

        # Check that no window exceeds the upper limit
        assert max(window_rates) <= higher, (
            f"Found window with {max(window_rates)} requests, exceeding upper limit of {higher}"
        )

        print(f"\nRate Limiter Test with {strategy} strategy:")
        print(f"Storage: {storage.__class__.__name__}")
        print(f"Expected rate: {expected_rate}/second")
        print(f"Actual average rate: {actual_rate:.2f}/second")
        print(f"Window rates: {window_rates}")
        print(f"Total successful requests: {total_successful}")
        print(f"Max requests in any 1-second window: {max(window_rates)}")
        print(
            f"Min requests in any 1-second window: {min(window_rates) if window_rates else 0}"
        )
        if len(window_rates) > 1:
            print(
                f"Standard deviation of window rates: {statistics.stdev(window_rates):.2f}"
            )
    finally:
        # Clean up: remove the test key
        if test_key in API_KEYS:
            del API_KEYS[test_key]

        # Restore original environment variables
        if setup_redis_env:
            for var in ["REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_URI"]:
                if var in original_env:
                    os.environ[var] = original_env[var]
                elif var in os.environ:
                    del os.environ[var]
