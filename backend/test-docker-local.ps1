# Quick test script to verify Dockerfile fixes locally
Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build -t galaxy-backend-test:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful! Starting container..." -ForegroundColor Green
    
    # Run container in detached mode
    $containerId = docker run -d -p 8080:8080 -p 8081:8081 -p 8082:8082 `
        -e DATABASE_URL="postgresql://user:pass@host:5432/db" `
        -e FRONTEND_URL="https://galaxy-of-knowledge-eta.vercel.app" `
        galaxy-backend-test:latest
    
    Write-Host "Container started: $containerId" -ForegroundColor Green
    Write-Host "Waiting 10 seconds for services to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Show logs
    Write-Host "`n=== Container Logs ===" -ForegroundColor Cyan
    docker logs $containerId
    
    # Test health endpoint
    Write-Host "`n=== Testing Health Endpoint ===" -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 5
        Write-Host "Health check: $($response.StatusCode) - $($response.Content)" -ForegroundColor Green
    } catch {
        Write-Host "Health check failed: $_" -ForegroundColor Red
    }
    
    # Cleanup
    Write-Host "`n=== Cleanup ===" -ForegroundColor Cyan
    docker stop $containerId
    docker rm $containerId
    Write-Host "Container stopped and removed" -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
