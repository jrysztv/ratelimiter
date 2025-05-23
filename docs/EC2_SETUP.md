# EC2 Setup Guide for Rate Limiter Deployment

This guide will walk you through setting up an EC2 instance to deploy the Propcorn Rate Limiter application.

## Prerequisites

- AWS Account with EC2 access
- Local machine with SSH client
- Basic knowledge of Linux commands

## Step 1: Create EC2 Instance

### 1.1 Launch Instance
1. Go to AWS EC2 Console
2. Click "Launch Instance"
3. **Name**: `propcorn-ratelimiter-prod`
4. **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible)
5. **Instance Type**: t2.micro (for development) or t3.small (for production)
6. **Key Pair**: Create a new key pair named `propcorn-ratelimiter-key` and download the `.pem` file

### 1.2 Configure Security GroupCreate a security group with the following rules:- **SSH (22)**: Your IP address  - **HTTP (80)**: 0.0.0.0/0 (Nginx reverse proxy)- **HTTPS (443)**: 0.0.0.0/0 (for SSL in future)- **Redis (6379)**: Only from within security group (internal only)**Note**: We do NOT expose port 8000 directly - Nginx handles all external traffic

### 1.3 Storage
- **Root Volume**: 20 GB gp3 (minimum)

## Step 2: Connect to EC2 Instance

```bash
# Make key file secure
chmod 400 propcorn-ratelimiter-key.pem

# Connect to instance
ssh -i propcorn-ratelimiter-key.pem ubuntu@<EC2_PUBLIC_IP>
```

## Step 3: Install Required Software

### 3.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Log out and back in for group changes to take effect
exit
```

### 3.3 Install Docker Compose
```bash
# Reconnect after logout
ssh -i propcorn-ratelimiter-key.pem ubuntu@<EC2_PUBLIC_IP>

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 3.4 Install Git
```bash
sudo apt install git -y
```

## Step 4: Setup Application Directory

### 4.1 Clone Repository
```bash
# Create application directory
sudo mkdir -p /opt/propcorn-ratelimiter
sudo chown ubuntu:ubuntu /opt/propcorn-ratelimiter

# Clone repository
cd /opt/propcorn-ratelimiter
git clone https://github.com/jrysztv/ratelimiter.git .

# Verify files
ls -la
```

### 4.2 Create Environment Configuration
```bash
# Create environment file for production
cat > .env.prod << EOF
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF
```

## Step 5: Setup SSH Key for GitHub Actions

### 5.1 Generate SSH Key for Deployment
```bash
# Generate SSH key (on EC2 instance)
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_actions_key -N ""

# Display public key (add this to ~/.ssh/authorized_keys)
cat ~/.ssh/github_actions_key.pub >> ~/.ssh/authorized_keys

# Display private key (copy this to GitHub secrets)
cat ~/.ssh/github_actions_key
```

### 5.2 Set Proper Permissions
```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/github_actions_key
```

## Step 6: Configure GitHub Repository Secrets

Go to your GitHub repository → Settings → Secrets and Variables → Actions

Add the following secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `EC2_SSH_KEY` | Contents of `~/.ssh/github_actions_key` (private key) | SSH private key for deployment |
| `EC2_HOST` | Your EC2 public IP or domain | EC2 instance address |
| `EC2_USERNAME` | `ubuntu` | EC2 username |
| `EC2_APP_PATH` | `/opt/propcorn-ratelimiter` | Application directory path |

## Step 7: Test Manual Deployment

Before setting up automated deployment, test manual deployment:

```bash
cd /opt/propcorn-ratelimiter

# Build and start services with Nginxdocker-compose -f docker-compose.prod-nginx.yml builddocker-compose -f docker-compose.prod-nginx.yml up -d# Check if services are runningdocker-compose -f docker-compose.prod-nginx.yml ps# Test health endpoint (through Nginx on port 80)curl http://localhost/health# Test API endpoint (through Nginx)curl -H "X-API-Key: test_key" http://localhost/api/endpoint# View logs if neededdocker-compose -f docker-compose.prod-nginx.yml logs
```

## Step 8: Firewall Configuration (Optional but Recommended)

```bash
# Install UFW
sudo apt install ufw -y

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow application port
sudo ufw allow 8000

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

## Step 9: Setup Log Rotation (Optional)

```bash
# Create log rotation configuration
sudo cat > /etc/logrotate.d/docker-containers << EOF
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=1M
    missingok
    delaycompress
    copytruncate
}
EOF
```

## Step 10: Setup Monitoring (Optional)

### 10.1 Install htop for process monitoring
```bash
sudo apt install htop -y
```

### 10.2 Create simple health check script
```bash
cat > /opt/propcorn-ratelimiter/healthcheck.sh << 'EOF'
#!/bin/bash
HEALTH_URL="http://localhost:8000/health"
TIMEOUT=10

if curl -f --max-time $TIMEOUT "$HEALTH_URL" > /dev/null 2>&1; then
    echo "$(date): Health check passed"
    exit 0
else
    echo "$(date): Health check failed"
    exit 1
fi
EOF

chmod +x /opt/propcorn-ratelimiter/healthcheck.sh
```

### 10.3 Setup cron job for health monitoring
```bash
# Add to crontab (runs every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/propcorn-ratelimiter/healthcheck.sh >> /var/log/app-health.log 2>&1") | crontab -
```

## Troubleshooting

### Common Issues

1. **Docker permission denied**
   ```bash
   sudo usermod -aG docker ubuntu
   # Then logout and login again
   ```

2. **Port already in use**
   ```bash
   sudo netstat -tulpn | grep :8000
   docker-compose -f docker-compose.prod.yml down
   ```

3. **Git pull authentication**
   ```bash
   # Use HTTPS with personal access token
   git remote set-url origin https://username:token@github.com/jrysztv/ratelimiter.git
   ```

4. **Health check fails**
   ```bash
   # Check application logs
   docker-compose -f docker-compose.prod.yml logs app
   
   # Check Redis logs
   docker-compose -f docker-compose.prod.yml logs redis
   ```

5. **Out of disk space**
   ```bash
   # Clean up Docker
   docker system prune -a
   docker volume prune
   ```

### Useful Commands

```bash
# View running containers
docker ps

# View all containers
docker ps -a

# View container logs
docker logs <container_name>

# Restart application
docker-compose -f docker-compose.prod.yml restart

# Update application
cd /opt/propcorn-ratelimiter
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Monitor resource usage
htop
df -h
```

## Security Best Practices

1. **Regular Updates**: Keep the system updated
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Fail2ban**: Install fail2ban for SSH protection
   ```bash
   sudo apt install fail2ban -y
   sudo systemctl enable fail2ban
   ```

3. **SSH Key Only**: Disable password authentication
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   sudo systemctl restart ssh
   ```

4. **Regular Backups**: Backup important data
   ```bash
   # Backup Redis data
   docker exec redis_container redis-cli BGSAVE
   ```

5. **Monitor Logs**: Regularly check application and system logs
   ```bash
   tail -f /var/log/syslog
   docker-compose -f docker-compose.prod.yml logs -f
   ``` 