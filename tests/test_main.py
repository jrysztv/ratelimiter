"""Tests for the FastAPI weather endpoint."""

import pytest
from fastapi.testclient import TestClient
from limits.aio.storage import MemoryStorage
from propcorn_ratelimiter.main import app
from propcorn_ratelimiter.rate_limiter.limiter import get_redis_storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    """Inject in-memory storage for all tests."""
    storage = MemoryStorage()
    monkeypatch.setattr(
        "propcorn_ratelimiter.rate_limiter.limiter.get_redis_storage", lambda: storage
    )
    return storage


@pytest.fixture
def mock_location_data():
    return {
        "status": "success",
        "country": "United States",
        "city": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
    }


@pytest.fixture
def mock_weather_data():
    return {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "current": {
            "time": "2024-03-20T12:00",
            "temperature_2m": 20.5,
            "relative_humidity_2m": 65,
            "precipitation": 0,
            "weather_code": 0,
            "wind_speed_10m": 5.2,
            "wind_direction_10m": 180,
        },
    }


async def mock_get_location(*args, **kwargs):
    return {
        "status": "success",
        "country": "United States",
        "city": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
    }


async def mock_get_weather(*args, **kwargs):
    return {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "current": {
            "time": "2024-03-20T12:00",
            "temperature_2m": 20.5,
            "relative_humidity_2m": 65,
            "precipitation": 0,
            "weather_code": 0,
            "wind_speed_10m": 5.2,
            "wind_direction_10m": 180,
        },
    }


def test_weather_endpoint_success(monkeypatch):
    """Test successful weather data retrieval using client IP."""
    monkeypatch.setattr("propcorn_ratelimiter.main.get_location", mock_get_location)
    monkeypatch.setattr("propcorn_ratelimiter.main.get_weather", mock_get_weather)

    response = client.get("/weather", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 200
    data = response.json()

    # Check location data
    assert data["location"]["city"] == "New York"
    assert data["location"]["country"] == "United States"
    assert data["location"]["coordinates"]["latitude"] == 40.7128
    assert data["location"]["coordinates"]["longitude"] == -74.0060

    # Check weather data
    expected_weather = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "current": {
            "time": "2024-03-20T12:00",
            "temperature_2m": 20.5,
            "relative_humidity_2m": 65,
            "precipitation": 0,
            "weather_code": 0,
            "wind_speed_10m": 5.2,
            "wind_direction_10m": 180,
        },
    }
    assert data["weather"] == expected_weather


def test_weather_endpoint_with_forwarded_ip(monkeypatch):
    """Test successful weather data retrieval using X-Forwarded-For header."""
    monkeypatch.setattr("propcorn_ratelimiter.main.get_location", mock_get_location)
    monkeypatch.setattr("propcorn_ratelimiter.main.get_weather", mock_get_weather)

    # Test with single IP
    response = client.get(
        "/weather", headers={"X-API-Key": "test_key_1", "X-Forwarded-For": "1.2.3.4"}
    )
    assert response.status_code == 200
    data = response.json()

    # Check location data
    assert data["location"]["city"] == "New York"
    assert data["location"]["country"] == "United States"
    assert data["location"]["coordinates"]["latitude"] == 40.7128
    assert data["location"]["coordinates"]["longitude"] == -74.0060

    # Test with multiple IPs
    response = client.get(
        "/weather",
        headers={
            "X-API-Key": "test_key_1",
            "X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Check location data
    assert data["location"]["city"] == "New York"
    assert data["location"]["country"] == "United States"
    assert data["location"]["coordinates"]["latitude"] == 40.7128
    assert data["location"]["coordinates"]["longitude"] == -74.0060

    # Check weather data
    expected_weather = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "current": {
            "time": "2024-03-20T12:00",
            "temperature_2m": 20.5,
            "relative_humidity_2m": 65,
            "precipitation": 0,
            "weather_code": 0,
            "wind_speed_10m": 5.2,
            "wind_direction_10m": 180,
        },
    }
    assert data["weather"] == expected_weather


async def mock_get_location_fail(*args, **kwargs):
    return {"status": "fail", "message": "Invalid IP address"}


def test_weather_endpoint_location_failure(monkeypatch):
    """Test weather endpoint when location lookup fails."""
    monkeypatch.setattr(
        "propcorn_ratelimiter.main.get_location", mock_get_location_fail
    )

    response = client.get("/weather", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Could not determine location from IP address"


async def mock_get_weather_fail(*args, **kwargs):
    raise Exception("Weather API error")


def test_weather_endpoint_weather_api_failure(monkeypatch):
    """Test weather endpoint when weather API call fails."""
    monkeypatch.setattr("propcorn_ratelimiter.main.get_location", mock_get_location)
    monkeypatch.setattr("propcorn_ratelimiter.main.get_weather", mock_get_weather_fail)

    response = client.get("/weather", headers={"X-API-Key": "test_key_1"})
    assert response.status_code == 500
    assert "Weather API error" in response.json()["detail"]
