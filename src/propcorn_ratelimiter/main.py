from fastapi import FastAPI, Request, HTTPException
from .weather.weather_request import get_weather
from .weather.geoip_enrichment import get_location
from .rate_limiter.limiter import rate_limit, get_redis_storage

app = FastAPI(title="Weather API", description="Get weather data for your location")


@app.get("/health")
async def health_check():
    """
    Health check endpoint that verifies Redis connection.
    Returns 200 if Redis is connected, 503 if not.
    """
    try:
        storage = get_redis_storage()
        # Check if storage is healthy
        is_healthy = await storage.check()
        if is_healthy:
            return {"status": "healthy", "redis": "connected"}
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unhealthy",
                    "redis": "disconnected",
                    "error": "Health check returned False",
                },
            )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "redis": "disconnected", "error": str(e)},
        )


@app.get("/weather")
@rate_limit(
    strategy="sliding", rate="5/minute"
)  # Custom rate limit for weather endpoint
async def weather_endpoint(request: Request):
    """
    Get weather data for a location based on an IP address.
    The IP address can be provided in the X-Forwarded-For header.
    If not provided, the client's IP address will be used.

    Requires a valid API key in the X-API-Key header.
    Rate limited to 5 requests per minute.
    """
    try:
        # Get IP address from header or fall back to client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host

        # Get location data from IP
        location_data = await get_location(client_ip)

        if location_data.get("status") == "fail":
            raise HTTPException(
                status_code=400, detail="Could not determine location from IP address"
            )

        # Extract coordinates
        latitude = location_data["lat"]
        longitude = location_data["lon"]

        # Get weather data
        weather_data = await get_weather(latitude, longitude)

        return {
            "location": {
                "city": location_data.get("city"),
                "country": location_data.get("country"),
                "coordinates": {"latitude": latitude, "longitude": longitude},
            },
            "weather": weather_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
