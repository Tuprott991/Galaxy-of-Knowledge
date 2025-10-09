# 🚀 Complete GCP Deployment Guide - Step by Step

## Overview
This guide will walk you through deploying your Galaxy of Knowledge backend (FastAPI + MCP Server + ADK Agent) to Google Cloud Run.

---

## ⚙️ Prerequisites Check

### 1. Install Google Cloud SDK
Download and install from: https://cloud.google.com/sdk/docs/install

**For Windows PowerShell:**
```powershell
# Download the installer
# https://cloud.google.com/sdk/docs/install#windows

# After installation, verify:
gcloud --version
```

### 2. Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop

```powershell
# Verify installation
docker --version
docker ps
```

### 3. Verify Your Files
```powershell
cd backend

# Check these files exist:
ls .env                    # ✅ Should exist
ls service_account.json    # ✅ Should exist
ls Dockerfile             # ✅ Should exist
ls requirements.txt       # ✅ Should exist
```

---

## 📋 STEP 1: GCP Project Setup

### 1.1 Authenticate with Google Cloud
```powershell
# Login to Google Cloud
gcloud auth login
```
This opens your browser. Sign in with your Google account.

### 1.2 List Your Projects
```powershell
# See all your GCP projects
gcloud projects list
```

### 1.3 Create New Project (if needed)
```powershell
# Create a new project
gcloud projects create galaxy-knowledge-prod --name="Galaxy of Knowledge"

# Or use existing project
gcloud config set project YOUR_PROJECT_ID
```

### 1.4 Set Default Project
```powershell
# Replace with your actual project ID
$env:GCP_PROJECT_ID = "your-project-id"
gcloud config set project $env:GCP_PROJECT_ID
```

### 1.5 Enable Billing
⚠️ **Important**: You need billing enabled to use Cloud Run

1. Go to: https://console.cloud.google.com/billing
2. Link a billing account to your project
3. Verify billing is enabled:
   ```powershell
   gcloud beta billing projects describe $env:GCP_PROJECT_ID
   ```

---

## 🔧 STEP 2: Enable Required APIs

```powershell
# Enable all required Google Cloud APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sqladmin.googleapis.com
```

**Wait for completion** (takes 1-2 minutes)

Verify APIs are enabled:
```powershell
gcloud services list --enabled
```

---

## 🗄️ STEP 3: Database Setup (PostgreSQL)

### Option A: Cloud SQL (Recommended for Production)

#### 3.1 Create Cloud SQL Instance
```powershell
# Create PostgreSQL instance
gcloud sql instances create galaxy-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YOUR_SECURE_PASSWORD

# This takes 5-10 minutes to complete
```

#### 3.2 Create Database
```powershell
gcloud sql databases create galaxy_db --instance=galaxy-postgres
```

#### 3.3 Create Database User
```powershell
gcloud sql users create galaxy_user \
    --instance=galaxy-postgres \
    --password=YOUR_SECURE_PASSWORD
```

#### 3.4 Get Connection Name
```powershell
gcloud sql instances describe galaxy-postgres --format="value(connectionName)"
# Save this! Format: PROJECT:REGION:INSTANCE_NAME
```

#### 3.5 Update Your `.env` File
```env
DB_HOST=/cloudsql/PROJECT:REGION:INSTANCE_NAME
DB_NAME=galaxy_db
DB_USER=galaxy_user
DB_PASSWORD=YOUR_SECURE_PASSWORD
DB_PORT=5432
```

### Option B: Use Existing Database
If you already have a PostgreSQL database, just update `.env` with its credentials.

---

## 🔐 STEP 4: Service Account Setup

### 4.1 Create Service Account (if you don't have one)
```powershell
gcloud iam service-accounts create galaxy-backend \
    --display-name="Galaxy Backend Service Account"
```

### 4.2 Grant Required Roles
```powershell
# Get your project number
$PROJECT_NUMBER = gcloud projects describe $env:GCP_PROJECT_ID --format="value(projectNumber)"

# Grant roles
gcloud projects add-iam-policy-binding $env:GCP_PROJECT_ID \
    --member="serviceAccount:galaxy-backend@$env:GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $env:GCP_PROJECT_ID \
    --member="serviceAccount:galaxy-backend@$env:GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $env:GCP_PROJECT_ID \
    --member="serviceAccount:galaxy-backend@$env:GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 4.3 Download Service Account Key (if needed)
```powershell
gcloud iam service-accounts keys create service_account.json \
    --iam-account=galaxy-backend@$env:GCP_PROJECT_ID.iam.gserviceaccount.com
```

---

## 🔒 STEP 5: Create Secrets in Secret Manager

### 5.1 Create `.env` Secret
```powershell
# Create secret from your .env file
gcloud secrets create galaxy-env --data-file=.env

# Verify
gcloud secrets describe galaxy-env
```

### 5.2 Create Service Account Secret
```powershell
# Create secret from your service_account.json
gcloud secrets create galaxy-service-account --data-file=service_account.json

# Verify
gcloud secrets describe galaxy-service-account
```

### 5.3 Grant Access to Service Account
```powershell
gcloud secrets add-iam-policy-binding galaxy-env \
    --member="serviceAccount:galaxy-backend@$env:GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding galaxy-service-account \
    --member="serviceAccount:galaxy-backend@$env:GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

---

## 🏗️ STEP 6: Build Docker Image

### 6.1 Build with Cloud Build (Recommended)
```powershell
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/$env:GCP_PROJECT_ID/galaxy-backend .

# This takes 5-10 minutes
```

### 6.2 Alternative: Build Locally
```powershell
# Build locally
docker build -t gcr.io/$env:GCP_PROJECT_ID/galaxy-backend .

# Push to Container Registry
docker push gcr.io/$env:GCP_PROJECT_ID/galaxy-backend
```

---

## 🚀 STEP 7: Deploy to Cloud Run

### 7.1 Deploy Service
```powershell
gcloud run deploy galaxy-of-knowledge-backend \
    --image gcr.io/$env:GCP_PROJECT_ID/galaxy-backend \
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
    --service-account galaxy-backend@$env:GCP_PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars "PORT=8080,MCP_PORT=8081,ADK_PORT=8082" \
    --set-secrets ".env=galaxy-env:latest,service_account.json=galaxy-service-account:latest"
```

### 7.2 If Using Cloud SQL, Add This Flag:
```powershell
# Add to the above command:
--add-cloudsql-instances PROJECT:REGION:INSTANCE_NAME
```

### 7.3 Wait for Deployment
Deployment takes 2-5 minutes. You'll see:
```
✓ Deploying... Done.
✓ Creating Revision...
✓ Routing traffic...
Service URL: https://galaxy-of-knowledge-backend-xyz-uc.a.run.app
```

**Save this URL!** You'll need it for your frontend.

---

## ✅ STEP 8: Verify Deployment

### 8.1 Test Health Endpoint
```powershell
$SERVICE_URL = gcloud run services describe galaxy-of-knowledge-backend --region us-central1 --format="value(status.url)"

# Test health check
curl $SERVICE_URL/health
```

**Expected response:**
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

### 8.2 Test API Documentation
```powershell
# Open in browser
start "$SERVICE_URL/docs"
```

### 8.3 Test Papers Endpoint
```powershell
curl "$SERVICE_URL/api/v1/papers"
```

---

## 🌐 STEP 9: Update Frontend

### 9.1 Get Your Backend URL
```powershell
echo $SERVICE_URL
# Example: https://galaxy-of-knowledge-backend-xyz-uc.a.run.app
```

### 9.2 Update Vercel Environment Variables

Go to: https://vercel.com/dashboard

1. Select your project: `galaxy-of-knowledge`
2. Go to **Settings** → **Environment Variables**
3. Add/Update these:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://galaxy-of-knowledge-backend-xyz-uc.a.run.app` |
| `VITE_ADK_URL` | `https://galaxy-of-knowledge-backend-xyz-uc.a.run.app` |

4. Click **Save**
5. Go to **Deployments** → **Redeploy** (click menu on latest deployment)

### 9.3 Test Frontend
Visit: https://galaxy-of-knowledge-eta.vercel.app

- ✅ Should load without errors
- ✅ Papers should display
- ✅ Chatbot should work
- ✅ No CORS errors in browser console

---

## 📊 STEP 10: Monitor Your Deployment

### 10.1 View Logs
```powershell
# Stream logs in real-time
gcloud run logs tail galaxy-of-knowledge-backend --region us-central1

# Read recent logs
gcloud run logs read galaxy-of-knowledge-backend --region us-central1 --limit 100
```

### 10.2 Check Service Status
```powershell
gcloud run services describe galaxy-of-knowledge-backend --region us-central1
```

### 10.3 View in Console
Open: https://console.cloud.google.com/run

---

## 🔄 STEP 11: Update/Redeploy

### When You Make Code Changes:

```powershell
# 1. Build new image
gcloud builds submit --tag gcr.io/$env:GCP_PROJECT_ID/galaxy-backend:v2 .

# 2. Update service
gcloud run services update galaxy-of-knowledge-backend \
    --image gcr.io/$env:GCP_PROJECT_ID/galaxy-backend:v2 \
    --region us-central1

# Or use the automated script:
.\deploy-cloud-run.ps1
```

---

## 💰 Cost Estimation

### Current Configuration:
- **Memory**: 2GB
- **CPU**: 2 vCPU
- **Min Instances**: 1 (always warm)
- **Max Instances**: 10

### Estimated Monthly Costs:
- **Low Traffic** (~10K requests): $10-20
- **Medium Traffic** (~100K requests): $30-60
- **High Traffic** (~1M requests): $100-200

### Cost Optimization:
```powershell
# Set min-instances to 0 to save costs (but slower cold starts)
gcloud run services update galaxy-of-knowledge-backend \
    --min-instances 0 \
    --region us-central1
```

---

## 🐛 Troubleshooting

### Issue: "Permission denied" errors

**Solution**: Make sure billing is enabled and APIs are activated
```powershell
gcloud services list --enabled
```

### Issue: Build fails

**Solution**: Check Dockerfile and requirements.txt
```powershell
# Test build locally first
docker build -t test .
```

### Issue: Service crashes on startup

**Solution**: Check logs for errors
```powershell
gcloud run logs read galaxy-of-knowledge-backend --region us-central1 --limit 50
```

### Issue: Database connection fails

**Solutions**:
1. Verify Cloud SQL instance is running
2. Check connection string in `.env`
3. Ensure `--add-cloudsql-instances` flag is set
4. Verify service account has Cloud SQL Client role

### Issue: CORS errors from frontend

**Solutions**:
1. Check `main.py` CORS settings allow your Vercel domain
2. Verify ADK Agent `--allow-origins` includes Vercel domain
3. Rebuild and redeploy

---

## 📝 Quick Reference Commands

### View Service URL
```powershell
gcloud run services describe galaxy-of-knowledge-backend --region us-central1 --format="value(status.url)"
```

### View Logs
```powershell
gcloud run logs tail galaxy-of-knowledge-backend --region us-central1
```

### Update Service
```powershell
gcloud run services update galaxy-of-knowledge-backend --region us-central1 [OPTIONS]
```

### Delete Service (if needed)
```powershell
gcloud run services delete galaxy-of-knowledge-backend --region us-central1
```

### List All Services
```powershell
gcloud run services list
```

---

## ✨ Automated Deployment Script

For easier redeployment, use the provided script:

```powershell
# Set your project ID
$env:GCP_PROJECT_ID = "your-project-id"
$env:GCP_REGION = "us-central1"

# Run deployment script
.\deploy-cloud-run.ps1
```

This script automatically:
1. Enables required APIs
2. Builds Docker image
3. Creates/updates secrets
4. Deploys to Cloud Run
5. Tests the deployment

---

## 🎉 Success Checklist

After deployment, verify:

- [ ] Backend URL received from Cloud Run
- [ ] Health check returns 200 OK
- [ ] API docs accessible at `/docs`
- [ ] Papers endpoint works
- [ ] Database connection successful
- [ ] Vercel environment variables updated
- [ ] Frontend loads without errors
- [ ] No CORS errors in browser console
- [ ] Chatbot works
- [ ] Logs show no errors

---

## 📚 Additional Resources

- **Cloud Run Documentation**: https://cloud.google.com/run/docs
- **Cloud SQL Documentation**: https://cloud.google.com/sql/docs
- **Secret Manager**: https://cloud.google.com/secret-manager/docs
- **Pricing Calculator**: https://cloud.google.com/products/calculator

---

## 🆘 Need Help?

1. **Check Logs First**:
   ```powershell
   gcloud run logs read galaxy-of-knowledge-backend --region us-central1
   ```

2. **Verify Configuration**:
   ```powershell
   gcloud run services describe galaxy-of-knowledge-backend --region us-central1
   ```

3. **Test Locally**:
   ```powershell
   docker-compose up
   ```

4. **GCP Console**: https://console.cloud.google.com/run

---

**You're ready to deploy! Start with STEP 1 and work through each step carefully.** 🚀

**Estimated Total Time**: 30-60 minutes for first deployment
