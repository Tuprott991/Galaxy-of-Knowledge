# Test ADK Proxy - Quick verification script

Write-Host "Testing ADK Agent Proxy..." -ForegroundColor Cyan

# Test 1: Health check
Write-Host "`n1. Testing FastAPI health endpoint..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction SilentlyContinue
if ($health) {
    Write-Host "✅ FastAPI is running" -ForegroundColor Green
} else {
    Write-Host "❌ FastAPI is not responding" -ForegroundColor Red
    exit 1
}

# Test 2: ADK Proxy
Write-Host "`n2. Testing ADK Agent proxy..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/apps/adk-agent/" -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ ADK Agent proxy is working!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Got status code: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ ADK Agent proxy failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Direct ADK Agent
Write-Host "`n3. Testing direct ADK Agent connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8082/apps/adk-agent/" -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ ADK Agent is running on port 8082" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ ADK Agent is not responding on port 8082" -ForegroundColor Red
    Write-Host "   Make sure to start it: cd adk-agent; adk api_server --port 8082" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "If all tests pass, you're ready to deploy!" -ForegroundColor Cyan
Write-Host "Run: .\deploy-aws.ps1 -Region `"ap-southeast-1`"" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
