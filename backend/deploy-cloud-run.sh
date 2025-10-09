#!/bin/bash

# ============================================
# Cloud Run Deployment Script
# Galaxy of Knowledge Backend
# ============================================

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="galaxy-of-knowledge-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
PORT=8080

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Galaxy of Knowledge - Cloud Run Deploy${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}📦 Setting GCP project to: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required GCP APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Build Docker image using Cloud Build
echo -e "${YELLOW}🏗️  Building Docker image...${NC}"
gcloud builds submit --tag ${IMAGE_NAME} .

# Create secrets in Secret Manager (if they don't exist)
echo -e "${YELLOW}🔐 Creating/updating secrets...${NC}"

# Create .env secret
if gcloud secrets describe galaxy-env --project=${PROJECT_ID} &> /dev/null; then
    echo "Updating galaxy-env secret..."
    gcloud secrets versions add galaxy-env --data-file=.env --project=${PROJECT_ID}
else
    echo "Creating galaxy-env secret..."
    gcloud secrets create galaxy-env --data-file=.env --project=${PROJECT_ID}
fi

# Create service account secret
if gcloud secrets describe galaxy-service-account --project=${PROJECT_ID} &> /dev/null; then
    echo "Updating galaxy-service-account secret..."
    gcloud secrets versions add galaxy-service-account --data-file=service_account.json --project=${PROJECT_ID}
else
    echo "Creating galaxy-service-account secret..."
    gcloud secrets create galaxy-service-account --data-file=service_account.json --project=${PROJECT_ID}
fi

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --port ${PORT} \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 80 \
    --max-instances 10 \
    --min-instances 1 \
    --allow-unauthenticated \
    --set-env-vars "PORT=${PORT},MCP_PORT=8081,ADK_PORT=8082" \
    --set-secrets ".env=galaxy-env:latest,service_account.json=galaxy-service-account:latest" \
    --service-account ${SERVICE_ACCOUNT_EMAIL}

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}API Docs:    ${SERVICE_URL}/docs${NC}"
echo -e "${GREEN}Health:      ${SERVICE_URL}/health${NC}"
echo -e "${GREEN}========================================${NC}"

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
if curl -s -f "${SERVICE_URL}/health" > /dev/null; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${RED}❌ Health check failed. Check logs:${NC}"
    echo -e "${YELLOW}gcloud run logs read --service ${SERVICE_NAME} --region ${REGION}${NC}"
fi
