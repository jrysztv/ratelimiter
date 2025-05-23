# GitHub Repository Setup Guide

This guide explains how to set up your GitHub repository with the necessary secrets and configurations for automated CI/CD deployment.

## Prerequisites

- GitHub account
- EC2 instance set up (see [EC2_SETUP.md](./EC2_SETUP.md))
- SSH keys generated on EC2 instance

## Step 1: Repository Setup

### 1.1 Create Repository Environment
1. Go to your repository: `https://github.com/jrysztv/ratelimiter`
2. Navigate to **Settings** → **Environments**
3. Click **New environment**
4. Name it `production`
5. Optionally, add protection rules:
   - Required reviewers (if working in a team)
   - Deployment branches (limit to `main` branch only)

## Step 2: Configure Repository Secrets

Navigate to **Settings** → **Secrets and variables** → **Actions**

### 2.1 Required Secrets

Add the following secrets by clicking **New repository secret**:

| Secret Name | Description | How to Get Value |
|-------------|-------------|------------------|
| `EC2_SSH_KEY_B64` | Base64-encoded private SSH key | `base64 -w 0 ~/.ssh/your-key.pem` |
| `EC2_HOST` | EC2 instance public IP or domain | From AWS EC2 console |
| `EC2_USERNAME` | EC2 username | `ubuntu` (for Ubuntu instances) |
| `EC2_APP_PATH` | Application directory on EC2 | `/opt/ratelimiter` |
| `AWS_ACCESS_KEY_ID` | AWS Access Key for dynamic security | From IAM user creation |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Key for dynamic security | From IAM user creation |
| `AWS_REGION` | AWS region where EC2 is located | e.g., `eu-west-1`, `us-east-1` |
| `EC2_SECURITY_GROUP_ID` | Security group ID for dynamic access | From EC2 console, format: `sg-...` |

### 2.2 Optional Secrets (for enhanced features)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `CODECOV_TOKEN` | Codecov upload token | Get from codecov.io |
| `SLACK_WEBHOOK` | Slack webhook for notifications | Slack webhook URL |
| `DOCKER_USERNAME` | Docker Hub username | For pushing images |
| `DOCKER_PASSWORD` | Docker Hub password/token | For pushing images |

## Step 3: Detailed Secret Setup Instructions

### 3.1 Getting EC2_SSH_KEY_B64

**NEW METHOD**: Use base64 encoding for reliability:

```bash
# On your local machine (Git Bash), encode your SSH key
base64 -w 0 ~/.ssh/your-key.pem
```

Copy the entire base64 string output and paste it as the value for `EC2_SSH_KEY_B64`.

**Why base64?**: Prevents line break and encoding issues that occur when copying SSH keys directly.

### 3.2 Setting Up AWS Credentials

**Create IAM User:**
1. **AWS IAM Console** → **Users** → **Create User**
2. **Name**: `github-actions-deploy`
3. **Permissions**: `AmazonEC2FullAccess`
4. **Create access key** → **Application running outside AWS**
5. **Copy**: Access Key ID and Secret Access Key

**Get Security Group ID:**
1. **AWS EC2 Console** → **Your Instance** → **Security** tab
2. **Copy Security Group ID** (format: `sg-1234567890abcdef0`)

### 3.3 Getting EC2_HOST

From AWS EC2 Console:
1. Select your instance
2. Copy the **Public IPv4 address** (e.g., `3.252.200.91`)
3. Use this as the value for `EC2_HOST`

### 3.4 Setting EC2_USERNAME and EC2_APP_PATH

- **EC2_USERNAME**: `ubuntu` (for Ubuntu instances)
- **EC2_APP_PATH**: `/opt/ratelimiter`

## Step 4: Environment Variables (Optional)

If your application needs additional environment variables, you can add them in two ways:

### 4.1 Repository Variables (Non-sensitive)
Go to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab

Example variables:
- `ENVIRONMENT`: `production`
- `LOG_LEVEL`: `INFO`
- `APP_NAME`: `propcorn-ratelimiter`

### 4.2 Environment Secrets (Sensitive)
Add sensitive environment variables as secrets:
- `DATABASE_PASSWORD`
- `API_SECRET_KEY`
- `REDIS_PASSWORD` (if Redis auth is enabled)

## Step 5: Branch Protection Rules (Recommended)

### 5.1 Protect Main Branch
1. Go to **Settings** → **Branches**
2. Click **Add rule**
3. Branch name pattern: `main`
4. Enable:
   - ✅ **Require a pull request before merging**
   - ✅ **Require status checks to pass before merging**
   - ✅ **Require branches to be up to date before merging**
   - ✅ **Require conversation resolution before merging**
   - ✅ **Include administrators**

### 5.2 Required Status Checks
Select the following required checks:
- `test` (the test job from GitHub Actions)
- `build` (the build job from GitHub Actions)

## Step 6: Webhook Configuration (Optional)

For Slack notifications or other webhooks:

### 6.1 Slack Integration
1. Create a Slack app and webhook
2. Add `SLACK_WEBHOOK` secret
3. Modify `.github/workflows/main.yml` to include Slack notifications

## Step 7: Testing the Setup

### 7.1 Manual Test
1. Make a small change to the repository
2. Commit and push to a feature branch
3. Create a pull request
4. Verify that tests run automatically

### 7.2 Deployment Test
1. Merge the PR to main
2. Check the Actions tab for deployment progress
3. Verify deployment on your EC2 instance

## Step 8: Repository Settings

### 8.1 General Settings
- **Description**: "Advanced rate limiting strategies with FastAPI and Redis"
- **Website**: Your EC2 instance URL (e.g., `http://54.123.45.67:8000`)
- **Topics**: `fastapi`, `rate-limiting`, `redis`, `python`, `docker`, `ci-cd`

### 8.2 Code Security and Analysis
Enable:
- ✅ **Dependency graph**
- ✅ **Dependabot alerts**
- ✅ **Dependabot security updates**
- ✅ **Code scanning** (GitHub CodeQL)

## Step 9: Monitoring and Notifications

### 9.1 Email Notifications
1. Go to **Settings** → **Notifications**
2. Configure email preferences for:
   - Failed Actions
   - Security alerts
   - Dependabot alerts

### 9.2 Status Badge (Optional)
Add a status badge to your README:

```markdown
[![CI/CD Pipeline](https://github.com/jrysztv/ratelimiter/actions/workflows/main.yml/badge.svg)](https://github.com/jrysztv/ratelimiter/actions/workflows/main.yml)
```

## Common Issues and Solutions

### Issue 1: SSH Connection Failed
**Error**: `Permission denied (publickey)`

**Solution**: 
- Verify `EC2_SSH_KEY` contains the complete private key
- Check that the public key is in `~/.ssh/authorized_keys` on EC2
- Ensure key permissions are correct (`chmod 600`)

### Issue 2: Deployment Directory Not Found
**Error**: `No such file or directory: /opt/propcorn-ratelimiter`

**Solution**:
- Verify `EC2_APP_PATH` secret value
- Ensure the directory exists on EC2 instance
- Check that the repository is cloned correctly

### Issue 3: Docker Permission Denied
**Error**: `Got permission denied while trying to connect to the Docker daemon socket`

**Solution**:
- Add ubuntu user to docker group: `sudo usermod -aG docker ubuntu`
- Logout and login to EC2 instance
- Restart the deployment

### Issue 4: Port Already in Use
**Error**: `bind: address already in use`

**Solution**:
- Stop existing containers: `docker-compose -f docker-compose.prod.yml down`
- Check for orphaned processes: `sudo netstat -tulpn | grep :8000`
- Kill processes if needed: `sudo kill -9 <PID>`

## Security Best Practices

1. **Rotate SSH Keys Regularly**: Generate new keys every 3-6 months
2. **Use Environment-Specific Secrets**: Don't use production secrets in development
3. **Limit Secret Access**: Only give team members access to secrets they need
4. **Monitor Secret Usage**: Check Actions logs for any unauthorized access
5. **Use Personal Access Tokens**: For Git operations, use tokens instead of passwords

## Advanced Configuration

### Multi-Environment Setup
For staging and production environments:

1. Create multiple environments in GitHub
2. Use environment-specific secrets
3. Modify workflow to deploy to different environments based on branch

### Auto-scaling Setup
For production with auto-scaling:

1. Use Application Load Balancer
2. Store secrets in AWS Secrets Manager
3. Modify deployment to work with multiple instances

### Monitoring Integration
Add monitoring tools:

1. **DataDog**: Add `DATADOG_API_KEY` secret
2. **New Relic**: Add `NEW_RELIC_LICENSE_KEY` secret
3. **Prometheus**: Configure scraping endpoints 