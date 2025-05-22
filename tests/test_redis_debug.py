import os
import asyncio
import sys
import pytest
from limits.aio.storage import RedisStorage
from propcorn_ratelimiter.rate_limiter.limiter import get_redis_storage

sys.path.append("/app/src")


async def test_redis_connection():
    print("Testing Redis connection in Docker...")

    # Set environment variables for Redis
    os.environ["REDIS_HOST"] = "redis"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_DB"] = "0"

    try:
        # Get Redis storage
        storage = get_redis_storage()
        print(f"Storage type: {type(storage)}")
        print(f"Storage URI should be: redis://redis:6379/0")

        # Test connection
        print("Checking Redis connection...")
        result = await storage.check()
        print(f"Redis check result: {result}")

        if result:
            print("✅ Redis connection successful!")
            # Try a simple operation
            await storage.incr("test_key", 60, 1)
            value = await storage.get("test_key")
            print(f"Test key value: {value}")
            await storage.clear("test_key")
            print("✅ Basic Redis operations successful!")
        else:
            print("❌ Redis check returned False")

        return result

    except Exception as e:
        print(f"❌ Error testing Redis: {e}")
        import traceback

        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_redis_connection_basic():
    """Basic test to check if we can connect to Redis at all"""
    try:
        storage = get_redis_storage()
        print(f"Storage type: {type(storage)}")
        print(f"Storage URI: {getattr(storage, '_uri', 'unknown')}")
        result = await storage.check()
        print(f"Redis check result: {result}")
        assert result is True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        raise


@pytest.mark.asyncio
async def test_redis_basic_operations():
    """Test basic Redis operations"""
    try:
        storage = get_redis_storage()

        # Test basic increment
        print("Testing basic increment...")
        result = await storage.incr("test_key", 60, 1)
        print(f"Increment result: {result}")

        # Test get
        print("Testing get...")
        value = await storage.get("test_key")
        print(f"Get result: {value}")

        # Test clear
        print("Testing clear...")
        await storage.clear("test_key")

        print("Basic operations completed successfully")

    except Exception as e:
        print(f"Redis basic operations failed: {e}")
        raise


@pytest.mark.asyncio
async def test_redis_concurrent_operations():
    """Test concurrent Redis operations to see if there's a deadlock"""
    try:
        storage = get_redis_storage()

        async def increment_task(task_id):
            try:
                print(f"Task {task_id} starting...")
                result = await storage.incr(f"concurrent_test_{task_id}", 60, 1)
                print(f"Task {task_id} completed with result: {result}")
                return result
            except Exception as e:
                print(f"Task {task_id} failed: {e}")
                raise

        print("Starting 5 concurrent tasks...")
        tasks = [increment_task(i) for i in range(5)]

        # Use asyncio.wait_for to prevent hanging
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=10.0)
        print(f"All tasks completed: {results}")

        # Clean up
        for i in range(5):
            await storage.clear(f"concurrent_test_{i}")

    except asyncio.TimeoutError:
        print("Concurrent operations timed out!")
        raise
    except Exception as e:
        print(f"Concurrent operations failed: {e}")
        raise


if __name__ == "__main__":
    result = asyncio.run(test_redis_connection())
    print(f"Final result: {result}")
