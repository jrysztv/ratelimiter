"""Module for enriching IP addresses with geolocation data using ip-api.com."""

import httpx
from typing import Dict, Any

IP_API_BASE_URL = "http://ip-api.com/json"


async def get_location(ip_address: str) -> Dict[str, Any]:
    """
    Get geolocation data for an IP address using ip-api.com.

    Args:
        ip_address: The IP address to look up

    Returns:
        Dict containing the geolocation data

    Raises:
        httpx.HTTPError: If the request fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{IP_API_BASE_URL}/{ip_address}")
        response.raise_for_status()
        return response.json()
