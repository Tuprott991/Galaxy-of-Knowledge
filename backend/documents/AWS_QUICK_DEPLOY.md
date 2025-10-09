# AWS App Runner - Quick Deploy Guide

Fast deployment reference for Galaxy of Knowledge backend on AWS App Runner.

## Prerequisites

```powershell
# Install AWS CLI v2
# Download from: https://aws.amazon.com/cli/

# Configure credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)

# Verify
aws sts get-caller-identity
docker --version
```

---

## 🚀 One-Command Deploy

```powershell
cd d:\Github Repos\Galaxy-of-Knowledge\backend

# Deploy with your existing database (default)
.\deploy-apprunner.ps1

# Custom options
.\deploy-apprunner.ps1 -Region "us-west-2" -ServiceName "my-backend"

# Create new AWS RDS database (if you want AWS to host it)
.\deploy-apprunner.ps1 -CreateDatabase

# Skip secrets update (already created)
.\deploy-apprunner.ps1 -SkipSecrets
```

**That's it!** The script will:
1. ✅ Create IAM roles
2. ✅ Use your existing database (from .env)
3. ✅ Configure secrets
4. ✅ Build Docker image
5. ✅ Push to ECR
6. ✅ Deploy to App Runner
7. ✅ Run health checks

**Note**: Your existing database in `.env` will be used. No need to create a new AWS RDS database!

---

## Manual Deployment (5 Steps)

### 1. Configure AWS

```powershell
$env:AWS_REGION = "us-east-1"
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
```

### 2. Database Setup

**You already have a database in .env - skip this step!** ✅

<details>
<summary>Optional: Create AWS RDS Database (click to expand)</summary>

Only if you want to use AWS RDS instead of your existing database:

```powershell
aws rds create-db-instance `
  --db-instance-identifier galaxy-postgres `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --master-username postgres `
  --master-user-password "YourSecurePassword123!" `
  --allocated-storage 20 `
  --publicly-accessible

# Wait (~10 minutes)
aws rds wait db-instance-available --db-instance-identifier galaxy-postgres

# Get endpoint
$DB_ENDPOINT = (aws rds describe-db-instances --db-instance-identifier galaxy-postgres --query 'DBInstances[0].Endpoint.Address' --output text)

# Update .env with: DATABASE_URL=postgresql://postgres:YourPassword@$DB_ENDPOINT:5432/galaxy
```
</details>

### 3. Build & Push Image

```powershell
# Create ECR repo
aws ecr create-repository --repository-name galaxy-backend

# Login
aws ecr get-login-password --region $env:AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com

# Build & push
docker build -t galaxy-backend:latest .
docker tag galaxy-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com/galaxy-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com/galaxy-backend:latest
```

### 4. Create App Runner Service

```powershell
# Get IAM role ARN (create if needed - see full guide)
$ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/AppRunnerECRAccessRole"

# Deploy
aws apprunner create-service `
  --service-name galaxy-backend `
  --source-configuration "{
    \"ImageRepository\": {
      \"ImageIdentifier\": \"${AWS_ACCOUNT_ID}.dkr.ecr.${env:AWS_REGION}.amazonaws.com/galaxy-backend:latest\",
      \"ImageRepositoryType\": \"ECR\",
      \"ImageConfiguration\": {
        \"Port\": \"8080\"
      }
    },
    \"AutoDeploymentsEnabled\": true,
    \"AuthenticationConfiguration\": {
      \"AccessRoleArn\": \"$ROLE_ARN\"
    }
  }" `
  --instance-configuration "{\"Cpu\": \"1024\", \"Memory\": \"2048\"}" `
  --health-check-configuration "{\"Protocol\": \"HTTP\", \"Path\": \"/health\"}"

# Wait (~5 minutes)
aws apprunner wait service-running --service-arn [YOUR_SERVICE_ARN]
```

### 5. Get Service URL

```powershell
$SERVICE_URL = (aws apprunner describe-service --service-arn [YOUR_SERVICE_ARN] --query 'Service.ServiceUrl' --output text)

Write-Host "Service URL: https://$SERVICE_URL"

# Test
curl https://$SERVICE_URL/health
```

---

## Update Vercel Frontend

1. Go to Vercel Dashboard → Settings → Environment Variables
2. Add:
   ```
   VITE_API_URL=https://YOUR_SERVICE_URL.awsapprunner.com
   VITE_ADK_URL=https://YOUR_SERVICE_URL.awsapprunner.com
   ```
3. Redeploy frontend

---

## Essential Commands

```powershell
# View logs
aws logs tail /aws/apprunner/galaxy-backend --follow

# Redeploy (after code changes)
docker build -t galaxy-backend:latest . && \
docker tag galaxy-backend:latest $ECR_REPO:latest && \
docker push $ECR_REPO:latest && \
aws apprunner start-deployment --service-arn $SERVICE_ARN

# Check status
aws apprunner describe-service --service-arn $SERVICE_ARN --query 'Service.Status'

# Pause service (stop paying)
aws apprunner pause-service --service-arn $SERVICE_ARN

# Resume service
aws apprunner resume-service --service-arn $SERVICE_ARN

# Delete everything
aws apprunner delete-service --service-arn $SERVICE_ARN
aws rds delete-db-instance --db-instance-identifier galaxy-postgres --skip-final-snapshot
aws ecr delete-repository --repository-name galaxy-backend --force
```

---

## Troubleshooting

### Service won't start
```powershell
# Check logs
aws logs tail /aws/apprunner/galaxy-backend --follow

# Check events
aws apprunner describe-service --service-arn $SERVICE_ARN --query 'Service.ServiceEvents[0:5]'
```

### Database connection failed
```powershell
# Verify RDS is running
aws rds describe-db-instances --db-instance-identifier galaxy-postgres --query 'DBInstances[0].DBInstanceStatus'

# Check security group allows port 5432
$SG_ID = (aws rds describe-db-instances --db-instance-identifier galaxy-postgres --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr 0.0.0.0/0
```

### CORS errors
- Verify `main.py` has your Vercel domain in CORS origins
- Check ADK Agent has `--allow-origins` flag in Dockerfile
- Rebuild and redeploy after changes

### Health check failing
```powershell
# Test locally first
docker run -p 8080:8080 galaxy-backend:latest

# In another terminal
curl http://localhost:8080/health
```

---

## Cost Estimate

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| App Runner | 1 vCPU, 2GB RAM | $25-50 |
| Your Database | (external) | $0 |
| ECR | < 5GB storage | $1-2 |
| Secrets Manager | 2 secrets | $1 |
| **Total** | | **~$27-53/month** |

**Free Tier**: First 2 months of App Runner may be free

**Savings Tips**:
- Pause App Runner when not in use
- Use RDS reserved instances (30-40% savings)
- Delete unused ECR images

---

## Comparison: App Runner vs Cloud Run

| Feature | AWS App Runner | GCP Cloud Run |
|---------|---------------|---------------|
| Pricing | $0.007/vCPU-hr | $0.024/vCPU-hr |
| Scale to Zero | ✅ Yes | ✅ Yes |
| Max Memory | 4GB | 32GB |
| Max CPU | 2 vCPU | 8 vCPU |
| Cold Start | 1-2 seconds | 100-500ms |
| Custom Domains | ✅ Free | ✅ Free |
| Setup Time | ~10 minutes | ~10 minutes |

**Winner for Cost**: AWS App Runner (~40% cheaper)
**Winner for Performance**: GCP Cloud Run (faster cold starts)

---

## Next Steps

1. ✅ Deploy with `.\deploy-apprunner.ps1`
2. ✅ Test API at `https://YOUR_URL/docs`
3. ✅ Update Vercel environment variables
4. ✅ Test frontend on https://galaxy-of-knowledge-eta.vercel.app
5. ✅ Set up CloudWatch alarms (optional)
6. ✅ Configure custom domain (optional)

---

## Resources

- **Full Guide**: `AWS_APP_RUNNER_DEPLOYMENT.md`
- **AWS Docs**: https://docs.aws.amazon.com/apprunner/
- **Pricing**: https://aws.amazon.com/apprunner/pricing/
- **Free Tier**: https://aws.amazon.com/free/

