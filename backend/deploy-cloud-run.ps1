# ============================================
# Cloud Run Deployment Script (PowerShell)
# Galaxy of Knowledge Backend
# ============================================

# Configuration
$PROJECT_ID = $env:GCP_PROJECT_ID
if (-not $PROJECT_ID) {
    $PROJECT_ID = Read-Host "Enter your GCP Project ID"
}

$REGION = $env:GCP_REGION
if (-not $REGION) {
    $REGION = "us-central1"
}

$SERVICE_NAME = "galaxy-of-knowledge-backend"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"
$PORT = 8080

Write-Host "========================================" -ForegroundColor Green
Write-Host "Galaxy of Knowledge - Cloud Run Deploy" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if gcloud is installed
try {
    $null = Get-Command gcloud -ErrorAction Stop
} catch {
    Write-Host "❌ gcloud CLI not found. Please install Google Cloud SDK." -ForegroundColor Red
    Write-Host "Download from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is installed
try {
    $null = Get-Command docker -ErrorAction Stop
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Set project
Write-Host "📦 Setting GCP project to: $PROJECT_ID" -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

# Enable required APIs
Write-Host "🔧 Enabling required GCP APIs..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Build Docker image using Cloud Build
Write-Host "🏗️  Building Docker image..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE_NAME .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Create secrets in Secret Manager
Write-Host "🔐 Creating/updating secrets..." -ForegroundColor Yellow

# Check and create .env secret
$envSecretExists = gcloud secrets describe galaxy-env --project=$PROJECT_ID 2>$null
if ($envSecretExists) {
    Write-Host "Updating galaxy-env secret..." -ForegroundColor Cyan
    gcloud secrets versions add galaxy-env --data-file=.env --project=$PROJECT_ID
} else {
    Write-Host "Creating galaxy-env secret..." -ForegroundColor Cyan
    gcloud secrets create galaxy-env --data-file=.env --project=$PROJECT_ID
}

# Check and create service account secret
$saSecretExists = gcloud secrets describe galaxy-service-account --project=$PROJECT_ID 2>$null
if ($saSecretExists) {
    Write-Host "Updating galaxy-service-account secret..." -ForegroundColor Cyan
    gcloud secrets versions add galaxy-service-account --data-file=service_account.json --project=$PROJECT_ID
} else {
    Write-Host "Creating galaxy-service-account secret..." -ForegroundColor Cyan
    gcloud secrets create galaxy-service-account --data-file=service_account.json --project=$PROJECT_ID
}

# Deploy to Cloud Run
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_NAME `
    --platform managed `
    --region $REGION `
    --port $PORT `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --concurrency 80 `
    --max-instances 10 `
    --min-instances 1 `
    --allow-unauthenticated `
    --set-env-vars "PORT=$PORT,MCP_PORT=8081,ADK_PORT=8082" `
    --set-secrets ".env=galaxy-env:latest,service_account.json=galaxy-service-account:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}

# Get service URL
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Service URL: $SERVICE_URL" -ForegroundColor Green
Write-Host "API Docs:    $SERVICE_URL/docs" -ForegroundColor Green
Write-Host "Health:      $SERVICE_URL/health" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Test the deployment
Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$SERVICE_URL/health" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Health check passed!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Health check returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Check logs with:" -ForegroundColor Yellow
    Write-Host "gcloud run logs read --service $SERVICE_NAME --region $REGION" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "🎉 Deployment script completed!" -ForegroundColor Green
