# Veteran Grave Marker - AWS Infrastructure Deployment Script (PowerShell)
# Usage: .\deploy.ps1 [-Environment dev|prod] [-GoogleClientId "..."] [-GoogleClientSecret "..."]

param(
    [string]$Environment = "dev",
    [string]$GoogleClientId = "",
    [string]$GoogleClientSecret = ""
)

$ErrorActionPreference = "Stop"

$Region = aws configure get region
$AccountId = aws sts get-caller-identity --query Account --output text

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Veteran Grave Marker Infrastructure Deploy" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Environment: $Environment"
Write-Host "Region: $Region"
Write-Host "Account: $AccountId"
Write-Host ""

# Stack names
$CognitoStack = "veteran-grave-cognito-$Environment"
$StorageStack = "veteran-grave-storage-$Environment"
$ApiStack = "veteran-grave-api-$Environment"

# Check for SAM CLI
$samExists = Get-Command sam -ErrorAction SilentlyContinue
if (-not $samExists) {
    Write-Host "ERROR: AWS SAM CLI is required for deploying the API stack." -ForegroundColor Red
    Write-Host "Install it with: pip install aws-sam-cli"
    Write-Host ""
    Write-Host "You can still deploy Cognito and Storage stacks manually."
    exit 1
}

# Deploy Storage Stack first (no dependencies)
Write-Host ""
Write-Host "Step 1/3: Deploying Storage Stack..." -ForegroundColor Yellow
Write-Host "--------------------------------------"

aws cloudformation deploy `
    --template-file storage.yaml `
    --stack-name $StorageStack `
    --parameter-overrides Environment=$Environment `
    --no-fail-on-empty-changeset

Write-Host "Storage stack deployed successfully!" -ForegroundColor Green

# Deploy Cognito Stack
Write-Host ""
Write-Host "Step 2/3: Deploying Cognito Stack..." -ForegroundColor Yellow
Write-Host "--------------------------------------"

if ([string]::IsNullOrEmpty($GoogleClientId) -or [string]::IsNullOrEmpty($GoogleClientSecret)) {
    Write-Host "WARNING: Google OAuth credentials not provided." -ForegroundColor Yellow
    Write-Host "You can deploy the Cognito stack later with:"
    Write-Host "  .\deploy.ps1 -Environment $Environment -GoogleClientId YOUR_ID -GoogleClientSecret YOUR_SECRET"
    Write-Host ""
    Write-Host "Skipping Cognito deployment for now..."
} else {
    aws cloudformation deploy `
        --template-file cognito.yaml `
        --stack-name $CognitoStack `
        --parameter-overrides `
            Environment=$Environment `
            GoogleClientId=$GoogleClientId `
            GoogleClientSecret=$GoogleClientSecret `
        --capabilities CAPABILITY_NAMED_IAM `
        --no-fail-on-empty-changeset

    Write-Host "Cognito stack deployed successfully!" -ForegroundColor Green
}

# Deploy API Stack (requires SAM and Cognito)
Write-Host ""
Write-Host "Step 3/3: Deploying API Stack..." -ForegroundColor Yellow
Write-Host "--------------------------------------"

# Check if Cognito stack exists
$cognitoExists = $null
try {
    $cognitoExists = aws cloudformation describe-stacks --stack-name $CognitoStack 2>$null
} catch {
    $cognitoExists = $null
}

if ($cognitoExists) {
    Push-Location $PSScriptRoot

    sam build --template-file api.yaml

    sam deploy `
        --template-file .aws-sam/build/template.yaml `
        --stack-name $ApiStack `
        --parameter-overrides `
            Environment=$Environment `
            CognitoStackName=$CognitoStack `
            StorageStackName=$StorageStack `
        --capabilities CAPABILITY_NAMED_IAM `
        --no-fail-on-empty-changeset `
        --resolve-s3

    Pop-Location

    Write-Host "API stack deployed successfully!" -ForegroundColor Green
} else {
    Write-Host "WARNING: Cognito stack not found. Deploy it first with Google credentials." -ForegroundColor Yellow
    Write-Host "Skipping API deployment..."
}

# Print outputs
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Stack Outputs:" -ForegroundColor Yellow
Write-Host "--------------"

# Get Storage outputs
Write-Host ""
Write-Host "Storage:" -ForegroundColor Cyan
aws cloudformation describe-stacks --stack-name $StorageStack `
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' `
    --output table

# Get Cognito outputs
try {
    $cognitoDesc = aws cloudformation describe-stacks --stack-name $CognitoStack 2>$null
    if ($cognitoDesc) {
        Write-Host ""
        Write-Host "Cognito:" -ForegroundColor Cyan
        aws cloudformation describe-stacks --stack-name $CognitoStack `
            --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' `
            --output table
    }
} catch {}

# Get API outputs
try {
    $apiDesc = aws cloudformation describe-stacks --stack-name $ApiStack 2>$null
    if ($apiDesc) {
        Write-Host ""
        Write-Host "API:" -ForegroundColor Cyan
        aws cloudformation describe-stacks --stack-name $ApiStack `
            --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' `
            --output table
    }
} catch {}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update your mobile app with the API endpoint and Cognito IDs"
Write-Host "2. Configure Google OAuth callback URL in Google Cloud Console:"
Write-Host "   - Add callback: https://veteran-grave-marker-$Environment-$AccountId.auth.$Region.amazoncognito.com/oauth2/idpresponse"
Write-Host "3. Test the API endpoints"
