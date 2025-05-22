import pytest
import asyncio
import time
import statistics
from typing import List
import httpx
from httpx import ASGITransport
from propcorn_ratelimiter.main import app
from propcorn_ratelimiter.rate_limiter.limiter import API_KEYS, get_redis_storage
from limits.aio.storage import MemoryStorage


@pytest.mark.asyncio
async def test_high_frequency_sliding_redis_async():
    """
    Test sliding window rate limiting with RedisStorage using async HTTP client.
    This avoids the deadlock issues with TestClient + async Redis operations.
    """
    # Add test key
    test_key = "test_key_sliding_redis_async"
    API_KEYS[test_key] = {
        "name": "Test Client Sliding Redis Async",
        "rate_limit": "5/minute",
    }

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Test basic rate limiting functionality
            storage = get_redis_storage()

            # Clear any existing data
            await storage.clear(test_key)

            # Make requests and count successes
            successful_requests = 0
            rate_limited_requests = 0

            # Test with a 10/second rate limit by making 15 requests quickly
            for i in range(15):
                response = await client.get("/weather", headers={"X-API-Key": test_key})

                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code == 429:
                    rate_limited_requests += 1

                # Small delay to avoid overwhelming
                await asyncio.sleep(0.05)

            print(f"\nAsync Redis Test Results:")
            print(f"Successful requests: {successful_requests}")
            print(f"Rate limited requests: {rate_limited_requests}")
            print(f"Total requests: {successful_requests + rate_limited_requests}")

            # Verify that rate limiting is working
            assert successful_requests > 0, "Should have some successful requests"
            assert rate_limited_requests > 0, "Should have some rate-limited requests"
            assert successful_requests <= 10, (
                "Should not exceed rate limit significantly"
            )

    finally:
        # Clean up
        if test_key in API_KEYS:
            del API_KEYS[test_key]


@pytest.mark.asyncio
async def test_high_frequency_fixed_redis_async():
    """
    Test fixed window rate limiting with RedisStorage using async HTTP client.
    """
    # Add test key
    test_key = "test_key_fixed_redis_async"
    API_KEYS[test_key] = {
        "name": "Test Client Fixed Redis Async",
        "rate_limit": "5/minute",
    }

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Test basic rate limiting functionality
            storage = get_redis_storage()

            # Clear any existing data
            await storage.clear(test_key)

            # Make requests and count successes
            successful_requests = 0
            rate_limited_requests = 0

            # Test with a 10/second rate limit by making 15 requests quickly
            for i in range(15):
                response = await client.get("/weather", headers={"X-API-Key": test_key})

                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code == 429:
                    rate_limited_requests += 1

                # Small delay
                await asyncio.sleep(0.05)

            print(f"\nAsync Redis Fixed Test Results:")
            print(f"Successful requests: {successful_requests}")
            print(f"Rate limited requests: {rate_limited_requests}")
            print(f"Total requests: {successful_requests + rate_limited_requests}")

            # Verify that rate limiting is working
            assert successful_requests > 0, "Should have some successful requests"
            assert rate_limited_requests > 0, "Should have some rate-limited requests"
            assert successful_requests <= 10, (
                "Should not exceed rate limit significantly"
            )

    finally:
        # Clean up
        if test_key in API_KEYS:
            del API_KEYS[test_key]


@pytest.mark.asyncio
async def test_redis_connection_via_app():
    """Test that Redis connection works through the app's health endpoint"""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

        print(f"Health check response: {response.status_code}")
        print(f"Health check body: {response.json()}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"] == "connected"
