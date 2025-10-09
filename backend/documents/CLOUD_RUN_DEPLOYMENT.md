# 🚀 Google Cloud Run Deployment Guide

## Overview
This guide helps you deploy the Galaxy of Knowledge backend to Google Cloud Run. The Docker container includes:
- **FastAPI** server (port 8080 - main entry point)
- **MCP Server** (port 8081 - internal)
- **ADK Agent** (port 8082 - internal)

## Prerequisites

### 1. Install Required Tools
- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Git

### 2. Prepare Your Environment Files

#### `.env` file
Make sure your `.env` file contains all necessary environment variables:
```env
# Database Configuration
DB_HOST=your-cloud-sql-instance
DB_NAME=galaxy_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_PORT=5432

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=/app/service_account.json
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1

# API Keys (if needed)
OPENAI_API_KEY=your-openai-key

# Server Configuration
PORT=8080
MCP_PORT=8081
ADK_PORT=8082
```

#### `service_account.json`
Ensure your service account JSON file is in the backend directory with appropriate permissions:
- Cloud SQL Client
- Vertex AI User
- Secret Manager Secret Accessor

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

1. **Set your GCP Project ID**:
```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_REGION="us-central1"
export SERVICE_ACCOUNT_EMAIL="your-service-account@your-project.iam.gserviceaccount.com"
```

2. **Make the script executable**:
```bash
chmod +x deploy-cloud-run.sh
```

3. **Run the deployment script**:
```bash
./deploy-cloud-run.sh
```

The script will:
- ✅ Enable required GCP APIs
- ✅ Build the Docker image using Cloud Build
- ✅ Create secrets in Secret Manager
- ✅ Deploy to Cloud Run
- ✅ Test the deployment

### Method 2: Manual Deployment

#### Step 1: Authenticate with GCP
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

#### Step 2: Enable Required APIs
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

#### Step 3: Build Docker Image
```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/galaxy-backend

# OR build locally and push
docker build -t gcr.io/YOUR_PROJECT_ID/galaxy-backend .
docker push gcr.io/YOUR_PROJECT_ID/galaxy-backend
```

#### Step 4: Create Secrets in Secret Manager
```bash
# Create .env secret
gcloud secrets create galaxy-env --data-file=.env

# Create service account secret
gcloud secrets create galaxy-service-account --data-file=service_account.json

# Grant access to the service account
gcloud secrets add-iam-policy-binding galaxy-env \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding galaxy-service-account \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

#### Step 5: Deploy to Cloud Run
```bash
gcloud run deploy galaxy-of-knowledge-backend \
    --image gcr.io/YOUR_PROJECT_ID/galaxy-backend \
    --platform managed \
    --region us-central1 \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 80 \
    --max-instances 10 \
    --min-instances 1 \
    --allow-unauthenticated \
    --set-env-vars "PORT=8080,MCP_PORT=8081,ADK_PORT=8082" \
    --set-secrets ".env=galaxy-env:latest,service_account.json=galaxy-service-account:latest"
```

## Configuration Options

### Resource Allocation
Adjust based on your needs:
- **Memory**: `--memory 2Gi` (1Gi, 2Gi, 4Gi, 8Gi)
- **CPU**: `--cpu 2` (1, 2, 4, 8)
- **Timeout**: `--timeout 300` (max 3600 seconds)

### Scaling
- **Min Instances**: `--min-instances 1` (Keep at least 1 warm)
- **Max Instances**: `--max-instances 10` (Auto-scale up to 10)
- **Concurrency**: `--concurrency 80` (Requests per container)

### Networking
If using Cloud SQL:
```bash
--add-cloudsql-instances PROJECT:REGION:INSTANCE_NAME
```

## Connecting to Cloud SQL

### Option 1: Cloud SQL Proxy (Recommended)
Update your `.env`:
```env
DB_HOST=/cloudsql/PROJECT:REGION:INSTANCE_NAME
```

Add to Cloud Run deployment:
```bash
--add-cloudsql-instances PROJECT:REGION:INSTANCE_NAME
```

### Option 2: Private IP
Requires VPC connector:
```bash
--vpc-connector YOUR_CONNECTOR_NAME
```

## Monitoring & Logging

### View Logs
```bash
# Stream logs
gcloud run logs tail galaxy-of-knowledge-backend --region us-central1

# Read recent logs
gcloud run logs read galaxy-of-knowledge-backend --region us-central1 --limit 50
```

### Check Service Status
```bash
gcloud run services describe galaxy-of-knowledge-backend --region us-central1
```

### View Metrics in Console
https://console.cloud.google.com/run

## Testing Your Deployment

### Health Check
```bash
curl https://YOUR_SERVICE_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "fastapi": "running",
    "mcp_server": "running",
    "adk_agent": "running"
  }
}
```

### API Documentation
Visit: `https://YOUR_SERVICE_URL/docs`

### Test Endpoints
```bash
# Test papers endpoint
curl https://YOUR_SERVICE_URL/api/v1/papers

# Test MCP Server (internal)
curl https://YOUR_SERVICE_URL:8081/sse
```

## Troubleshooting

### Container Fails to Start
1. Check logs:
```bash
gcloud run logs read galaxy-of-knowledge-backend --region us-central1 --limit 100
```

2. Common issues:
   - Missing environment variables
   - Invalid service account credentials
   - Database connection failure

### Port Binding Issues
Cloud Run expects your app on `PORT` env variable (default 8080). Make sure:
- FastAPI listens on `0.0.0.0:${PORT}`
- Internal services use different ports (8081, 8082)

### Memory/CPU Issues
Increase resources:
```bash
gcloud run services update galaxy-of-knowledge-backend \
    --memory 4Gi \
    --cpu 4 \
    --region us-central1
```

### Secret Access Issues
Verify service account permissions:
```bash
gcloud secrets get-iam-policy galaxy-env
gcloud secrets get-iam-policy galaxy-service-account
```

## Cost Optimization

### Tips to Reduce Costs:
1. **Use min-instances 0** for low traffic (cold starts may occur)
2. **Set appropriate max-instances** to prevent runaway costs
3. **Optimize memory/CPU** - start small and scale up
4. **Use request-based billing** - only pay for actual usage

### Estimated Costs:
- **Compute**: ~$0.065 per vCPU-hour, ~$0.0065 per GB-hour
- **Requests**: First 2M requests/month free, then $0.40 per million
- **Networking**: Egress charges may apply

## Security Best Practices

1. **Use Secret Manager** for sensitive data (✅ Implemented)
2. **Enable authentication** if not public:
   ```bash
   --no-allow-unauthenticated
   ```
3. **Use service accounts** with minimal permissions
4. **Enable VPC** for internal services
5. **Regular security updates** - rebuild and redeploy regularly

## CI/CD Integration

### GitHub Actions Example
Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v0
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
      
      - name: Build and Deploy
        run: |
          cd backend
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/galaxy-backend
          gcloud run deploy galaxy-of-knowledge-backend --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/galaxy-backend
```

## Support

For issues:
1. Check logs in Cloud Console
2. Review [Cloud Run documentation](https://cloud.google.com/run/docs)
3. Check service health endpoint
4. Review container logs: `/tmp/*.log`

## Next Steps

After deployment:
1. ✅ Test all API endpoints
2. ✅ Configure custom domain (optional)
3. ✅ Set up monitoring/alerts
4. ✅ Configure backups
5. ✅ Update frontend to use new backend URL
