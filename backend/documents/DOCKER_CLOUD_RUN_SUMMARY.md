# 📦 Docker & Cloud Run Setup - Complete

## What Was Created

### 1. Docker Files
- ✅ **`Dockerfile`** - Main production Dockerfile with multi-stage build
- ✅ **`Dockerfile.supervisor`** - Alternative with Supervisor for better process management
- ✅ **`.dockerignore`** - Excludes unnecessary files from image
- ✅ **`docker-compose.yml`** - Local development with Docker Compose

### 2. Deployment Scripts
- ✅ **`deploy-cloud-run.sh`** - Automated deployment for Linux/Mac
- ✅ **`deploy-cloud-run.ps1`** - Automated deployment for Windows PowerShell

### 3. Documentation
- ✅ **`CLOUD_RUN_DEPLOYMENT.md`** - Comprehensive deployment guide
- ✅ **`DOCKER_QUICKSTART.md`** - Quick reference for Docker commands

## Container Architecture

The Docker container runs **three services simultaneously**:

```
┌─────────────────────────────────────────┐
│         Galaxy Backend Container         │
├─────────────────────────────────────────┤
│                                          │
│  ┌────────────────────────────────┐    │
│  │   FastAPI Server (Port 8080)    │◄───┼─── External Traffic
│  │   - Main API endpoints          │    │
│  │   - Health checks               │    │
│  │   - Documentation               │    │
│  └────────────────────────────────┘    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │   MCP Server (Port 8081)        │◄───┼─── Internal Only
│  │   - SSE transport               │    │
│  │   - Tool integration            │    │
│  │   - Database queries            │    │
│  └────────────────────────────────┘    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │   ADK Agent (Port 8082)         │◄───┼─── Internal Only
│  │   - AI agent runtime            │    │
│  │   - MCP tool integration        │    │
│  └────────────────────────────────┘    │
│                                          │
└─────────────────────────────────────────┘
```

## Features Implemented

### ✅ Multi-Service Container
- All three services (FastAPI, MCP, ADK) run in a single container
- Process management via bash script or Supervisor
- Graceful shutdown handling

### ✅ Cloud Run Optimized
- Listens on `PORT` environment variable (Cloud Run requirement)
- Health check endpoint at `/health`
- Supports Cloud Run's lifecycle (startup/shutdown)
- Proper logging to stdout/stderr

### ✅ Security Best Practices
- `.env` file loaded from Cloud Run secrets
- `service_account.json` loaded from Cloud Run secrets
- No hardcoded credentials in image
- Multi-stage build to reduce image size

### ✅ Environment Configuration
- All ports configurable via environment variables
- Database connection via environment variables
- GCP credentials via mounted service account

## Quick Start Guide

### Option 1: Local Testing with Docker Compose
```powershell
# Navigate to backend directory
cd backend

# Start all services
docker-compose up

# Test
curl http://localhost:8080/health
```

### Option 2: Deploy to Cloud Run (Windows)
```powershell
# Set your GCP project
$env:GCP_PROJECT_ID = "your-project-id"

# Run deployment script
.\deploy-cloud-run.ps1
```

### Option 3: Manual Docker Build & Run
```powershell
# Build image
docker build -t galaxy-backend .

# Run container
docker run -p 8080:8080 -p 8081:8081 -p 8082:8082 `
  --env-file .env `
  -v ${PWD}/service_account.json:/app/service_account.json `
  galaxy-backend
```

## Configuration Files Needed

### 1. `.env` File
Your `.env` file should contain:
```env
# Database Configuration (Cloud SQL or external PostgreSQL)
DB_HOST=your-database-host
DB_NAME=galaxy_db
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_PORT=5432

# Google Cloud Configuration
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/app/service_account.json

# API Keys (if needed)
OPENAI_API_KEY=your-api-key-if-needed

# Server Ports (Cloud Run sets PORT automatically to 8080)
PORT=8080
MCP_PORT=8081
ADK_PORT=8082
```

### 2. `service_account.json`
Your GCP service account JSON with these roles:
- Cloud SQL Client (if using Cloud SQL)
- Vertex AI User
- Secret Manager Secret Accessor
- Cloud Run Invoker (for internal calls)

## Cloud Run Deployment Flow

The deployment script (`deploy-cloud-run.ps1`) does:

1. **Enable APIs**: Activates required GCP services
2. **Build Image**: Uses Cloud Build to create Docker image
3. **Create Secrets**: Stores `.env` and `service_account.json` in Secret Manager
4. **Deploy**: Creates/updates Cloud Run service with proper configuration
5. **Test**: Verifies deployment with health check

## Port Configuration

### Local Development
- FastAPI: `http://localhost:8080`
- MCP Server: `http://localhost:8081`
- ADK Agent: `http://localhost:8082`

### Cloud Run Production
- External: `https://your-service-url` (routes to port 8080)
- Internal services (8081, 8082) accessible only within container

## Resource Recommendations

### Starter Configuration
```yaml
Memory: 2Gi
CPU: 2
Min Instances: 0
Max Instances: 5
Concurrency: 80
```

### Production Configuration
```yaml
Memory: 4Gi
CPU: 4
Min Instances: 1  # Keep warm for faster response
Max Instances: 10
Concurrency: 80
```

## Monitoring & Troubleshooting

### View Logs
```powershell
# Stream logs in real-time
gcloud run logs tail galaxy-of-knowledge-backend --region us-central1

# Read recent logs
gcloud run logs read galaxy-of-knowledge-backend --region us-central1 --limit 100
```

### Check Service Status
```powershell
gcloud run services describe galaxy-of-knowledge-backend --region us-central1
```

### Common Issues & Solutions

#### Issue: Container starts but services fail
**Solution**: Check logs for specific service errors
```powershell
# Inside container logs
docker exec galaxy-backend cat /tmp/fastapi.log
docker exec galaxy-backend cat /tmp/mcp_server.log
docker exec galaxy-backend cat /tmp/adk_agent.log
```

#### Issue: Database connection fails
**Solution**: 
1. Verify `.env` has correct database credentials
2. Check if Cloud SQL instance is running
3. Ensure service account has Cloud SQL Client role
4. For Cloud SQL, add `--add-cloudsql-instances` flag

#### Issue: Secrets not loading
**Solution**:
1. Verify secrets exist in Secret Manager
2. Check service account has Secret Accessor role
3. Verify secret names match in deployment command

## Cost Estimation

### Cloud Run Costs (Approximate)
- **Compute**: ~$0.065/vCPU-hour + ~$0.0065/GB-hour
- **Requests**: First 2M free/month, then $0.40/million
- **Example**: 2 vCPU, 2GB, 1M requests/month ≈ $10-15/month

### Cost Optimization Tips
1. Use `min-instances: 0` for low traffic (accept cold starts)
2. Right-size memory/CPU (start small, scale up if needed)
3. Set appropriate `max-instances` to prevent runaway costs
4. Monitor usage in GCP Console

## Next Steps

### 1. Test Locally First
```powershell
docker-compose up
# Verify all services work
# Test API endpoints
# Check database connectivity
```

### 2. Deploy to Cloud Run
```powershell
.\deploy-cloud-run.ps1
```

### 3. Update Frontend
Update your frontend to use the new Cloud Run URL:
```typescript
const API_URL = 'https://your-service-url';
```

### 4. Set Up Monitoring (Optional)
- Enable Cloud Monitoring
- Set up alerts for errors/latency
- Configure log-based metrics

### 5. Custom Domain (Optional)
```powershell
gcloud run domain-mappings create --service galaxy-of-knowledge-backend --domain your-domain.com
```

## Files Summary

```
backend/
├── Dockerfile                    # Main production Dockerfile
├── Dockerfile.supervisor         # Alternative with Supervisor
├── .dockerignore                 # Docker ignore rules
├── docker-compose.yml            # Local dev compose file
├── deploy-cloud-run.sh          # Linux/Mac deployment script
├── deploy-cloud-run.ps1         # Windows PowerShell script
├── CLOUD_RUN_DEPLOYMENT.md      # Full deployment guide
├── DOCKER_QUICKSTART.md         # Quick reference
└── DOCKER_CLOUD_RUN_SUMMARY.md  # This file
```

## Support & Documentation

- **Docker**: https://docs.docker.com/
- **Cloud Run**: https://cloud.google.com/run/docs
- **FastAPI**: https://fastapi.tiangolo.com/
- **ADK**: https://github.com/google/adk
- **MCP**: Model Context Protocol documentation

## Ready to Deploy! 🚀

You now have everything needed to:
1. ✅ Build Docker images
2. ✅ Test locally with Docker Compose
3. ✅ Deploy to Google Cloud Run
4. ✅ Monitor and troubleshoot
5. ✅ Scale for production

**Run the deployment script when ready:**
```powershell
.\deploy-cloud-run.ps1
```
