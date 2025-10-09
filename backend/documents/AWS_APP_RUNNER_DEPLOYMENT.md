# AWS App Runner Deployment Guide

Complete guide to deploy Galaxy of Knowledge backend to AWS App Runner.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Configure AWS CLI](#configure-aws-cli)
4. [Setup Database (RDS PostgreSQL)](#setup-database)
5. [Configure Secrets Manager](#configure-secrets-manager)
6. [Build and Push Docker Image](#build-docker-image)
7. [Deploy to App Runner](#deploy-app-runner)
8. [Configure Custom Domain (Optional)](#custom-domain)
9. [Update Frontend](#update-frontend)
10. [Monitoring and Logs](#monitoring)
11. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### Required Tools
```powershell
# Check if AWS CLI is installed
aws --version  # Should show version 2.x

# If not installed, download from:
# https://aws.amazon.com/cli/

# Check Docker
docker --version

# Check Git
git --version
```

### AWS Account Requirements
- Active AWS account
- Credit card on file (for billing)
- IAM user with appropriate permissions

### Cost Estimate
- **App Runner**: $0.007/vCPU-hour + $0.0008/GB-hour (~$25-50/month)
- **RDS PostgreSQL**: $15-100/month (depends on instance size)
- **Secrets Manager**: $0.40/secret/month
- **ECR Storage**: $0.10/GB/month
- **Total**: ~$50-200/month

---

## 2. AWS Account Setup

### Step 1: Create IAM User

1. Go to AWS Console → IAM → Users → Create User
2. Username: `apprunner-deploy`
3. Enable "Programmatic access"
4. Attach policies:
   - `AWSAppRunnerFullAccess`
   - `AmazonEC2ContainerRegistryFullAccess`
   - `AmazonRDSFullAccess`
   - `SecretsManagerReadWrite`
   - `IAMFullAccess` (for creating service roles)

5. Save the **Access Key ID** and **Secret Access Key**

### Step 2: Create App Runner Service Role

```powershell
# Create trust policy file
$trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@

$trustPolicy | Out-File -Encoding utf8 trust-policy.json

# Create the role
aws iam create-role `
  --role-name AppRunnerECRAccessRole `
  --assume-role-policy-document file://trust-policy.json

# Attach ECR policy
aws iam attach-role-policy `
  --role-name AppRunnerECRAccessRole `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

---

## 3. Configure AWS CLI

### Set AWS Credentials

```powershell
# Configure AWS CLI
aws configure

# Enter your credentials:
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity

# Set environment variable for region
$env:AWS_REGION = "us-east-1"
```

### Get Your AWS Account ID

```powershell
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
Write-Host "Your AWS Account ID: $AWS_ACCOUNT_ID"
```

---

## 4. Setup Database (RDS PostgreSQL)

### Option A: RDS PostgreSQL (Recommended for Production)

```powershell
# Create RDS PostgreSQL instance
aws rds create-db-instance `
  --db-instance-identifier galaxy-postgres `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --engine-version 15.4 `
  --master-username postgres `
  --master-user-password "YourSecurePassword123!" `
  --allocated-storage 20 `
  --storage-type gp3 `
  --publicly-accessible `
  --backup-retention-period 7 `
  --tags Key=Project,Value=GalaxyOfKnowledge

# Wait for database to be available (takes ~10 minutes)
aws rds wait db-instance-available --db-instance-identifier galaxy-postgres

# Get database endpoint
$DB_ENDPOINT = (aws rds describe-db-instances `
  --db-instance-identifier galaxy-postgres `
  --query 'DBInstances[0].Endpoint.Address' `
  --output text)

Write-Host "Database Endpoint: $DB_ENDPOINT"

# Security Group: Allow App Runner to connect
# Get the security group ID
$SG_ID = (aws rds describe-db-instances `
  --db-instance-identifier galaxy-postgres `
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' `
  --output text)

# Allow all inbound PostgreSQL traffic (for development)
# For production, restrict to App Runner VPC
aws ec2 authorize-security-group-ingress `
  --group-id $SG_ID `
  --protocol tcp `
  --port 5432 `
  --cidr 0.0.0.0/0
```

### Option B: Use Existing PostgreSQL

If you have an existing PostgreSQL database, just note the connection string:

```
postgresql://username:password@host:5432/database
```

### Initialize Database

```powershell
# Update your .env file with RDS endpoint
# DATABASE_URL=postgresql://postgres:YourSecurePassword123!@galaxy-postgres.xxxxxx.us-east-1.rds.amazonaws.com:5432/galaxy

# Run database initialization (from local machine)
cd d:\Github Repos\Galaxy-of-Knowledge\backend
python database/load_projects.py
```

---

## 5. Configure Secrets Manager

### Create Secrets

```powershell
# Create .env secret
aws secretsmanager create-secret `
  --name galaxy-backend-env `
  --description "Environment variables for Galaxy Backend" `
  --secret-string (Get-Content .env -Raw)

# Create service account JSON secret
aws secretsmanager create-secret `
  --name galaxy-service-account `
  --description "Google Cloud service account for Vertex AI" `
  --secret-string (Get-Content service_account.json -Raw)

# Verify secrets created
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `galaxy`)].Name'
```

### Update .env for AWS

```powershell
# Add AWS-specific variables to your .env file
@"
# Database
DATABASE_URL=postgresql://postgres:YourSecurePassword123!@$DB_ENDPOINT:5432/galaxy

# Vertex AI (keep existing)
GOOGLE_APPLICATION_CREDENTIALS=/app/service_account.json

# AWS Secrets
AWS_REGION=us-east-1

# CORS
FRONTEND_URL=https://galaxy-of-knowledge-eta.vercel.app
"@ | Out-File -Append .env
```

---

## 6. Build and Push Docker Image

### Create ECR Repository

```powershell
# Create repository
aws ecr create-repository `
  --repository-name galaxy-backend `
  --region $env:AWS_REGION

# Get repository URI
$ECR_REPO = (aws ecr describe-repositories `
  --repository-names galaxy-backend `
  --query 'repositories[0].repositoryUri' `
  --output text)

Write-Host "ECR Repository: $ECR_REPO"
```

### Build and Push Docker Image

```powershell
# Login to ECR
aws ecr get-login-password --region $env:AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

# Build Docker image
cd d:\Github Repos\Galaxy-of-Knowledge\backend
docker build -t galaxy-backend:latest .

# Tag image
docker tag galaxy-backend:latest ${ECR_REPO}:latest

# Push to ECR
docker push ${ECR_REPO}:latest

Write-Host "✅ Image pushed successfully to ECR"
```

---

## 7. Deploy to App Runner

### Create App Runner Configuration File

Create `apprunner.yaml` in the backend directory:

```yaml
version: 1.0
runtime: python311
build:
  commands:
    build:
      - echo "Using pre-built Docker image"
run:
  runtime-version: 3.11
  command: bash -c "uvicorn main:app --host 0.0.0.0 --port 8080 & python -m MCP_Server.sse_server & adk api_server --port 8082 --allow-origins=$FRONTEND_URL & wait"
  network:
    port: 8080
    env: AWS_VPC_PUBLIC_SUBNETS
  env:
    - name: PORT
      value: "8080"
```

### Deploy with AWS CLI

```powershell
# Get the IAM role ARN
$ROLE_ARN = (aws iam get-role `
  --role-name AppRunnerECRAccessRole `
  --query 'Role.Arn' `
  --output text)

# Create App Runner service
aws apprunner create-service `
  --service-name galaxy-backend `
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$ECR_REPO':latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8080",
        "RuntimeEnvironmentVariables": {
          "FRONTEND_URL": "https://galaxy-of-knowledge-eta.vercel.app"
        }
      }
    },
    "AutoDeploymentsEnabled": true,
    "AuthenticationConfiguration": {
      "AccessRoleArn": "'$ROLE_ARN'"
    }
  }' `
  --instance-configuration '{
    "Cpu": "1024",
    "Memory": "2048"
  }' `
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' `
  --region $env:AWS_REGION

# Wait for service to be running (takes ~5 minutes)
Write-Host "⏳ Waiting for App Runner service to be ready..."
aws apprunner wait service-running --service-arn (aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`galaxy-backend`].ServiceArn' --output text)

# Get service URL
$SERVICE_URL = (aws apprunner describe-service `
  --service-arn (aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`galaxy-backend`].ServiceArn' --output text) `
  --query 'Service.ServiceUrl' `
  --output text)

Write-Host "✅ App Runner service deployed!"
Write-Host "🌐 Service URL: https://$SERVICE_URL"
```

### Configure Environment Variables via Secrets

```powershell
# Update App Runner service to use Secrets Manager
aws apprunner update-service `
  --service-arn (aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`galaxy-backend`].ServiceArn' --output text) `
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$ECR_REPO':latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8080",
        "RuntimeEnvironmentSecrets": {
          "DATABASE_URL": "arn:aws:secretsmanager:'$env:AWS_REGION':'$AWS_ACCOUNT_ID':secret:galaxy-backend-env",
          "GOOGLE_APPLICATION_CREDENTIALS_JSON": "arn:aws:secretsmanager:'$env:AWS_REGION':'$AWS_ACCOUNT_ID':secret:galaxy-service-account"
        }
      }
    }
  }'
```

---

## 8. Configure Custom Domain (Optional)

### Add Custom Domain

```powershell
# Associate custom domain
aws apprunner associate-custom-domain `
  --service-arn (aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`galaxy-backend`].ServiceArn' --output text) `
  --domain-name api.yourdomain.com

# Get DNS records to configure
aws apprunner describe-custom-domains `
  --service-arn (aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`galaxy-backend`].ServiceArn' --output text)

# Add the CNAME records to your DNS provider
# Wait for DNS propagation (~5-30 minutes)
```

---

## 9. Update Frontend

### Update Vercel Environment Variables

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables

2. Add/Update:
   ```
   VITE_API_URL=https://your-service-url.awsapprunner.com
   VITE_ADK_URL=https://your-service-url.awsapprunner.com
   ```

3. Redeploy frontend:
   ```powershell
   cd d:\Github Repos\Galaxy-of-Knowledge\frontend
   git add .
   git commit -m "Update API URLs for AWS App Runner"
   git push
   ```

### Test CORS

```powershell
# Test from your frontend domain
curl -H "Origin: https://galaxy-of-knowledge-eta.vercel.app" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: Content-Type" `
  -X OPTIONS `
  https://$SERVICE_URL/api/v1/papers/

# Should return CORS headers
```

---

## 10. Monitoring and Logs

### View Logs

```powershell
# Get service ARN
$SERVICE_ARN = (aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`galaxy-backend`].ServiceArn' --output text)

# View application logs (in CloudWatch)
# Get log group name
$LOG_GROUP = "/aws/apprunner/galaxy-backend"

# View recent logs
aws logs tail $LOG_GROUP --follow
```

### Check Service Status

```powershell
# Get service status
aws apprunner describe-service `
  --service-arn $SERVICE_ARN `
  --query 'Service.Status' `
  --output text

# Get service metrics
aws cloudwatch get-metric-statistics `
  --namespace AWS/AppRunner `
  --metric-name RequestCount `
  --dimensions Name=ServiceName,Value=galaxy-backend `
  --start-time (Get-Date).AddHours(-1) `
  --end-time (Get-Date) `
  --period 3600 `
  --statistics Sum
```

### Set Up Alarms

```powershell
# Create alarm for high error rate
aws cloudwatch put-metric-alarm `
  --alarm-name galaxy-backend-high-errors `
  --alarm-description "Alert when error rate is high" `
  --metric-name 5xxStatusResponses `
  --namespace AWS/AppRunner `
  --statistic Sum `
  --period 300 `
  --evaluation-periods 1 `
  --threshold 10 `
  --comparison-operator GreaterThanThreshold `
  --dimensions Name=ServiceName,Value=galaxy-backend
```

---

## 11. Troubleshooting

### Common Issues

#### 1. Service Won't Start

```powershell
# Check logs
aws logs tail /aws/apprunner/galaxy-backend --follow

# Check service events
aws apprunner describe-service `
  --service-arn $SERVICE_ARN `
  --query 'Service.ServiceEvents[0:5]'
```

**Solutions:**
- Verify environment variables are set correctly
- Check database connection string
- Ensure secrets are accessible
- Verify Docker image runs locally

#### 2. Database Connection Failed

```bash
Error: could not connect to server
```

**Solutions:**
```powershell
# Check RDS is running
aws rds describe-db-instances --db-instance-identifier galaxy-postgres

# Verify security group allows connections
aws ec2 describe-security-groups --group-ids $SG_ID

# Test connection from local machine
psql postgresql://postgres:password@$DB_ENDPOINT:5432/galaxy
```

#### 3. CORS Errors

```
Access to fetch at 'https://...' from origin 'https://galaxy-of-knowledge-eta.vercel.app' has been blocked by CORS policy
```

**Solutions:**
- Verify CORS configuration in `main.py` includes your Vercel domain
- Check ADK Agent has `--allow-origins` flag
- Restart App Runner service after changes

#### 4. 503 Service Unavailable

**Solutions:**
```powershell
# Check health check status
aws apprunner describe-service `
  --service-arn $SERVICE_ARN `
  --query 'Service.HealthCheckConfiguration'

# Verify /health endpoint works
curl https://$SERVICE_URL/health
```

#### 5. Secrets Not Loading

**Solutions:**
```powershell
# Verify secrets exist
aws secretsmanager list-secrets

# Check IAM permissions for App Runner role
aws iam list-attached-role-policies --role-name AppRunnerECRAccessRole

# Add Secrets Manager permission if missing
aws iam attach-role-policy `
  --role-name AppRunnerECRAccessRole `
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

---

## Quick Reference Commands

```powershell
# Deploy new version
docker build -t galaxy-backend:latest .
docker tag galaxy-backend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
aws apprunner start-deployment --service-arn $SERVICE_ARN

# View logs
aws logs tail /aws/apprunner/galaxy-backend --follow

# Get service URL
aws apprunner describe-service --service-arn $SERVICE_ARN --query 'Service.ServiceUrl' --output text

# Pause service (stop billing)
aws apprunner pause-service --service-arn $SERVICE_ARN

# Resume service
aws apprunner resume-service --service-arn $SERVICE_ARN

# Delete service
aws apprunner delete-service --service-arn $SERVICE_ARN
```

---

## Next Steps

1. ✅ Deploy backend to App Runner
2. ✅ Verify health check: `https://your-service-url/health`
3. ✅ Test API: `https://your-service-url/docs`
4. ✅ Update Vercel environment variables
5. ✅ Test frontend connectivity
6. ✅ Set up monitoring and alarms
7. ✅ Configure custom domain (optional)

---

## Cost Optimization Tips

1. **Use Auto-scaling**: App Runner scales to zero when not in use
2. **Right-size Resources**: Start with 1024 CPU / 2048 Memory, adjust based on usage
3. **Pause Non-Production**: Pause dev/staging environments when not in use
4. **Use Reserved Instances**: For RDS, use reserved instances for 30-40% savings
5. **Monitor Costs**: Set up billing alerts in AWS Budgets

---

## Support

- **AWS App Runner Docs**: https://docs.aws.amazon.com/apprunner/
- **AWS Free Tier**: First 2 months of App Runner usage may qualify for free tier
- **Cost Calculator**: https://calculator.aws/

