# Rate Limiter with Visualization Analysis 🚀

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI/CD](https://github.com/jrysztv/ratelimiter/actions/workflows/main.yml/badge.svg)](https://github.com/jrysztv/ratelimiter/actions)

A production-ready rate limiting service that demonstrates **Redis-based rate limiting superiority** over in-memory alternatives through comprehensive testing and visualization.

## 🔍 Key Findings

This project compares in-memory vs Redis-based rate limiting across two strategies, proving **Redis provides more consistent and reliable rate limiting** for production applications.

### 📊 Performance Analysis

**Sliding Window Results:**
- **Memory Storage**: [11, 10, 10, 4] - High variance, significant drop in final window
- **Redis Storage**: [10, 10, 11, 8] - More consistent performance across time windows

**Fixed Window Results:**
- **Memory Storage**: [10, 10, 10, 10] - Appears consistent but lacks persistence
- **Redis Storage**: [10, 10, 10, 10] - Consistent with cross-process reliability

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
- Simple implementation
- Predictable reset times  
- Potential for traffic bursts at window boundaries

**Sliding Window**: Rolling time window that moves with each request
- Smoother rate distribution
- More complex calculation
- Better user experience under load

Each strategy uses Redis for distributed storage, ensuring rate limits work across multiple server instances.

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