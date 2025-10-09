# AWS App Runner Deployment Script for Galaxy of Knowledge Backend
# This script automates the deployment process to AWS App Runner

param(
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "galaxy-backend",
    
    [Parameter(Mandatory=$false)]
    [string]$DBPassword = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateDatabase = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipSecrets = $false
)

# Colors for output
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }

Write-Host @"
================================================
  AWS App Runner Deployment
  Galaxy of Knowledge Backend
================================================
"@ -ForegroundColor Cyan

# Check prerequisites
Write-Info "`nChecking prerequisites..."

# Check AWS CLI
try {
    $awsVersion = aws --version 2>&1
    Write-Success "AWS CLI: $awsVersion"
}
catch {
    Write-Error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
    exit 1
}

# Check Docker
try {
    $dockerVersion = docker --version
    Write-Success "Docker: $dockerVersion"
    
    # Check if Docker daemon is running
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker Desktop is not running. Please start Docker Desktop and try again."
        exit 1
    }
}
catch {
    Write-Error "Docker not found. Please install Docker Desktop"
    exit 1
}

# Check AWS credentials
try {
    $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
    Write-Success "AWS Credentials configured"
    Write-Info "  Account ID: $($identity.Account)"
    Write-Info "  User: $($identity.Arn)"
}
catch {
    Write-Error "AWS credentials not configured. Run: aws configure"
    exit 1
}

# Set environment variables
$env:AWS_REGION = $Region
$AWS_ACCOUNT_ID = $identity.Account
$ECR_REPO = "$AWS_ACCOUNT_ID.dkr.ecr.$Region.amazonaws.com/$ServiceName"

Write-Info "`nConfiguration:"
Write-Info "  Region: $Region"
Write-Info "  Service Name: $ServiceName"
Write-Info "  ECR Repository: $ECR_REPO"

# Step 1: Create IAM Role for App Runner
Write-Info "`nStep 1/8: Setting up IAM Role..."

$roleExists = aws iam get-role --role-name AppRunnerECRAccessRole 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Info "Creating AppRunnerECRAccessRole..."
    
    # Create trust policy with proper JSON formatting
    $trustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"build.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
    
    $trustPolicy | Out-File -Encoding ascii -NoNewline trust-policy.json
    
    aws iam create-role --role-name AppRunnerECRAccessRole --assume-role-policy-document file://trust-policy.json | Out-Null
    
    aws iam attach-role-policy --role-name AppRunnerECRAccessRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess | Out-Null
    
    # Add Secrets Manager permission
    aws iam attach-role-policy --role-name AppRunnerECRAccessRole --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite | Out-Null
    
    Remove-Item trust-policy.json
    Write-Success "IAM Role created"
}
else {
    Write-Success "IAM Role already exists"
}

$ROLE_ARN = (aws iam get-role --role-name AppRunnerECRAccessRole --query 'Role.Arn' --output text)

# Step 2: Create RDS PostgreSQL Database (optional)
if ($CreateDatabase) {
    Write-Info "`nStep 2/8: Setting up PostgreSQL Database..."
    
    $dbExists = aws rds describe-db-instances --db-instance-identifier galaxy-postgres 2>&1
    if ($LASTEXITCODE -ne 0) {
        if ([string]::IsNullOrEmpty($DBPassword)) {
            Write-Warning "Database password not provided. Generating random password..."
            $DBPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object {[char]$_}) + "Aa1!"
            Write-Info "Generated password: $DBPassword"
            Write-Warning "Save this password! You'll need it for DATABASE_URL"
        }
        
        Write-Info "Creating RDS PostgreSQL instance (this takes ~10 minutes)..."
        aws rds create-db-instance --db-instance-identifier galaxy-postgres --db-instance-class db.t3.micro --engine postgres --engine-version 15.4 --master-username postgres --master-user-password $DBPassword --allocated-storage 20 --storage-type gp3 --publicly-accessible --backup-retention-period 7 --tags Key=Project,Value=GalaxyOfKnowledge | Out-Null
        
        Write-Info "Waiting for database to be available..."
        aws rds wait db-instance-available --db-instance-identifier galaxy-postgres
        
        # Configure security group
        $SG_ID = (aws rds describe-db-instances --db-instance-identifier galaxy-postgres --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text)
        
        aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr 0.0.0.0/0 2>&1 | Out-Null
        
        Write-Success "Database created"
    }
    else {
        Write-Success "Database already exists"
    }
    
    $DB_ENDPOINT = (aws rds describe-db-instances --db-instance-identifier galaxy-postgres --query 'DBInstances[0].Endpoint.Address' --output text)
    
    Write-Info "  Database Endpoint: $DB_ENDPOINT"
    $DATABASE_URL = "postgresql://postgres:$DBPassword@$DB_ENDPOINT:5432/galaxy"
}
else {
    Write-Success "`nStep 2/8: Using existing database from .env"
    Write-Info "  Using your existing DATABASE_URL from .env file"
}

# Step 3: Create Secrets in AWS Secrets Manager
if (-not $SkipSecrets) {
    Write-Info "`nStep 3/8: Configuring Secrets Manager..."
    
    # Update .env with database URL if we created a new database
    if ($CreateDatabase -and -not [string]::IsNullOrEmpty($DATABASE_URL)) {
        $envContent = Get-Content .env -Raw
        if ($envContent -match "DATABASE_URL=.*") {
            $envContent = $envContent -replace "DATABASE_URL=.*", "DATABASE_URL=$DATABASE_URL"
        }
        else {
            $envContent += "`nDATABASE_URL=$DATABASE_URL"
        }
        $envContent | Out-File -Encoding utf8 .env
        Write-Info "  Updated .env with new database URL"
    }
    else {
        Write-Info "  Using existing DATABASE_URL from .env"
    }
    
    # Create or update .env secret
    $secretExists = aws secretsmanager describe-secret --secret-id galaxy-backend-env 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Creating galaxy-backend-env secret..."
        aws secretsmanager create-secret --name galaxy-backend-env --description "Environment variables for Galaxy Backend" --secret-string (Get-Content .env -Raw) | Out-Null
    }
    else {
        Write-Info "Updating galaxy-backend-env secret..."
        aws secretsmanager update-secret --secret-id galaxy-backend-env --secret-string (Get-Content .env -Raw) | Out-Null
    }
    
    # Create or update service account secret
    if (Test-Path "service_account.json") {
        $secretExists = aws secretsmanager describe-secret --secret-id galaxy-service-account 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Info "Creating galaxy-service-account secret..."
            # Read and properly escape JSON for AWS CLI
            $serviceAccountJson = Get-Content service_account.json -Raw | ConvertFrom-Json | ConvertTo-Json -Compress -Depth 10
            aws secretsmanager create-secret --name galaxy-service-account --description "Google Cloud service account for Vertex AI" --secret-string $serviceAccountJson | Out-Null
        }
        else {
            Write-Info "Updating galaxy-service-account secret..."
            $serviceAccountJson = Get-Content service_account.json -Raw | ConvertFrom-Json | ConvertTo-Json -Compress -Depth 10
            aws secretsmanager update-secret --secret-id galaxy-service-account --secret-string $serviceAccountJson | Out-Null
        }
    }
    else {
        Write-Warning "service_account.json not found - skipping"
    }
    
    Write-Success "Secrets configured"
}
else {
    Write-Warning "Skipping secrets creation (SkipSecrets flag)"
}

# Step 4: Create ECR Repository
Write-Info "`nStep 4/8: Setting up ECR Repository..."

$repoExists = aws ecr describe-repositories --repository-names $ServiceName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Info "Creating ECR repository..."
    aws ecr create-repository --repository-name $ServiceName --region $Region | Out-Null
    Write-Success "ECR repository created"
}
else {
    Write-Success "ECR repository already exists"
}

# Step 5: Build Docker Image
Write-Info "`nStep 5/8: Building Docker image..."

docker build -t ${ServiceName}:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed"
    exit 1
}
Write-Success "Docker image built"

# Step 6: Push to ECR
Write-Info "`nStep 6/8: Pushing image to ECR..."

Write-Info "Logging in to ECR..."
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ECR_REPO

Write-Info "Tagging image..."
docker tag ${ServiceName}:latest ${ECR_REPO}:latest

Write-Info "Pushing image..."
docker push ${ECR_REPO}:latest
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker push failed"
    exit 1
}
Write-Success "Image pushed to ECR"

# Step 7: Create or Update App Runner Service
Write-Info "`nStep 7/8: Deploying to App Runner..."

$serviceList = aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='$ServiceName']" --output json | ConvertFrom-Json
$serviceExists = $null

# Check if service exists and is in a valid state
foreach ($service in $serviceList) {
    $serviceArn = $service.ServiceArn
    $serviceStatus = (aws apprunner describe-service --service-arn $serviceArn --query 'Service.Status' --output text)
    
    if ($serviceStatus -eq "CREATE_FAILED" -or $serviceStatus -eq "DELETE_FAILED") {
        Write-Warning "Found service in $serviceStatus state. Deleting it..."
        aws apprunner delete-service --service-arn $serviceArn | Out-Null
        
        # Wait for deletion
        Write-Info "Waiting for service deletion..."
        $maxAttempts = 30
        $attempt = 0
        do {
            Start-Sleep -Seconds 10
            $attempt++
            $checkStatus = aws apprunner describe-service --service-arn $serviceArn --query 'Service.Status' --output text 2>&1
            if ($checkStatus -match "ResourceNotFoundException") {
                Write-Success "Service deleted successfully"
                break
            }
            Write-Info "Deletion in progress... (attempt $attempt/$maxAttempts)"
        } while ($attempt -lt $maxAttempts)
    } elseif ($serviceStatus -eq "RUNNING" -or $serviceStatus -eq "OPERATION_IN_PROGRESS") {
        $serviceExists = $serviceArn
    }
}

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
