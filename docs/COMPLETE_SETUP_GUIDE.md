# Complete Production Setup Guide 🚀

This guide walks you through setting up a production rate limiter service with automated CI/CD deployment to AWS EC2.

## 📋 Prerequisites

- AWS Account with EC2 access
- GitHub account
- Local machine with SSH client
- Basic familiarity with Docker and Git

## 🔧 Phase 1: AWS EC2 Setup

### 1.1 Launch EC2 Instance

1. **Go to AWS EC2 Console**
2. **Launch Instance:**
   - **AMI**: Ubuntu Server 22.04 LTS
   - **Instance Type**: t2.micro (Free Tier) or larger
   - **Key Pair**: Create new or use existing `.pem` file
   - **Security Group**: Create new with these rules:
     - SSH (22): Your IP only
     - HTTP (80): 0.0.0.0/0
     - HTTPS (443): 0.0.0.0/0

### 1.2 Connect and Install Dependencies

```bash
# Connect to your instance
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR-EC2-IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose git

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Verify Docker installation
docker --version
docker-compose --version
```

### 1.3 Setup Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/ratelimiter
sudo chown ubuntu:ubuntu /opt/ratelimiter
cd /opt/ratelimiter

# Clone the repository
git clone https://github.com/jrysztv/ratelimiter.git .

# Test Docker setup
docker-compose -f docker-compose.prod-nginx.yml build
```

## 🔐 Phase 2: GitHub Configuration

### 2.1 Repository Setup

If you don't have a GitHub repository yet:

```bash
# Create new repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO

# Copy project files here
# Commit and push initial version
```

### 2.2 Environment Secrets Setup

**Critical Step**: Configure GitHub Environment Secrets correctly.

1. **Go to your GitHub repository**
2. **Navigate to**: Settings → Environments
3. **Create environment**: `production`
4. **Add these secrets**:

```bash
# Required secrets:
EC2_SSH_KEY     = [Complete contents of your .pem file]
EC2_HOST        = [Your EC2 public IP address]
EC2_USERNAME    = ubuntu
EC2_APP_PATH    = /opt/ratelimiter
```

### 2.3 SSH Key Secret Format

**CRITICAL**: The SSH key must be copied exactly as-is:

```bash
# Display your key content:
cat ~/.ssh/your-key.pem

# Copy EVERYTHING including these lines:
-----BEGIN RSA PRIVATE KEY-----
[all the key content]
-----END RSA PRIVATE KEY-----
```

**Common Mistakes:**
- ❌ Missing BEGIN/END lines
- ❌ Extra spaces or newlines
- ❌ Windows line endings (CRLF)
- ❌ Partial key content

## 🚀 Phase 3: Deployment Pipeline

### 3.1 Workflow Overview

The GitHub Actions workflow consists of:

1. **Test Stage**: Runs unit tests (Redis tests may fail in CI, that's expected)
2. **Build Stage**: Builds Docker images and tests with Nginx
3. **Deploy Stage**: Deploys to EC2 using SSH

### 3.2 Common Build Issues and Solutions

**Issue**: `docker-compose: command not found`
**Solution**: The workflow uses `docker compose` (v2 syntax) for GitHub Actions and `docker-compose` (legacy) for EC2.

**Issue**: SSH connection failures
**Solution**: Verify your SSH key secret format and EC2 security group settings.

**Issue**: Redis test failures in CI
**Solution**: Expected behavior. Core tests pass, Redis tests fail gracefully.

### 3.3 Trigger Deployment

```bash
# Make a commit to trigger deployment
echo "Deployment triggered at $(date)" >> deployment-log.txt
git add .
git commit -m "trigger: automated deployment"
git push origin main
```

## 🔍 Phase 4: Verification and Testing

### 4.1 Health Check

```bash
# Test health endpoint
curl http://YOUR-EC2-IP/health
# Expected: {"status":"healthy","redis":"connected"}

# Test API documentation
curl http://YOUR-EC2-IP/docs
# Should return HTML documentation page
```

### 4.2 Rate Limiting Test

```bash
# Test with valid API key (5 requests/minute limit)
for i in {1..8}; do
  echo "Request $i:"
  curl -H "X-API-Key: test_key_1" http://YOUR-EC2-IP/weather
  echo -e "\n---"
  sleep 2
done
```

**Expected Behavior:**
- First 5 requests: Return weather data
- Requests 6-8: Return rate limit exceeded error

### 4.3 Security Verification

```bash
# Check security headers
curl -I http://YOUR-EC2-IP/health

# Should include headers like:
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# X-Content-Type-Options: nosniff
```

## 🛠️ Phase 5: Troubleshooting

### 5.1 Common Deployment Issues

**Container Not Starting:**
```bash
# Check container status
docker ps -a

# View logs
docker-compose -f docker-compose.prod-nginx.yml logs

# Restart containers
docker-compose -f docker-compose.prod-nginx.yml down
docker-compose -f docker-compose.prod-nginx.yml up -d
```

**GitHub Actions Failures:**
1. Check the Actions tab in your repository
2. Common issues:
   - SSH key format problems
   - EC2 security group blocking access
   - Insufficient EC2 disk space

**Redis Connection Issues:**
```bash
# Test Redis connectivity
docker exec -it ratelimiter-redis-1 redis-cli ping
# Should return: PONG
```

### 5.2 Monitoring and Maintenance

**Check Service Status:**
```bash
# Service health
curl http://localhost/health

# Container resources
docker stats

# Disk usage
df -h
```

**Update Deployment:**
```bash
# Manual update (on EC2)
cd /opt/ratelimiter
git pull origin main
docker-compose -f docker-compose.prod-nginx.yml down
docker-compose -f docker-compose.prod-nginx.yml up -d --build
```

## 🎯 Phase 6: Production Optimization

### 6.1 Performance Tuning

**Nginx Configuration:**
- Rate limiting: 10 req/sec (network level)
- Worker processes: Auto-detected
- Connection limits: Default

**Redis Configuration:**
- Memory policy: allkeys-lru
- Max memory: 50% of available RAM
- Persistence: RDB snapshots

### 6.2 Monitoring Setup

**Basic Monitoring:**
```bash
# Create monitoring script
cat > /opt/ratelimiter/monitor.sh << 'EOF'
#!/bin/bash
echo "=== Service Health Check ==="
curl -s http://localhost/health | jq .
echo -e "\n=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo -e "\n=== Resource Usage ==="
docker stats --no-stream
EOF

chmod +x /opt/ratelimiter/monitor.sh
```

### 6.3 Backup Strategy

**Redis Data Backup:**
```bash
# Create backup script
cat > /opt/ratelimiter/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/ratelimiter/backups"
mkdir -p $BACKUP_DIR
docker exec ratelimiter-redis-1 redis-cli BGSAVE
docker cp ratelimiter-redis-1:/data/dump.rdb "$BACKUP_DIR/redis-$(date +%Y%m%d-%H%M%S).rdb"
EOF

chmod +x /opt/ratelimiter/backup.sh
```

## ✅ Success Criteria

Your deployment is successful when:

1. ✅ Health endpoint returns healthy status
2. ✅ Weather API responds with location data
3. ✅ Rate limiting blocks excess requests
4. ✅ Security headers are present
5. ✅ GitHub Actions deploy without errors
6. ✅ Containers restart automatically after EC2 reboot

## 🎉 Next Steps

With your production system running:

1. **Custom Domain**: Configure Route 53 and SSL certificates
2. **Monitoring**: Set up CloudWatch or Prometheus
3. **Scaling**: Implement auto-scaling groups
4. **API Keys**: Move from hardcoded to database-driven keys
5. **Analytics**: Add request logging and usage analytics

---

*This guide is based on real deployment experience. If you encounter issues not covered here, check the GitHub Issues or create a new one with details.* 