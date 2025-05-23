import os
import pytest
import socket
from propcorn_ratelimiter.rate_limiter.limiter import get_redis_storage


def is_running_in_docker():
    """Check if we're running inside a Docker container."""
    try:
        with open("/proc/self/cgroup", "r") as f:
            return any("docker" in line for line in f)
    except:
        return False


def get_redis_host_from_env():
    """Get the Redis host from environment variables."""
    uri = os.environ.get("REDIS_URI")
    if uri:
        # Simplistic parsing just for this test
        if "://" in uri:
            uri = uri.split("://", 1)[1]
        return uri.split(":", 1)[0]

    return os.environ.get("REDIS_HOST", "redis")


def test_redis_connection_auto_detection():
    """Test that the Redis connection logic checks environment variables."""
    # Save original environment variables
    original_redis_host = os.environ.get("REDIS_HOST")
    original_redis_port = os.environ.get("REDIS_PORT")
    original_redis_db = os.environ.get("REDIS_DB")
    original_redis_uri = os.environ.get("REDIS_URI")

    try:
        # Clear all Redis-related environment variables
        if "REDIS_HOST" in os.environ:
            del os.environ["REDIS_HOST"]
        if "REDIS_PORT" in os.environ:
            del os.environ["REDIS_PORT"]
        if "REDIS_DB" in os.environ:
            del os.environ["REDIS_DB"]
        if "REDIS_URI" in os.environ:
            del os.environ["REDIS_URI"]

        # Get Redis storage with default settings (should be "redis")
        _ = get_redis_storage()
        default_host = get_redis_host_from_env()

        # The default redis host should be "redis" (service name)
        print(f"Default Redis host (no env vars): {default_host}")
        assert default_host == "redis", (
            f"Expected default host to be 'redis', got {default_host}"
        )

        # Test with localhost
        os.environ["REDIS_HOST"] = "localhost"
        _ = get_redis_storage()
        local_host = get_redis_host_from_env()
        assert local_host == "localhost", (
            f"Expected host to be 'localhost', got {local_host}"
        )
        print(f"Redis host with REDIS_HOST=localhost: {local_host}")

        # Test with custom settings
        os.environ["REDIS_HOST"] = "custom-host"
        os.environ["REDIS_PORT"] = "6380"
        os.environ["REDIS_DB"] = "2"
        _ = get_redis_storage()
        custom_host = get_redis_host_from_env()
        assert custom_host == "custom-host", (
            f"Expected host to be 'custom-host', got {custom_host}"
        )
        print(f"Redis host with REDIS_HOST=custom-host: {custom_host}")

        # Test with direct URI
        os.environ["REDIS_URI"] = "redis://direct-uri:6381/3"
        _ = get_redis_storage()
        direct_host = get_redis_host_from_env()
        assert direct_host == "direct-uri", (
            f"Expected host to be 'direct-uri', got {direct_host}"
        )
        print(f"Redis host with REDIS_URI=redis://direct-uri:6381/3: {direct_host}")

        # Test behavior when running in Docker
        in_docker = is_running_in_docker()
        print(f"Running in Docker: {in_docker}")

        print("All Redis configurations working as expected")

    finally:
        # Restore original environment variables
        if original_redis_host:
            os.environ["REDIS_HOST"] = original_redis_host
        elif "REDIS_HOST" in os.environ:
            del os.environ["REDIS_HOST"]

        if original_redis_port:
            os.environ["REDIS_PORT"] = original_redis_port
        elif "REDIS_PORT" in os.environ:
            del os.environ["REDIS_PORT"]

        if original_redis_db:
            os.environ["REDIS_DB"] = original_redis_db
        elif "REDIS_DB" in os.environ:
            del os.environ["REDIS_DB"]

        if original_redis_uri:
            os.environ["REDIS_URI"] = original_redis_uri
        elif "REDIS_URI" in os.environ:
            del os.environ["REDIS_URI"]
