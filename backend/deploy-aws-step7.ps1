Write-Info "`nStep 7/8: Deploying to App Runner..."

$serviceExists = aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='$ServiceName'].ServiceArn" --output text

if ([string]::IsNullOrEmpty($serviceExists)) {
    Write-Info "Creating new App Runner service..."
    
    # Create service configuration as a PowerShell object and convert to JSON
    $serviceConfig = @{
        ServiceName = $ServiceName
        SourceConfiguration = @{
            ImageRepository = @{
                ImageIdentifier = "${ECR_REPO}:latest"
                ImageRepositoryType = "ECR"
                ImageConfiguration = @{
                    Port = "8080"
                    RuntimeEnvironmentVariables = @{
                        PORT = "8080"
                        FRONTEND_URL = "https://galaxy-of-knowledge-eta.vercel.app"
                    }
                }
            }
            AutoDeploymentsEnabled = $true
            AuthenticationConfiguration = @{
                AccessRoleArn = $ROLE_ARN
            }
        }
        InstanceConfiguration = @{
            Cpu = "1024"
            Memory = "2048"
        }
        HealthCheckConfiguration = @{
            Protocol = "HTTP"
            Path = "/health"
            Interval = 10
            Timeout = 5
            HealthyThreshold = 1
            UnhealthyThreshold = 5
        }
    }
    
    # Convert to JSON and save
    $serviceConfig | ConvertTo-Json -Depth 10 | Out-File -Encoding ascii -NoNewline service-config.json
    
    Write-Info "Creating App Runner service..."
    $result = aws apprunner create-service --cli-input-json file://service-config.json 2>&1 | ConvertFrom-Json
    
    if ($LASTEXITCODE -eq 0) {
        $SERVICE_ARN = $result.Service.ServiceArn
        Remove-Item service-config.json
        
        Write-Info "Waiting for service to be ready (this takes ~5 minutes)..."
        Write-Info "Service ARN: $SERVICE_ARN"
        
        # Poll for service status (App Runner doesn't have wait command)
        $maxAttempts = 60
        $attempt = 0
        do {
            Start-Sleep -Seconds 10
            $attempt++
            $status = (aws apprunner describe-service --service-arn $SERVICE_ARN --query 'Service.Status' --output text 2>&1)
            Write-Info "Status: $status (attempt $attempt/$maxAttempts)"
        } while ($status -ne "RUNNING" -and $attempt -lt $maxAttempts)
        
        if ($status -eq "RUNNING") {
            Write-Success "App Runner service created and running!"
        } else {
            Write-Warning "Service created but not yet running. Status: $status"
        }
    } else {
        Write-Error "Failed to create App Runner service. Check service-config.json for issues."
        exit 1
    }
}
else {
    Write-Info "Updating existing App Runner service..."
    $SERVICE_ARN = $serviceExists
    
    Write-Info "Starting deployment..."
    aws apprunner start-deployment --service-arn $SERVICE_ARN | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Waiting for deployment to complete..."
        
        # Poll for deployment status
        $maxAttempts = 60
        $attempt = 0
        do {
            Start-Sleep -Seconds 10
            $attempt++
            $status = (aws apprunner describe-service --service-arn $SERVICE_ARN --query 'Service.Status' --output text 2>&1)
            Write-Info "Status: $status (attempt $attempt/$maxAttempts)"
        } while ($status -ne "RUNNING" -and $attempt -lt $maxAttempts)
        
        if ($status -eq "RUNNING") {
            Write-Success "App Runner service updated and running!"
        } else {
            Write-Warning "Deployment in progress. Status: $status"
        }
    } else {
        Write-Error "Failed to start deployment"
        exit 1
    }
}

# Step 8: Get Service URL and Test
Write-Info "`nStep 8/8: Verifying deployment..."

$SERVICE_URL = (aws apprunner describe-service --service-arn $SERVICE_ARN --query 'Service.ServiceUrl' --output text 2>&1)
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to get service URL"
    exit 1
}

Write-Success "`nDeployment Complete!"
Write-Host @"

================================================
       Deployment Successful!
================================================

Service URL: https://$SERVICE_URL

Next Steps:

1. Test your API:
   https://$SERVICE_URL/health
   https://$SERVICE_URL/docs

2. Update Vercel Environment Variables:
   - Go to: https://vercel.com/dashboard
   - Add: VITE_API_URL=https://$SERVICE_URL
   - Add: VITE_ADK_URL=https://$SERVICE_URL

3. View Logs:
   aws logs tail /aws/apprunner/$ServiceName --follow

4. Check Service Status:
   aws apprunner describe-service --service-arn $SERVICE_ARN

5. Pause Service (to save costs when not in use):
   aws apprunner pause-service --service-arn $SERVICE_ARN

Documentation:
   - AWS_APP_RUNNER_DEPLOYMENT.md
   - https://docs.aws.amazon.com/apprunner/

"@ -ForegroundColor Cyan

# Test health endpoint
Write-Info "Testing health endpoint..."
try {
    $response = Invoke-WebRequest -Uri "https://$SERVICE_URL/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Success "Health check passed!"
    }
}
catch {
    Write-Warning "Health check failed. Service may still be starting up."
    Write-Info "Wait a few minutes and test manually: https://$SERVICE_URL/health"
}

Write-Info "`nSaving deployment info..."
@"
Deployment Information
=====================
Date: $(Get-Date)
Service Name: $ServiceName
Service ARN: $SERVICE_ARN
Service URL: https://$SERVICE_URL
Region: $Region
ECR Repository: $ECR_REPO
Database Endpoint: $DB_ENDPOINT

Quick Commands:
--------------
# View logs
aws logs tail /aws/apprunner/$ServiceName --follow

# Redeploy
docker build -t ${ServiceName}:latest . && docker tag ${ServiceName}:latest ${ECR_REPO}:latest && docker push ${ECR_REPO}:latest && aws apprunner start-deployment --service-arn $SERVICE_ARN

# Pause service
aws apprunner pause-service --service-arn $SERVICE_ARN

# Resume service
aws apprunner resume-service --service-arn $SERVICE_ARN

# Delete service
aws apprunner delete-service --service-arn $SERVICE_ARN
"@ | Out-File -Encoding utf8 deployment-info.txt

Write-Success "Deployment info saved to deployment-info.txt"
Write-Host "`nDone!" -ForegroundColor Green
