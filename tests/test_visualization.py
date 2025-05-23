import os
import time
import json
import pytest
import asyncio
import statistics
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Any, Tuple, Callable
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from limits.aio.storage import MemoryStorage, RedisStorage
from propcorn_ratelimiter.rate_limiter.limiter import (
    rate_limit,
    API_KEYS,
    get_redis_storage,
)

# Create a test app
app = FastAPI()
client = TestClient(app)

# Global variable to store the shared base directory for all tests in the same session
_shared_base_dir = None


def get_shared_results_directory() -> str:
    """Get or create a shared timestamped results directory for all tests in the session."""
    global _shared_base_dir
    if _shared_base_dir is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        _shared_base_dir = os.path.join("results", timestamp)

        # Create main directory and strategy subdirectories
        sliding_dir = os.path.join(_shared_base_dir, "sliding_window")
        fixed_dir = os.path.join(_shared_base_dir, "fixed_window")

        os.makedirs(sliding_dir, exist_ok=True)
        os.makedirs(fixed_dir, exist_ok=True)

    return _shared_base_dir


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


async def run_visualization_test(
    rate_limit_value: str,
    lower: int,
    higher: int,
    strategy: str,
    get_storage_fn: Callable[[], Any],
    test_key: str,
    test_key_name: str,
    endpoint_path: str,
    setup_redis_env: bool = False,
) -> Dict[str, Any]:
    """
    Run a rate limiting test and return data for visualization.
    Based on _test_high_frequency_rate_limiting but returns test data.
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
        test_duration = 3  # seconds - slightly longer for better visualization
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
        for i in range(int(actual_duration) + 1):  # Include partial last window
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

        # Return test data for visualization
        return {
            "storage_type": storage.__class__.__name__,
            "strategy": strategy,
            "expected_rate": expected_rate,
            "target_request_rate": target_request_rate,
            "actual_rate": actual_rate,
            "actual_duration": actual_duration,
            "successful_requests": total_successful,
            "window_rates": window_rates,
            "lower_limit": lower,
            "higher_limit": higher,
            "request_timestamps": successful_requests,
            "start_time": start_time,
            "end_time": end_time,
        }

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


def save_test_data(data: Dict[str, Any], strategy_dir: str, storage_type: str) -> str:
    """Save test data to JSON file."""
    filename = f"{storage_type.lower()}_data.json"
    filepath = os.path.join(strategy_dir, filename)

    # Convert timestamps to relative times for JSON serialization
    json_data = data.copy()
    if "request_timestamps" in json_data:
        start_time = json_data["start_time"]
        json_data["relative_timestamps"] = [
            t - start_time for t in json_data["request_timestamps"]
        ]
        # Remove absolute timestamps as they're not JSON serializable in a useful way
        del json_data["request_timestamps"]
        del json_data["start_time"]
        del json_data["end_time"]

    with open(filepath, "w") as f:
        json.dump(json_data, f, indent=2)

    return filepath


def create_individual_visualization(
    data: Dict[str, Any], strategy_dir: str, storage_type: str
) -> str:
    """Create visualization for individual test."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Window rates over time
    window_rates = data["window_rates"]
    time_axis = list(range(len(window_rates)))

    ax1.bar(
        time_axis,
        window_rates,
        alpha=0.7,
        color="blue" if "Memory" in storage_type else "green",
    )
    ax1.axhline(
        y=data["expected_rate"],
        color="r",
        linestyle="-",
        label=f"Expected Rate: {data['expected_rate']}/sec",
        linewidth=2,
    )
    ax1.axhline(
        y=data["higher_limit"],
        color="orange",
        linestyle="--",
        label=f"Upper Limit: {data['higher_limit']}/sec",
    )
    ax1.axhline(
        y=data["lower_limit"],
        color="green",
        linestyle="--",
        label=f"Lower Limit: {data['lower_limit']}/sec",
    )

    ax1.set_xlabel("Time Window (seconds)")
    ax1.set_ylabel("Requests per Second")
    ax1.set_title(
        f"{data['strategy'].title()} Window - {storage_type}\nWindow-by-Window Request Rates"
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_ylim(0, max(max(window_rates) + 2, data["higher_limit"] + 2))

    # Plot 2: Cumulative requests
    cumulative = []
    total = 0
    for rate in window_rates:
        total += rate
        cumulative.append(total)

    # Expected cumulative line
    expected_cumulative = [
        data["expected_rate"] * (i + 1) for i in range(len(window_rates))
    ]

    ax2.plot(
        time_axis, cumulative, "b-", marker="o", label="Actual Cumulative", linewidth=2
    )
    ax2.plot(
        time_axis, expected_cumulative, "r--", label="Expected Cumulative", linewidth=2
    )
    ax2.set_xlabel("Time Window (seconds)")
    ax2.set_ylabel("Cumulative Requests")
    ax2.set_title("Cumulative Request Count Over Time")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Add test metadata
    stats_text = (
        f"Storage: {storage_type}\n"
        f"Strategy: {data['strategy'].title()}\n"
        f"Expected Rate: {data['expected_rate']}/sec\n"
        f"Actual Rate: {data['actual_rate']:.2f}/sec\n"
        f"Duration: {data['actual_duration']:.2f}s\n"
        f"Total Requests: {data['successful_requests']}\n"
        f"Max Window: {max(window_rates)}/sec\n"
        f"Min Window: {min(window_rates)}/sec"
    )

    fig.text(
        0.02,
        0.02,
        stats_text,
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8),
    )

    plt.tight_layout(rect=[0, 0.15, 1, 0.96])

    # Save figure
    filename = f"{storage_type.lower()}_plot.png"
    filepath = os.path.join(strategy_dir, filename)
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return filepath


def create_comparison_visualization(
    memory_data: Dict[str, Any],
    redis_data: Dict[str, Any],
    strategy_dir: str,
    strategy: str,
) -> str:
    """Create comparison visualization between memory and redis storage."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Ensure both datasets have the same length for comparison
    max_windows = max(len(memory_data["window_rates"]), len(redis_data["window_rates"]))

    # Pad shorter dataset with zeros
    memory_rates = memory_data["window_rates"][:]
    redis_rates = redis_data["window_rates"][:]

    while len(memory_rates) < max_windows:
        memory_rates.append(0)
    while len(redis_rates) < max_windows:
        redis_rates.append(0)

    time_axis = list(range(max_windows))

    # Plot 1: Memory Storage Window Rates
    ax1.bar(time_axis, memory_rates, alpha=0.7, color="blue", label="Memory Storage")
    ax1.axhline(y=memory_data["expected_rate"], color="r", linestyle="-", linewidth=2)
    ax1.set_title(f"{strategy.title()} Window - Memory Storage")
    ax1.set_ylabel("Requests/sec")
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, max(max(memory_rates) + 2, memory_data["expected_rate"] + 2))

    # Plot 2: Redis Storage Window Rates
    ax2.bar(time_axis, redis_rates, alpha=0.7, color="green", label="Redis Storage")
    ax2.axhline(y=redis_data["expected_rate"], color="r", linestyle="-", linewidth=2)
    ax2.set_title(f"{strategy.title()} Window - Redis Storage")
    ax2.set_ylabel("Requests/sec")
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, max(max(redis_rates) + 2, redis_data["expected_rate"] + 2))

    # Plot 3: Side-by-side comparison
    x_pos = range(max_windows)
    width = 0.35
    ax3.bar(
        [x - width / 2 for x in x_pos],
        memory_rates,
        width,
        alpha=0.7,
        color="blue",
        label="Memory",
    )
    ax3.bar(
        [x + width / 2 for x in x_pos],
        redis_rates,
        width,
        alpha=0.7,
        color="green",
        label="Redis",
    )
    ax3.axhline(
        y=memory_data["expected_rate"],
        color="r",
        linestyle="-",
        linewidth=2,
        label="Expected Rate",
    )
    ax3.set_xlabel("Time Window (seconds)")
    ax3.set_ylabel("Requests/sec")
    ax3.set_title(f"{strategy.title()} Window - Storage Comparison")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: Cumulative comparison
    memory_cumulative = []
    redis_cumulative = []
    mem_total = redis_total = 0

    for mem_rate, redis_rate in zip(memory_rates, redis_rates):
        mem_total += mem_rate
        redis_total += redis_rate
        memory_cumulative.append(mem_total)
        redis_cumulative.append(redis_total)

    expected_cumulative = [
        memory_data["expected_rate"] * (i + 1) for i in range(max_windows)
    ]

    ax4.plot(
        time_axis,
        memory_cumulative,
        "b-",
        marker="o",
        label="Memory Cumulative",
        linewidth=2,
    )
    ax4.plot(
        time_axis,
        redis_cumulative,
        "g-",
        marker="s",
        label="Redis Cumulative",
        linewidth=2,
    )
    ax4.plot(
        time_axis, expected_cumulative, "r--", label="Expected Cumulative", linewidth=2
    )
    ax4.set_xlabel("Time Window (seconds)")
    ax4.set_ylabel("Cumulative Requests")
    ax4.set_title("Cumulative Requests Comparison")
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # Add overall comparison stats
    stats_text = (
        f"Strategy: {strategy.title()} Window\n\n"
        f"Memory Storage:\n"
        f"  Actual Rate: {memory_data['actual_rate']:.2f}/sec\n"
        f"  Total Requests: {memory_data['successful_requests']}\n"
        f"  Max Window: {max(memory_rates)}/sec\n\n"
        f"Redis Storage:\n"
        f"  Actual Rate: {redis_data['actual_rate']:.2f}/sec\n"
        f"  Total Requests: {redis_data['successful_requests']}\n"
        f"  Max Window: {max(redis_rates)}/sec\n\n"
        f"Expected Rate: {memory_data['expected_rate']}/sec"
    )

    fig.text(
        0.02,
        0.02,
        stats_text,
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8),
    )

    plt.tight_layout(rect=[0, 0.2, 1, 0.96])

    # Save figure
    filename = f"{strategy}_comparison.png"
    filepath = os.path.join(strategy_dir, filename)
    plt.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.close(fig)

    return filepath


@pytest.mark.asyncio
async def test_visualize_sliding_window():
    """Test and visualize sliding window rate limiting for both storage types."""
    base_dir = get_shared_results_directory()
    sliding_dir = os.path.join(base_dir, "sliding_window")

    # Test parameters
    rate_limit_value = "10/second"
    lower, higher = 8, 16  # Memory storage bounds
    redis_lower, redis_higher = 8, 14  # Redis storage bounds (tighter)

    # Run memory storage test
    memory_data = await run_visualization_test(
        rate_limit_value,
        lower,
        higher,
        "sliding",
        lambda: MemoryStorage(),
        "test_key_viz_sliding_memory",
        "Viz Test Sliding Memory",
        "/test-viz-sliding-memory",
    )

    # Run Redis storage test
    redis_data = await run_visualization_test(
        rate_limit_value,
        redis_lower,
        redis_higher,
        "sliding",
        configure_redis_for_environment,
        "test_key_viz_sliding_redis",
        "Viz Test Sliding Redis",
        "/test-viz-sliding-redis",
        setup_redis_env=True,
    )

    # Save data and create visualizations
    save_test_data(memory_data, sliding_dir, "MemoryStorage")
    save_test_data(redis_data, sliding_dir, "RedisStorage")

    create_individual_visualization(memory_data, sliding_dir, "MemoryStorage")
    create_individual_visualization(redis_data, sliding_dir, "RedisStorage")

    create_comparison_visualization(memory_data, redis_data, sliding_dir, "sliding")

    print(f"\nSliding window test results saved to: {sliding_dir}")


@pytest.mark.asyncio
async def test_visualize_fixed_window():
    """Test and visualize fixed window rate limiting for both storage types."""
    base_dir = get_shared_results_directory()
    fixed_dir = os.path.join(base_dir, "fixed_window")

    # Test parameters
    rate_limit_value = "10/second"
    lower, higher = 8, 16  # Memory storage bounds
    redis_lower, redis_higher = 8, 14  # Redis storage bounds (tighter)

    # Run memory storage test
    memory_data = await run_visualization_test(
        rate_limit_value,
        lower,
        higher,
        "fixed",
        lambda: MemoryStorage(),
        "test_key_viz_fixed_memory",
        "Viz Test Fixed Memory",
        "/test-viz-fixed-memory",
    )

    # Run Redis storage test
    redis_data = await run_visualization_test(
        rate_limit_value,
        redis_lower,
        redis_higher,
        "fixed",
        configure_redis_for_environment,
        "test_key_viz_fixed_redis",
        "Viz Test Fixed Redis",
        "/test-viz-fixed-redis",
        setup_redis_env=True,
    )

    # Save data and create visualizations
    save_test_data(memory_data, fixed_dir, "MemoryStorage")
    save_test_data(redis_data, fixed_dir, "RedisStorage")

    create_individual_visualization(memory_data, fixed_dir, "MemoryStorage")
    create_individual_visualization(redis_data, fixed_dir, "RedisStorage")

    create_comparison_visualization(memory_data, redis_data, fixed_dir, "fixed")

    print(f"\nFixed window test results saved to: {fixed_dir}")


# @pytest.mark.asyncio
# async def test_visualize_all_strategies():
#     """Run all visualization tests and create a final summary."""
#     print("Running complete rate limiter visualization test suite...")

#     # Create base directory
#     base_dir = get_shared_results_directory()

#     # Run both strategy tests
#     await test_visualize_sliding_window()
#     await test_visualize_fixed_window()

#     # Create overall summary
#     summary_file = os.path.join(base_dir, "test_summary.txt")
#     with open(summary_file, "w") as f:
#         f.write("Rate Limiter Visualization Test Summary\n")
#         f.write("=" * 40 + "\n\n")
#         f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
#         f.write("Tests Completed:\n")
#         f.write("- Sliding Window (Memory Storage)\n")
#         f.write("- Sliding Window (Redis Storage)\n")
#         f.write("- Fixed Window (Memory Storage)\n")
#         f.write("- Fixed Window (Redis Storage)\n\n")
#         f.write("Generated Files:\n")
#         f.write("- Individual storage visualizations\n")
#         f.write("- Strategy comparison visualizations\n")
#         f.write("- Raw test data (JSON format)\n\n")
#         f.write("Directory Structure:\n")
#         f.write(f"{base_dir}/\n")
#         f.write("├── sliding_window/\n")
#         f.write("│   ├── memorystorage_data.json\n")
#         f.write("│   ├── memorystorage_plot.png\n")
#         f.write("│   ├── redisstorage_data.json\n")
#         f.write("│   ├── redisstorage_plot.png\n")
#         f.write("│   └── sliding_comparison.png\n")
#         f.write("├── fixed_window/\n")
#         f.write("│   ├── memorystorage_data.json\n")
#         f.write("│   ├── memorystorage_plot.png\n")
#         f.write("│   ├── redisstorage_data.json\n")
#         f.write("│   ├── redisstorage_plot.png\n")
#         f.write("│   └── fixed_comparison.png\n")
#         f.write("└── test_summary.txt\n")

#     print(f"\nAll visualization tests completed!")
#     print(f"Results saved to: {base_dir}")
#     print(f"Summary saved to: {summary_file}")
