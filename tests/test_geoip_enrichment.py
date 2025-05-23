"""Tests for the geoip enrichment module."""

import pytest
from propcorn_ratelimiter.weather.geoip_enrichment import get_location


@pytest.mark.asyncio
async def test_get_location():
    """Test that get_location returns expected data structure."""
    # Test with a known IP (Google's DNS)
    result = await get_location("8.8.8.8")

    # Check that we got a response
    assert result is not None

    # Check for essential fields that should be present
    assert "country" in result
    assert "city" in result
    assert "lat" in result
    assert "lon" in result

    # Verify the data types
    assert isinstance(result["country"], str)
    assert isinstance(result["city"], str)
    assert isinstance(result["lat"], (int, float))
    assert isinstance(result["lon"], (int, float))


@pytest.mark.asyncio
async def test_get_location_invalid_ip():
    """Test that get_location handles invalid IP addresses appropriately."""
    result = await get_location("invalid.ip.address")
    assert result is not None
    assert "status" in result
    assert (
        result["status"] == "fail"
    )  # ip-api.com returns status: "fail" for invalid IPs
