# ✅ Pre-Deployment Checklist

Before deploying to Cloud Run, ensure you have completed all these steps:

## 1. Prerequisites

### Install Required Software
- [ ] Google Cloud SDK (gcloud) installed
  - Download: https://cloud.google.com/sdk/docs/install
  - Verify: `gcloud --version`
- [ ] Docker Desktop installed and running
  - Download: https://www.docker.com/products/docker-desktop
  - Verify: `docker --version`
- [ ] Git installed (already have this)

### GCP Setup
- [ ] GCP Project created
- [ ] Billing enabled for the project
- [ ] gcloud authenticated: `gcloud auth login`
- [ ] Default project set: `gcloud config set project YOUR_PROJECT_ID`

## 2. Configuration Files

### `.env` File
- [ ] `.env` file exists in `backend/` directory
- [ ] Contains all required environment variables:
  ```env
  DB_HOST=
  DB_NAME=
  DB_USER=
  DB_PASSWORD=
  DB_PORT=
  GCP_PROJECT_ID=
  GCP_LOCATION=
  GOOGLE_APPLICATION_CREDENTIALS=/app/service_account.json
  PORT=8080
  MCP_PORT=8081
  ADK_PORT=8082
  ```
- [ ] Database credentials are correct
- [ ] No sensitive data will be committed to Git (`.env` in `.gitignore`)

### Service Account JSON
- [ ] `service_account.json` exists in `backend/` directory
- [ ] Service account has required roles:
  - [ ] Cloud SQL Client (if using Cloud SQL)
  - [ ] Vertex AI User
  - [ ] Secret Manager Secret Accessor
  - [ ] Cloud Run Invoker
- [ ] JSON file is valid (can open and view)
- [ ] File is in `.gitignore` (do not commit to Git)

## 3. Database Setup

### PostgreSQL Database
- [ ] Database instance is running and accessible
- [ ] Database `galaxy_db` (or your DB name) exists
- [ ] Database user has proper permissions
- [ ] Can connect from your local machine
- [ ] Required tables and schema exist

### For Cloud SQL
- [ ] Cloud SQL instance created
- [ ] Instance name noted: `PROJECT:REGION:INSTANCE_NAME`
- [ ] Public IP or Private IP configured
- [ ] Cloud SQL Admin API enabled
- [ ] Connection tested successfully

## 4. Docker Files

### Verify Files Exist
- [ ] `backend/Dockerfile` exists
- [ ] `backend/.dockerignore` exists
- [ ] `backend/docker-compose.yml` exists (optional, for local testing)
- [ ] `backend/requirements.txt` is complete and up to date

### Test Docker Build Locally
- [ ] Image builds successfully: `docker build -t galaxy-backend .`
- [ ] Image size is reasonable (check with `docker images`)
- [ ] No build errors or warnings

## 5. Local Testing

### Test with Docker Compose
- [ ] Start services: `docker-compose up`
- [ ] All three services start successfully:
  - [ ] FastAPI on port 8080
  - [ ] MCP Server on port 8081
  - [ ] ADK Agent on port 8082
- [ ] No errors in logs
- [ ] Services stay running (don't crash)

### Test Endpoints
- [ ] Health check works: `curl http://localhost:8080/health`
- [ ] API docs accessible: http://localhost:8080/docs
- [ ] Can fetch papers: `curl http://localhost:8080/api/v1/papers`
- [ ] Database queries work
- [ ] MCP Server responds: `curl http://localhost:8081/sse`

### Test Database Connection
- [ ] Database connection pool initializes
- [ ] Can read from database
- [ ] Can write to database (if applicable)
- [ ] No connection errors in logs

## 6. GCP Preparation

### Enable APIs
```powershell
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

- [ ] Cloud Build API enabled
- [ ] Cloud Run API enabled
- [ ] Container Registry API enabled
- [ ] Secret Manager API enabled
- [ ] Cloud SQL Admin API enabled (if using Cloud SQL)

### IAM & Permissions
- [ ] Service account email noted down
- [ ] Service account has all required roles
- [ ] Billing account linked to project
- [ ] You have Cloud Run Admin role (or Owner/Editor)

## 7. Secrets Management

### Secret Manager Setup
- [ ] Understand that `.env` will be stored as secret
- [ ] Understand that `service_account.json` will be stored as secret
- [ ] Secrets will be mounted to container at runtime
- [ ] Secrets are not included in Docker image

### Secret Names (will be created by script)
- [ ] `galaxy-env` - for .env file
- [ ] `galaxy-service-account` - for service_account.json

## 8. Deployment Script

### Windows PowerShell Script
- [ ] `deploy-cloud-run.ps1` exists
- [ ] Script is readable (check encoding)
- [ ] Set execution policy if needed:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### Environment Variables
- [ ] Set `$env:GCP_PROJECT_ID` or be ready to enter when prompted
- [ ] Set `$env:GCP_REGION` or use default (us-central1)

## 9. Resource Configuration

### Review Resource Settings (in deployment script)
- [ ] Memory: 2Gi (can increase if needed)
- [ ] CPU: 2 (can increase if needed)
- [ ] Min instances: 1 (or 0 to save costs)
- [ ] Max instances: 10 (adjust based on expected traffic)
- [ ] Concurrency: 80 (requests per container)
- [ ] Timeout: 300 seconds (5 minutes)

### Authentication
- [ ] Decide: Public (`--allow-unauthenticated`) or Private
- [ ] Current default: Public (anyone can access)
- [ ] Change if needed: `--no-allow-unauthenticated`

## 10. Cost Awareness

### Understand Cloud Run Pricing
- [ ] CPU/Memory costs: ~$0.065 per vCPU-hour
- [ ] Request costs: First 2M free, then $0.40/million
- [ ] Networking: Egress charges apply
- [ ] Estimate monthly cost based on usage

### Cost Controls
- [ ] Set max-instances to limit runaway costs
- [ ] Consider min-instances: 0 for dev, 1+ for prod
- [ ] Set up budget alerts in GCP Console
- [ ] Review pricing calculator

## 11. Networking & Security

### Cloud SQL Connection (if applicable)
- [ ] Cloud SQL instance running
- [ ] Connection method chosen:
  - [ ] Cloud SQL Proxy (recommended)
  - [ ] Private IP (requires VPC)
  - [ ] Public IP with authorized networks
- [ ] Update deployment script with `--add-cloudsql-instances` if needed

### CORS Configuration
- [ ] Frontend URL will be whitelisted (or using `*` for development)
- [ ] Review CORS settings in `main.py`
- [ ] Update for production if needed

## 12. Monitoring Setup (Optional but Recommended)

### Before Deployment
- [ ] Plan to set up error reporting
- [ ] Plan to set up uptime checks
- [ ] Plan to set up log-based alerts
- [ ] Set up notification channels (email, Slack, etc.)

## 13. Documentation Review

### Read Documentation
- [ ] Read `CLOUD_RUN_DEPLOYMENT.md` completely
- [ ] Understand `DOCKER_QUICKSTART.md` commands
- [ ] Review `DOCKER_CLOUD_RUN_SUMMARY.md`
- [ ] Keep links handy for troubleshooting

## 14. Backup & Rollback Plan

### Before First Deployment
- [ ] Commit all code changes to Git
- [ ] Push to remote repository
- [ ] Tag current version: `git tag v1.0-pre-deployment`
- [ ] Know how to rollback if needed

### Rollback Strategy
- [ ] Can redeploy previous image version
- [ ] Have database backup (if applicable)
- [ ] Can switch back to old infrastructure if needed

## 15. Final Checks

### Code Quality
- [ ] All code committed to Git
- [ ] No uncommitted changes
- [ ] `.gitignore` includes sensitive files
- [ ] No TODO comments for critical issues

### Testing
- [ ] All async functions have `await`
- [ ] Database pool initialized properly
- [ ] No known bugs in critical paths
- [ ] Health check endpoint works

### Environment
- [ ] In correct directory: `cd backend`
- [ ] Docker daemon is running
- [ ] Logged into `gcloud`: `gcloud auth list`
- [ ] Correct project selected: `gcloud config get-value project`

## 🚀 Ready to Deploy?

If ALL boxes above are checked, you're ready to deploy!

### Run Deployment
```powershell
# Navigate to backend directory
cd backend

# Run deployment script
.\deploy-cloud-run.ps1
```

### During Deployment
The script will:
1. ✅ Enable GCP APIs
2. ✅ Build Docker image (5-10 minutes)
3. ✅ Create secrets in Secret Manager
4. ✅ Deploy to Cloud Run (2-5 minutes)
5. ✅ Run health check

### After Deployment
- [ ] Service URL received
- [ ] Health check passed
- [ ] API docs accessible at `/docs`
- [ ] Test key endpoints
- [ ] Monitor logs for errors
- [ ] Update frontend with new backend URL

## Post-Deployment Tasks

### Immediate
- [ ] Test all major API endpoints
- [ ] Check Cloud Run logs for errors
- [ ] Verify database connectivity
- [ ] Test MCP Server functionality
- [ ] Update frontend environment variables

### Within 24 Hours
- [ ] Set up monitoring alerts
- [ ] Configure custom domain (if needed)
- [ ] Enable HTTPS (automatic on Cloud Run)
- [ ] Review resource usage
- [ ] Check costs in Billing

### Ongoing
- [ ] Monitor logs daily
- [ ] Review costs weekly
- [ ] Keep dependencies updated
- [ ] Rebuild image monthly for security updates

## Troubleshooting

If deployment fails, check:
1. Error messages in terminal
2. Cloud Build logs in GCP Console
3. Cloud Run logs: `gcloud run logs read`
4. Service status: `gcloud run services describe`
5. Review this checklist again

## Need Help?

- GCP Console: https://console.cloud.google.com
- Cloud Run Logs: Console → Cloud Run → Service → Logs
- Support: Check error messages and documentation

---

**Good luck with your deployment! 🎉**
