# Complete Setup Guide for Propcorn Rate Limiter

This guide provides step-by-step instructions to set up the complete CI/CD pipeline for the Propcorn Rate Limiter project, from local development to AWS EC2 deployment.

## 🎯 Overview

This setup will give you:
- ✅ Local development environment
- ✅ Automated testing with visualizations
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Automated deployment to AWS EC2
- ✅ Production-ready containerized application

## 📋 Prerequisites

- **Local Machine**: Git, Docker, Docker Compose
- **AWS Account**: EC2 access
- **GitHub Account**: Repository access
- **Domain/IP**: For production access (optional)

## 🚀 Quick Start

### Option 1: Use the Quick Setup Script
```bash
# Clone and run the setup script
git clone https://github.com/jrysztv/ratelimiter.git
cd ratelimiter
chmod +x scripts/quick-setup.sh
./scripts/quick-setup.sh
```

### Option 2: Manual Setup
Follow the detailed steps below for complete control.

## 📝 Step-by-Step Setup

### Step 1: Local Development Setup

#### 1.1 Clone Repository
```bash
git clone https://github.com/jrysztv/ratelimiter.git
cd ratelimiter
```

#### 1.2 Install Dependencies
```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

#### 1.3 Start Development Environment
```bash
# Start development containers
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# Test the application
curl http://localhost:8000/health
```

#### 1.4 Run Tests
```bash
# Run standard tests
poetry run pytest tests/ -v

# Generate visualization results
poetry run pytest tests/test_visualization.py -v

# Check test results
ls -la results/
```

### Step 2: AWS EC2 Setup

#### 2.1 Create EC2 Instance
Follow the detailed guide in [EC2_SETUP.md](./EC2_SETUP.md):

1. **Launch Instance**: Ubuntu 22.04 LTS, t2.micro/t3.small
2. **Security Group**: SSH (22), HTTP (80), Custom TCP (8000)
3. **Key Pair**: Create and download `propcorn-ratelimiter-key.pem`

#### 2.2 Connect and Configure EC2
```bash
# Connect to EC2
chmod 400 propcorn-ratelimiter-key.pem
ssh -i propcorn-ratelimiter-key.pem ubuntu@<EC2_PUBLIC_IP>

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
sudo mkdir -p /opt/propcorn-ratelimiter
sudo chown ubuntu:ubuntu /opt/propcorn-ratelimiter
cd /opt/propcorn-ratelimiter

# Clone repository
git clone https://github.com/jrysztv/ratelimiter.git .
```

#### 2.3 Generate SSH Keys for GitHub Actions
```bash
# On EC2 instance
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_actions_key -N ""

# Add public key to authorized_keys
cat ~/.ssh/github_actions_key.pub >> ~/.ssh/authorized_keys

# Display private key (copy this for GitHub secrets)
cat ~/.ssh/github_actions_key
```

### Step 3: GitHub Repository Configuration

#### 3.1 Set Up Repository Secrets
Go to your GitHub repository → Settings → Secrets and Variables → Actions

Add these secrets:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `EC2_SSH_KEY` | Private key content | Output of `cat ~/.ssh/github_actions_key` |
| `EC2_HOST` | EC2 public IP | AWS EC2 console |
| `EC2_USERNAME` | `ubuntu` | Default Ubuntu username |
| `EC2_APP_PATH` | `/opt/propcorn-ratelimiter` | Application directory |

#### 3.2 Create Production Environment
1. Go to Settings → Environments
2. Create environment named `production`
3. Add protection rules (optional):
   - Required reviewers
   - Deployment branches: `main` only

#### 3.3 Configure Branch Protection
1. Go to Settings → Branches
2. Add rule for `main` branch:
   - ✅ Require pull request before merging
   - ✅ Require status checks to pass
   - ✅ Require branches to be up to date

### Step 4: Test Manual Deployment

#### 4.1 Test on EC2
```bash
# On EC2 instance
cd /opt/propcorn-ratelimiter

# Build and start production containers
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Check if services are running
docker-compose -f docker-compose.prod.yml ps

# Test health endpoint
curl http://localhost:8000/health

# Test API endpoint
curl -H "X-API-Key: test_key" http://localhost:8000/api/weather?city=London
```

#### 4.2 Verify Logs
```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs app

# View Redis logs
docker-compose -f docker-compose.prod.yml logs redis

# Monitor in real-time
docker-compose -f docker-compose.prod.yml logs -f
```

### Step 5: Test CI/CD Pipeline

#### 5.1 Create Test Feature Branch
```bash
# On local machine
git checkout -b test-deployment

# Make a small change
echo "# Test deployment" >> test-deployment.md
git add test-deployment.md
git commit -m "Test: Add deployment test file"
git push origin test-deployment
```

#### 5.2 Create Pull Request
1. Go to GitHub repository
2. Create pull request from `test-deployment` to `main`
3. Verify that CI tests run automatically
4. Check GitHub Actions tab for test results

#### 5.3 Test Deployment
1. Merge the pull request
2. Check GitHub Actions for deployment progress
3. Verify deployment on EC2:
   ```bash
   curl http://<EC2_PUBLIC_IP>:8000/health
   ```

## 🔧 Configuration Options

### Environment Variables

#### Local Development
```bash
# .env.dev (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
LOG_LEVEL=DEBUG
```

#### Production
```bash
# On EC2 instance - .env.prod
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### API Key Configuration

Edit the API keys in your application code:
```python
API_KEYS = {
    "premium_user": {
        "name": "Premium User",
        "rate_limit": "1000/hour"
    },
    "basic_user": {
        "name": "Basic User",
        "rate_limit": "100/hour"
    }
}
```

## 📊 Monitoring and Maintenance

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Redis health
docker exec redis_container redis-cli ping

# Container status
docker-compose -f docker-compose.prod.yml ps
```

### Performance Monitoring
```bash
# System resources
htop
df -h

# Docker stats
docker stats

# Application logs
docker-compose -f docker-compose.prod.yml logs -f app
```

### Maintenance Tasks

#### Regular Updates
```bash
# On EC2 instance
cd /opt/propcorn-ratelimiter
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

#### Cleanup
```bash
# Remove unused Docker resources
docker system prune -a
docker volume prune

# Clear application logs
docker-compose -f docker-compose.prod.yml logs --tail=0 app
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. GitHub Actions SSH Connection Failed
**Error**: `Permission denied (publickey)`

**Solution**:
```bash
# Regenerate SSH keys on EC2
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_actions_key -N ""
cat ~/.ssh/github_actions_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Update EC2_SSH_KEY secret in GitHub with new private key
cat ~/.ssh/github_actions_key
```

#### 2. Docker Permission Denied
**Error**: `Got permission denied while trying to connect to the Docker daemon`

**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker ubuntu
# Logout and login again
exit
```

#### 3. Application Not Responding
**Error**: Health check returns 404 or connection refused

**Solution**:
```bash
# Check if containers are running
docker-compose -f docker-compose.prod.yml ps

# Check application logs
docker-compose -f docker-compose.prod.yml logs app

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Rebuild if necessary
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

#### 4. Rate Limiting Not Working
**Error**: Rate limiting allows too many requests

**Solution**:
```bash
# Check Redis connection
docker exec redis_container redis-cli ping

# Verify API key headers
curl -v -H "X-API-Key: test_key" http://localhost:8000/api/endpoint

# Check application logs for rate limiting messages
docker-compose logs app | grep -i "rate limit"
```

#### 5. Tests Failing in CI
**Error**: Tests pass locally but fail in GitHub Actions

**Solution**:
```bash
# Check if Redis service is properly configured in workflow
# Verify test environment variables
# Check GitHub Actions logs for specific error messages

# Run tests locally with same conditions as CI
docker-compose -f docker-compose.dev.yml up -d redis
poetry run pytest tests/ -v
```

## 🔄 Continuous Improvement

### Performance Optimization
1. **Monitor Response Times**: Use application metrics
2. **Optimize Docker Images**: Multi-stage builds, smaller base images
3. **Database Optimization**: Redis memory management
4. **Caching**: Implement application-level caching

### Security Enhancements
1. **Regular Updates**: Keep dependencies updated
2. **Security Scanning**: Enable GitHub security features
3. **Access Control**: Rotate SSH keys regularly
4. **Network Security**: Configure proper firewall rules

### Scaling Considerations
1. **Load Balancing**: Use AWS Application Load Balancer
2. **Auto Scaling**: Configure auto-scaling groups
3. **Database**: Consider Redis Cluster for high availability
4. **Monitoring**: Implement comprehensive monitoring with CloudWatch

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Redis Documentation](https://redis.io/documentation)

## 🎉 Success Checklist

After completing this setup, you should have:

- [ ] ✅ Local development environment running
- [ ] ✅ Tests passing with visualization results
- [ ] ✅ EC2 instance configured and accessible
- [ ] ✅ GitHub repository with proper secrets
- [ ] ✅ CI/CD pipeline running successfully
- [ ] ✅ Production application deployed and healthy
- [ ] ✅ Automatic deployment on main branch push
- [ ] ✅ Monitoring and logging configured

**Congratulations! 🎊 Your rate limiter project is now production-ready with full CI/CD automation!** 