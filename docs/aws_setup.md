# AWS Setup Guide for PROPCORN-RATELIMITER

This guide covers the setup required for deploying the application to AWS EC2 using GitHub Actions CI/CD.

## EC2 Instance Setup

1. **Launch an EC2 instance**:
   - Amazon Linux 2 or Ubuntu Server recommended
   - t2.micro (free tier) or larger as needed
   - Configure security group to allow:
     - SSH (port 22) from your IP
     - HTTP (port 80) from anywhere
     - HTTPS (port 443) from anywhere
     - Application port (8000) from anywhere or behind a load balancer

2. **Install Docker and Docker Compose**:
   ```bash
   # Update system
   sudo yum update -y  # Amazon Linux
   # or
   sudo apt-get update  # Ubuntu

   # Install Docker
   sudo amazon-linux-extras install docker  # Amazon Linux
   # or
   sudo apt-get install docker.io  # Ubuntu

   # Start Docker service
   sudo service docker start
   sudo usermod -a -G docker ec2-user  # Amazon Linux
   # or
   sudo usermod -a -G docker ubuntu  # Ubuntu

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Set up Git credentials**:
   ```bash
   # Configure Git
   git config --global user.name "Your Name"
   git config --global user.email "your-email@example.com"
   
   # Set up credential helper (optional)
   git config --global credential.helper store
   ```

4. **Clone repository**:
   ```bash
   mkdir -p /home/ec2-user/apps  # Amazon Linux
   # or
   mkdir -p /home/ubuntu/apps  # Ubuntu
   
   cd /home/ec2-user/apps  # Amazon Linux
   # or
   cd /home/ubuntu/apps  # Ubuntu
   
   git clone https://github.com/yourusername/PROPCORN-RATELIMITER.git
   cd PROPCORN-RATELIMITER
   ```

## GitHub Secrets Configuration

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

1. **AWS Credentials**:
   - `AWS_ACCESS_KEY_ID`: Your AWS Access Key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Key
   - `AWS_REGION`: The AWS region (e.g., `us-east-1`)

2. **EC2 Connection Information**:
   - `EC2_HOST`: Your EC2 instance public DNS or IP
   - `EC2_USERNAME`: The username for SSH connection (e.g., `ec2-user` or `ubuntu`)
   - `EC2_APP_PATH`: The path to your application (e.g., `/home/ec2-user/apps/PROPCORN-RATELIMITER`)
   - `EC2_SSH_KEY`: Your private SSH key for connecting to the EC2 instance

## Environment Variables

On your EC2 instance, create a `.env` file in your application directory with production environment variables:

```bash
cd /home/ec2-user/apps/PROPCORN-RATELIMITER  # Amazon Linux
# or
cd /home/ubuntu/apps/PROPCORN-RATELIMITER  # Ubuntu

cat > .env << EOF
ENVIRONMENT=production
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
# Add other environment variables here
EOF
```

## First-time Deployment

Manually deploy the application for the first time:

```bash
cd /home/ec2-user/apps/PROPCORN-RATELIMITER  # Amazon Linux
# or
cd /home/ubuntu/apps/PROPCORN-RATELIMITER  # Ubuntu

docker-compose -f docker-compose.prod.yml up -d
```

## Handling Redis Data

For production, you may want to set up Redis persistence to prevent data loss during restarts:

1. **Configure Redis persistence**:
   - The Docker Compose file already includes `--appendonly yes`
   - Redis data is stored in a volume (`redis_data`)

2. **Backup strategy (optional)**:
   ```bash
   # Create a backup script
   cat > /home/ec2-user/backup-redis.sh << EOF
   #!/bin/bash
   TIMESTAMP=\$(date +%Y%m%d%H%M%S)
   BACKUP_DIR=/home/ec2-user/backups
   mkdir -p \$BACKUP_DIR
   docker exec propcorn-ratelimiter-redis-1 redis-cli SAVE
   docker cp propcorn-ratelimiter-redis-1:/data/dump.rdb \$BACKUP_DIR/redis-\$TIMESTAMP.rdb
   # Add AWS S3 upload command if needed
   EOF
   
   chmod +x /home/ec2-user/backup-redis.sh
   
   # Add to crontab to run daily
   (crontab -l 2>/dev/null; echo "0 0 * * * /home/ec2-user/backup-redis.sh") | crontab -
   ```

## Troubleshooting

- **Check container logs**:
  ```bash
  docker-compose -f docker-compose.prod.yml logs -f
  ```

- **Verify Redis connection**:
  ```bash
  docker exec -it propcorn-ratelimiter-redis-1 redis-cli ping
  ```

- **Restart containers**:
  ```bash
  docker-compose -f docker-compose.prod.yml restart
  ``` 