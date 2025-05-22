"""Module for fetching weather data using Open-Meteo API."""

import httpx
from typing import Dict, Any

OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get current weather data for given coordinates using Open-Meteo API.

    Args:
        latitude: The latitude coordinate
        longitude: The longitude coordinate

    Returns:
        Dict containing the current weather data

    Raises:
        httpx.HTTPError: If the request fails
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m",
        "timezone": "auto",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(OPEN_METEO_BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
