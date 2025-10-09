# 🐳 Docker Quick Reference Guide

## Local Testing

### Build and Run with Docker
```bash
# Build the image
docker build -t galaxy-backend .

# Run the container
docker run -p 8080:8080 -p 8081:8081 -p 8082:8082 \
  --env-file .env \
  -v $(pwd)/service_account.json:/app/service_account.json \
  galaxy-backend

# Run in background
docker run -d -p 8080:8080 -p 8081:8081 -p 8082:8082 \
  --name galaxy-backend \
  --env-file .env \
  -v $(pwd)/service_account.json:/app/service_account.json \
  galaxy-backend
```

### Using Docker Compose (Recommended for Local Dev)
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
```

### Supervisor Version (Better Process Management)
```bash
# Build with supervisor
docker build -f Dockerfile.supervisor -t galaxy-backend:supervisor .

# Run
docker run -p 8080:8080 -p 8081:8081 -p 8082:8082 \
  --env-file .env \
  galaxy-backend:supervisor
```

## Testing the Container

### Test Endpoints
```bash
# Health check
curl http://localhost:8080/health

# API docs
open http://localhost:8080/docs

# MCP Server
curl http://localhost:8081/sse

# Check all services
curl http://localhost:8080/api/v1/papers
```

### View Container Logs
```bash
# View all logs
docker logs galaxy-backend

# Follow logs
docker logs -f galaxy-backend

# Last 100 lines
docker logs --tail 100 galaxy-backend

# Inside container logs
docker exec galaxy-backend tail -f /tmp/fastapi.log
docker exec galaxy-backend tail -f /tmp/mcp_server.log
docker exec galaxy-backend tail -f /tmp/adk_agent.log
```

### Debug Inside Container
```bash
# Enter container shell
docker exec -it galaxy-backend bash

# Check running processes
docker exec galaxy-backend ps aux

# Test internal connectivity
docker exec galaxy-backend curl http://localhost:8080/health
docker exec galaxy-backend curl http://localhost:8081/sse
docker exec galaxy-backend curl http://localhost:8082/
```

## Cloud Run Deployment

### Quick Deploy
```bash
# Set variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# Deploy
./deploy-cloud-run.sh
```

### Manual Cloud Build
```bash
# Submit to Cloud Build
gcloud builds submit --tag gcr.io/${GCP_PROJECT_ID}/galaxy-backend

# Deploy to Cloud Run
gcloud run deploy galaxy-backend \
  --image gcr.io/${GCP_PROJECT_ID}/galaxy-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Update Existing Deployment
```bash
# Build new image
gcloud builds submit --tag gcr.io/${GCP_PROJECT_ID}/galaxy-backend:v2

# Update service
gcloud run services update galaxy-backend \
  --image gcr.io/${GCP_PROJECT_ID}/galaxy-backend:v2 \
  --region us-central1
```

## Troubleshooting

### Container Won't Start
```bash
# Check if ports are available
netstat -an | grep 8080
lsof -i :8080

# Run with verbose output
docker run --rm -it galaxy-backend bash
# Then manually run: /app/start.sh
```

### Service Crashes
```bash
# Check exit code
docker inspect galaxy-backend | grep ExitCode

# Full container info
docker inspect galaxy-backend

# Resource usage
docker stats galaxy-backend
```

### Database Connection Issues
```bash
# Test database connection from container
docker exec galaxy-backend python -c "
import asyncio
from database.connect import init_db_pool, test_connection
asyncio.run(test_connection())
"
```

### Environment Variables
```bash
# List all env vars in container
docker exec galaxy-backend env

# Check specific variable
docker exec galaxy-backend echo $PORT
```

## Cleanup

### Remove Containers
```bash
# Stop and remove
docker stop galaxy-backend
docker rm galaxy-backend

# Force remove
docker rm -f galaxy-backend

# Docker Compose cleanup
docker-compose down -v  # Also remove volumes
```

### Remove Images
```bash
# Remove specific image
docker rmi galaxy-backend

# Remove all unused images
docker image prune -a

# Full cleanup
docker system prune -a --volumes
```

## Performance Tips

### Optimize Image Size
```bash
# Check image size
docker images galaxy-backend

# Use multi-stage build (already in Dockerfile)
# Use .dockerignore (already created)
```

### Resource Limits
```bash
# Run with memory limit
docker run --memory="2g" --cpus="2" galaxy-backend

# In docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       cpus: '2'
#       memory: 2G
```

## Useful Commands

### Docker Management
```bash
# List running containers
docker ps

# List all containers
docker ps -a

# List images
docker images

# Container resource usage
docker stats

# Inspect network
docker network ls
docker network inspect bridge
```

### Port Management
```bash
# Check port mappings
docker port galaxy-backend

# Test port accessibility
curl http://localhost:8080/health
curl http://localhost:8081/sse
curl http://localhost:8082/
```

## Environment Variables Reference

Required in `.env` file:
```env
# Database
DB_HOST=your-host
DB_NAME=galaxy_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_PORT=5432

# GCP
GCP_PROJECT_ID=your-project
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/app/service_account.json

# Ports (Cloud Run sets PORT automatically)
PORT=8080
MCP_PORT=8081
ADK_PORT=8082
```

## Next Steps

1. ✅ Test locally with `docker-compose up`
2. ✅ Verify all three services start correctly
3. ✅ Test API endpoints
4. ✅ Deploy to Cloud Run with `./deploy-cloud-run.sh`
5. ✅ Monitor logs and performance
6. ✅ Set up CI/CD pipeline (optional)
