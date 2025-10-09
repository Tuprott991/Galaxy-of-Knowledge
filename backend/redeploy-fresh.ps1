# Quick Deploy Script - Deletes old service and creates new one

param(
    [Parameter(Mandatory=$false)]
    [string]$Region = "ap-southeast-1"
)

Write-Host "Cleaning up old App Runner service..." -ForegroundColor Yellow

# Delete old service if exists
$oldService = aws apprunner list-services --region $Region --query "ServiceSummaryList[?ServiceName=='galaxy-backend'].ServiceArn" --output text

if ($oldService) {
    Write-Host "Found existing service, deleting..." -ForegroundColor Yellow
    aws apprunner delete-service --service-arn $oldService --region $Region
    
    Write-Host "Waiting for deletion to complete..." -ForegroundColor Yellow
    $maxWait = 30
    $waited = 0
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 10
        $status = aws apprunner describe-service --service-arn $oldService --region $Region 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Service deleted successfully!" -ForegroundColor Green
            break
        }
        $waited++
        Write-Host "Still deleting... ($waited/$maxWait)" -ForegroundColor Yellow
    }
}

Write-Host "`nStarting fresh deployment..." -ForegroundColor Cyan
.\deploy-aws.ps1 -Region $Region
