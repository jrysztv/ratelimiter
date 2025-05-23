# AWS Setup Guide for PROPCORN-RATELIMITER

This guide covers the complete AWS setup required for deploying the application to AWS EC2 using automated GitHub Actions CI/CD with dynamic security group management.

## Prerequisites

- AWS Account with EC2 access
- Basic familiarity with AWS IAM and EC2

## Phase 1: IAM User Setup for GitHub Actions

### 1.1 Create IAM User

1. **Go to AWS IAM Console** → **Users** → **Create User**
2. **User details**:
   - **User name**: `github-actions-deploy`
   - **Uncheck** "Provide user access to the AWS Management Console"
3. **Permissions**: 
   - **Attach policies directly**
   - **Select**: `AmazonEC2FullAccess`
4. **Review and create user**

### 1.2 Generate Access Keys

1. **Select the created user** → **Security credentials** tab
2. **Create access key** → **Application running outside AWS**
3. **Copy both values**:
   - **Access Key ID** (starts with `AKIA...`)
   - **Secret Access Key** (long random string)
4. **Store these safely** - you'll add them to GitHub secrets

## Phase 2: EC2 Instance Setup

### 2.1 Launch EC2 Instance

1. **Launch an EC2 instance**:
   - **AMI**: Ubuntu Server 22.04 LTS (recommended)
   - **Instance Type**: t2.micro (free tier) or larger as needed
   - **Key Pair**: Create new or use existing `.pem` file
   - **Security Group**: Create new with these rules:

**Inbound Rules:**
```
Type    Port    Source          Description
SSH     22      YOUR-IP/32      Personal access (replace YOUR-IP)
HTTP    80      0.0.0.0/0       Public web access
HTTPS   443     0.0.0.0/0       Public web access (optional)
```

**IMPORTANT**: 
- ✅ **Only add YOUR personal IP** for SSH access
- ❌ **Never use 0.0.0.0/0 for SSH** - GitHub Actions manages this dynamically
- ✅ **HTTP/HTTPS can be open** for public web access

### 2.2 Get Security Group ID

After creating the instance:
1. **AWS EC2 Console** → **Instances** → **Select your instance**
2. **Security** tab → **Security groups** → **Copy the Security Group ID**
3. **Save this ID** - you'll need it for GitHub secrets (format: `sg-1234567890abcdef0`)

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

Add the following secrets to your GitHub repository (Settings → Environments → production):

### EC2 Connection Secrets:
- **`EC2_HOST`**: Your EC2 instance public DNS or IP (e.g., `3.252.200.91`)
- **`EC2_USERNAME`**: The username for SSH connection (`ubuntu` for Ubuntu instances)
- **`EC2_APP_PATH`**: The path to your application (e.g., `/opt/ratelimiter`)
- **`EC2_SSH_KEY_B64`**: Your base64-encoded private SSH key

### AWS Credentials for Dynamic Security Management:
- **`AWS_ACCESS_KEY_ID`**: From the IAM user you created (starts with `AKIA...`)
- **`AWS_SECRET_ACCESS_KEY`**: From the IAM user you created (long random string)
- **`AWS_REGION`**: The AWS region where your EC2 is located (e.g., `eu-west-1`)
- **`EC2_SECURITY_GROUP_ID`**: Your security group ID (e.g., `sg-1234567890abcdef0`)

### Encode SSH Key for GitHub:
```bash
# Run in Git Bash to encode your SSH key
base64 -w 0 ~/.ssh/your-key.pem
# Copy the entire output string to EC2_SSH_KEY_B64 secret
```

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