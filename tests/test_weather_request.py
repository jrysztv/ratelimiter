"""Tests for the weather request module."""

import pytest
from propcorn_ratelimiter.weather.weather_request import get_weather
import httpx


@pytest.mark.asyncio
async def test_get_weather():
    """Test that get_weather returns expected data structure."""
    # Test with coordinates for New York City
    result = await get_weather(40.7128, -74.0060)

    # Check that we got a response
    assert result is not None

    # Check for essential fields that should be present
    assert "current" in result
    assert "latitude" in result
    assert "longitude" in result

    # Check current weather data structure
    current = result["current"]
    assert "time" in current
    assert "temperature_2m" in current
    assert "relative_humidity_2m" in current
    assert "precipitation" in current
    assert "weather_code" in current
    assert "wind_speed_10m" in current
    assert "wind_direction_10m" in current

    # Verify data types
    assert isinstance(result["latitude"], (int, float))
    assert isinstance(result["longitude"], (int, float))
    assert isinstance(current["temperature_2m"], (int, float))
    assert isinstance(current["relative_humidity_2m"], (int, float))
    assert isinstance(current["precipitation"], (int, float))
    assert isinstance(current["weather_code"], (int, float))
    assert isinstance(current["wind_speed_10m"], (int, float))
    assert isinstance(current["wind_direction_10m"], (int, float))


@pytest.mark.asyncio
async def test_get_weather_invalid_coordinates():
    """Test that get_weather handles invalid coordinates appropriately."""
    # Test with invalid coordinates (outside valid range)
    with pytest.raises(httpx.HTTPError):
        await get_weather(1000.0, 2000.0)
