# 🚀 Quick Deploy to GCP - Cheat Sheet

**For complete guide, see: `GCP_DEPLOYMENT_GUIDE.md`**

---

## Pre-Flight Check ✈️

```powershell
# Verify installations
gcloud --version  # Google Cloud SDK
docker --version  # Docker Desktop

# Check files exist
cd backend
ls .env, service_account.json, Dockerfile
```

---

## Quick Deploy (5 Commands) 🏃

### 1️⃣ Login & Set Project
```powershell
gcloud auth login
$env:GCP_PROJECT_ID = "your-project-id"
gcloud config set project $env:GCP_PROJECT_ID
```

### 2️⃣ Enable APIs
```powershell
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com
```

### 3️⃣ Create Secrets
```powershell
gcloud secrets create galaxy-env --data-file=.env
gcloud secrets create galaxy-service-account --data-file=service_account.json
```

### 4️⃣ Build & Deploy
```powershell
# This does everything!
.\deploy-cloud-run.ps1
```

**OR Manual:**
```powershell
# Build
gcloud builds submit --tag gcr.io/$env:GCP_PROJECT_ID/galaxy-backend .

# Deploy
gcloud run deploy galaxy-of-knowledge-backend \
    --image gcr.io/$env:GCP_PROJECT_ID/galaxy-backend \
    --region us-central1 \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --allow-unauthenticated \
    --set-env-vars "PORT=8080,MCP_PORT=8081,ADK_PORT=8082" \
    --set-secrets ".env=galaxy-env:latest,service_account.json=galaxy-service-account:latest"
```

### 5️⃣ Get URL & Update Frontend
```powershell
# Get backend URL
gcloud run services describe galaxy-of-knowledge-backend --region us-central1 --format="value(status.url)"

# Copy this URL and add to Vercel:
# VITE_API_URL = <YOUR_URL>
# VITE_ADK_URL = <YOUR_URL>
```

---

## Test Deployment ✅

```powershell
$URL = "https://your-service-url"

# Health check
curl "$URL/health"

# API docs
start "$URL/docs"

# Test endpoint
curl "$URL/api/v1/papers"
```

---

## Update After Code Changes 🔄

```powershell
# Option 1: Automated
.\deploy-cloud-run.ps1

# Option 2: Manual
gcloud builds submit --tag gcr.io/$env:GCP_PROJECT_ID/galaxy-backend:v2 .
gcloud run services update galaxy-of-knowledge-backend --image gcr.io/$env:GCP_PROJECT_ID/galaxy-backend:v2 --region us-central1
```

---

## View Logs 📋

```powershell
# Stream logs
gcloud run logs tail galaxy-of-knowledge-backend --region us-central1

# Read logs
gcloud run logs read galaxy-of-knowledge-backend --region us-central1 --limit 50
```

---

## Common Issues 🐛

**Build fails?**
```powershell
# Test locally first
docker build -t test .
docker run -p 8080:8080 test
```

**Service crashes?**
```powershell
# Check logs
gcloud run logs read galaxy-of-knowledge-backend --region us-central1
```

**CORS errors?**
- Check `main.py` allows your Vercel domain
- Rebuild and redeploy

**Database connection fails?**
- Update `.env` with correct DB credentials
- If using Cloud SQL, add: `--add-cloudsql-instances PROJECT:REGION:INSTANCE`

---

## Cost Settings 💰

**Save Money** (slower cold starts):
```powershell
gcloud run services update galaxy-of-knowledge-backend --min-instances 0 --region us-central1
```

**Always Warm** (no cold starts, costs more):
```powershell
gcloud run services update galaxy-of-knowledge-backend --min-instances 1 --region us-central1
```

---

## Full Checklist ✓

- [ ] Google Cloud SDK installed
- [ ] Docker Desktop installed
- [ ] GCP project created
- [ ] Billing enabled
- [ ] `.env` file configured
- [ ] `service_account.json` exists
- [ ] APIs enabled
- [ ] Secrets created
- [ ] Image built
- [ ] Service deployed
- [ ] Health check passes
- [ ] Vercel env vars updated
- [ ] Frontend works

---

## URLs You Need 🔗

**GCP Console**: https://console.cloud.google.com/run  
**Vercel Dashboard**: https://vercel.com/dashboard  
**Your Frontend**: https://galaxy-of-knowledge-eta.vercel.app/

---

## Quick Commands Reference 📚

```powershell
# View service URL
gcloud run services describe galaxy-of-knowledge-backend --region us-central1 --format="value(status.url)"

# Update service
gcloud run services update galaxy-of-knowledge-backend --region us-central1

# Delete service
gcloud run services delete galaxy-of-knowledge-backend --region us-central1

# List services
gcloud run services list

# View service details
gcloud run services describe galaxy-of-knowledge-backend --region us-central1
```

---

## One-Liner Deploy 🎯

```powershell
$env:GCP_PROJECT_ID="your-project-id"; .\deploy-cloud-run.ps1
```

---

**That's it! For detailed explanations, see `GCP_DEPLOYMENT_GUIDE.md`** 📖
