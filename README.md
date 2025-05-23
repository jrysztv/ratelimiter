# Rate Limiter with Visualization Analysis 🚀

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI/CD](https://github.com/jrysztv/ratelimiter/actions/workflows/main.yml/badge.svg)](https://github.com/jrysztv/ratelimiter/actions)

A production-ready rate limiting service that demonstrates **Redis-based rate limiting superiority** over in-memory alternatives through comprehensive testing and visualization.

## 🔍 Key Findings

This project compares in-memory vs Redis-based rate limiting across two strategies, proving **Redis provides more consistent and reliable rate limiting** for production applications.

### 📊 Performance Analysis

**What do these numbers mean?** Each array represents requests allowed per 1-second window during our 4-second test:

**Sliding Window Results:**
- **Memory Storage**: [11, 10, 10, 4] - High variance, significant drop in final window
  - Window 1: 11 requests allowed
  - Window 2: 10 requests allowed  
  - Window 3: 10 requests allowed
  - Window 4: 4 requests allowed (rate limiter kicked in)
- **Redis Storage**: [10, 10, 11, 8] - More consistent performance across time windows
  - Window 1: 10 requests allowed
  - Window 2: 10 requests allowed
  - Window 3: 11 requests allowed  
  - Window 4: 8 requests allowed (more predictable limiting)

**Fixed Window Results:**
- **Memory Storage**: [10, 10, 10, 10] - Appears consistent but lacks persistence
- **Redis Storage**: [10, 10, 10, 10] - Consistent with cross-process reliability

### 🔄 How Sliding Window Rate Limiting Works

Think of a sliding window like a **moving time frame** that follows each request:

```
Time:    0s----1s----2s----3s----4s
Limit:   10 requests per second

Sliding Window Movement:
┌─────────────────┐
│ Window 1 (0-1s) │ → 11 requests allowed
└─────────────────┘
     ┌─────────────────┐
     │ Window 2 (1-2s) │ → 10 requests allowed  
     └─────────────────┘
          ┌─────────────────┐
          │ Window 3 (2-3s) │ → 10 requests allowed
          └─────────────────┘
               ┌─────────────────┐
               │ Window 4 (3-4s) │ → 4 requests allowed
               └─────────────────┘
```

**Key Concept**: Every second, the window "slides" forward by 1 second. At each position, the rate limiter checks: "How many requests happened in the last 1 second?" If it's ≤10, allow the request. If >10, block it.

**Why the numbers differ:**
- **Memory Storage [11, 10, 10, 4]**: The first window allows 11 requests (slight overage), then the rate limiter becomes more aggressive, causing a dramatic drop to 4 in the final window
- **Redis Storage [10, 10, 11, 8]**: More consistent enforcement, with only small variations around the 10 req/sec limit

### 🎯 Test Parameters Explained

Our visualization tests use different acceptable bounds for each storage type:

**Memory Storage Bounds**: 8-16 requests/window (wider tolerance)
- More volatile performance due to in-process limitations
- Higher variance in race conditions and timing issues
- Acceptable range reflects real-world memory storage behavior

**Redis Storage Bounds**: 8-14 requests/window (tighter tolerance)  
- More predictable performance due to atomic Redis operations
- Better consistency across concurrent requests
- Tighter bounds reflect Redis's superior reliability

**Expected Rate**: 10 requests/second in all tests
**Test Duration**: 4 seconds with 30 requests/second attempted
**Result**: The arrays show how many requests were actually allowed in each 1-second window

### 📋 Fixed vs Sliding Window Comparison

**Fixed Window** (resets at exact intervals):
```
Time:     0s----1s----2s----3s----4s
Windows:  [────1────][────2────][────3────][────4────]
Resets:        ↑           ↑           ↑           ↑
```
- Window 1: Count requests from 0-1s, reset at 1s
- Window 2: Count requests from 1-2s, reset at 2s  
- Result: [10, 10, 10, 10] - exactly 10 per window

**Sliding Window** (moves continuously):
```
Time:     0s----1s----2s----3s----4s  
Windows:  [──1──]
               [──2──]
                    [──3──]
                         [──4──]
```
- Each window looks at the "last 1 second" from that point
- More complex calculation, but smoother rate limiting
- Result: [11, 10, 10, 4] - varies based on request timing

## 📈 Visualization Results

### Generated Performance Charts

![Fixed Window Comparison](results/2025-05-23_01-40/fixed_window/fixed_comparison.png)
*Fixed Window strategy comparison shows both storage types performing consistently at 10 req/sec windows.*

![Sliding Window Comparison](results/2025-05-23_01-40/sliding_window/sliding_comparison.png)
*Sliding Window comparison reveals Redis's superior consistency over memory storage under load.*

![Redis Storage Detail](results/2025-05-23_01-40/sliding_window/redisstorage_data.png)
*Detailed Redis storage performance showing smooth rate limiting behavior with minimal variance.*

The visualization clearly demonstrates Redis-based storage provides more predictable rate limiting, especially important for production environments where consistency is critical.

## 🌤️ Weather API Usage

The service provides rate-limited weather data with automatic location detection:

```bash
# Basic usage (using client IP for location)
curl -H "X-API-Key: test_key_1" http://your-server/weather

# With custom location via forwarded header
curl -H "X-API-Key: test_key_2" \
     -H "X-Forwarded-For: 8.8.8.8" \
     http://your-server/weather
```

**API Response:**
```json
{
  "location": {
    "city": "Vienna",
    "country": "Austria",
    "coordinates": {"latitude": 48.2324, "longitude": 16.3518}
  },
  "weather": {
    "temperature_2m": 10.6,
    "relative_humidity_2m": 73,
    "precipitation": 0.0,
    "wind_speed_10m": 16.1
  }
}
```

The endpoint fetches current weather data from Open-Meteo API and forwards it with location enrichment. When an API key is provided in the header, detailed weather forecasts are included.

## ⚙️ Rate Limiting Architecture

### API Key Bucketing
Rate limits are applied per API key using Redis-based storage:

```python
API_KEYS = {
    "test_key_1": {"name": "Basic User", "rate_limit": "5/minute"},
    "test_key_2": {"name": "Premium User", "rate_limit": "10/minute"}
}
```

### Supported Strategies

**Fixed Window**: Requests counted in fixed time intervals (e.g., 10 requests per minute starting at :00 seconds)
- **Algorithm**: Reset counter every N seconds, increment on each request
- **Pros**: Simple implementation, predictable reset times, efficient memory usage
- **Cons**: Potential for traffic bursts at window boundaries (100% of limit in first few milliseconds)
- **Use case**: When you need simple, predictable rate limiting with clear reset points

**Sliding Window**: Rolling time window that moves with each request  
- **Algorithm**: Check request count in the "last N seconds" from current time
- **Pros**: Smoother rate distribution, better user experience under load, prevents boundary bursts
- **Cons**: More complex calculation, higher memory/CPU usage, requires timestamp tracking
- **Use case**: When you need smooth, consistent rate limiting without traffic spikes

Each strategy uses Redis for distributed storage, ensuring rate limits work across multiple server instances.

### 🧮 How to Use the Rate Limit Decorator

**Basic Usage - Use API Key's Default Rate:**
```python
from fastapi import FastAPI, Request
from propcorn_ratelimiter.rate_limiter.limiter import rate_limit

app = FastAPI()

@app.get("/api/data")
@rate_limit(strategy="sliding")  # Uses API key's configured rate limit
async def get_data(request: Request):
    return {"data": "some data"}
```

**Custom Rate Limit Override:**
```python
@app.get("/weather")
@rate_limit(strategy="sliding", rate="5/minute")  # Override with custom limit
async def weather_endpoint(request: Request):
    # Your endpoint logic here
    return {"weather": "sunny"}
```

**Different Strategies:**
```python
# Fixed window - resets at exact intervals
@app.get("/api/fixed")
@rate_limit(strategy="fixed", rate="10/minute")
async def fixed_endpoint(request: Request):
    return {"message": "fixed window"}

# Sliding window - smooth rate limiting  
@app.get("/api/sliding")
@rate_limit(strategy="sliding", rate="10/minute") 
async def sliding_endpoint(request: Request):
    return {"message": "sliding window"}

# Moving window - hybrid approach
@app.get("/api/moving")
@rate_limit(strategy="moving", rate="10/minute")
async def moving_endpoint(request: Request):
    return {"message": "moving window"}
```

**Rate Limit Formats:**
```python
# Different time units supported
@rate_limit(rate="5/minute")    # 5 requests per minute
@rate_limit(rate="100/hour")    # 100 requests per hour  
@rate_limit(rate="10/second")   # 10 requests per second
@rate_limit(rate="1000/day")    # 1000 requests per day
```

**API Key Configuration:**
```python
# In your application setup
API_KEYS = {
    "basic_user": {"name": "Basic Plan", "rate_limit": "100/hour"},
    "premium_user": {"name": "Premium Plan", "rate_limit": "1000/hour"},
    "enterprise": {"name": "Enterprise", "rate_limit": "10000/hour"}
}
```

**Client Usage:**
```bash
# Include API key in request headers
curl -H "X-API-Key: basic_user" http://your-api.com/weather

# Rate limit exceeded response (HTTP 429)
{
  "detail": {
    "error": "Rate limit exceeded",
    "reset_time": 1234567890,
    "remaining": 0
  }
}
```

**Testing with Custom Storage:**
```python
from limits.aio.storage import MemoryStorage

# For testing, inject memory storage
@app.get("/test")
@rate_limit(strategy="sliding", rate="2/minute", storage_backend=MemoryStorage())
async def test_endpoint(request: Request):
    return {"message": "test"}
```

### 🎯 Redis vs Memory Storage

**Production (Redis):**
- ✅ **Persistence**: Survives application restarts
- ✅ **Distribution**: Works across multiple app instances  
- ✅ **Consistency**: Atomic operations prevent race conditions
- ✅ **Scalability**: Handles high concurrency reliably

**Development/Testing (Memory):**
- ✅ **Simple setup**: No external dependencies
- ✅ **Fast tests**: In-memory operations  
- ❌ **Lost on restart**: Counter resets when app restarts
- ❌ **Single instance**: Doesn't work with load balancers

## 🚀 Production Setup

### Prerequisites
- AWS EC2 instance (t2.micro or larger)
- GitHub repository
- Domain name (optional)

### 1. EC2 Instance Setup

```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install -y docker.io docker-compose git

# Add user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Clone repository
git clone https://github.com/jrysztv/ratelimiter.git
cd ratelimiter
```

### 2. GitHub Secrets Configuration

Add these Environment Secrets in GitHub → Settings → Environments → production:

```
EC2_SSH_KEY: [Your complete .pem file contents]
EC2_HOST: [Your EC2 public IP]
EC2_USERNAME: ubuntu
EC2_APP_PATH: /opt/ratelimiter
```

**Important**: Copy the entire SSH key including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines.

### 3. Security Group Settings

Configure EC2 Security Group:
- **SSH (22)**: Your IP only
- **HTTP (80)**: 0.0.0.0/0  
- **HTTPS (443)**: 0.0.0.0/0

### 4. Production Deployment

```bash
# Build and start with Nginx reverse proxy
docker-compose -f docker-compose.prod-nginx.yml up -d

# Verify deployment
curl http://localhost/health
# Expected: {"status":"healthy","redis":"connected"}
```

### 5. Testing Rate Limits

```bash
# Test rate limiting (test_key_1 allows 5 req/min)
for i in {1..8}; do
  curl -H "X-API-Key: test_key_1" http://your-ip/weather
  echo "Request $i completed"
done
```

After 5 requests, you should receive:
```json
{"detail": {"error": "Rate limit exceeded", "reset_time": 1234567890}}
```

## 🔮 Future Improvements

- **Redis-based API Key Store**: Currently API keys are hardcoded; implement dynamic key management with Redis
- **Rate Limit Analytics**: Add endpoint to view current usage statistics per API key
- **Custom Rate Limit Headers**: Include `X-RateLimit-Remaining` and `X-RateLimit-Reset` in responses
- **Geographic Rate Limiting**: Different limits based on client location

## 🛡️ Security Features

- **Nginx Reverse Proxy**: Terminates external connections, hides internal services
- **Dual-Layer Rate Limiting**: Nginx (network-level) + Application (business logic)
- **Security Headers**: X-Frame-Options, X-XSS-Protection, X-Content-Type-Options
- **Attack Pattern Blocking**: SQL injection, XSS, and path traversal protection
- **Non-root Container**: Application runs as limited user for security

## 📚 Technical Stack

- **Backend**: FastAPI (Python 3.11)
- **Rate Limiting**: limits library with Redis backend
- **Reverse Proxy**: Nginx with security hardening
- **Containerization**: Docker with multi-stage builds
- **CI/CD**: GitHub Actions with automated testing and deployment
- **Infrastructure**: AWS EC2 with automated provisioning

## 🧪 Development

```bash
# Setup development environment
poetry install
docker-compose -f docker-compose.dev.yml up -d redis

# Run tests
poetry run pytest tests/ -v

# Generate visualization results
poetry run pytest tests/test_visualization.py -v
```

---

*This project demonstrates production-ready rate limiting with comprehensive testing, security hardening, and automated deployment. The visualization analysis provides concrete evidence of Redis-based rate limiting advantages for scalable applications.*