#!/bin/bash
# Veteran Grave Marker - AWS Infrastructure Deployment Script
# Usage: ./deploy.sh [dev|prod] [google-client-id] [google-client-secret]

set -e

ENVIRONMENT=${1:-dev}
GOOGLE_CLIENT_ID=${2:-""}
GOOGLE_CLIENT_SECRET=${3:-""}

REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=========================================="
echo "Veteran Grave Marker Infrastructure Deploy"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# Stack names
COGNITO_STACK="veteran-grave-cognito-${ENVIRONMENT}"
STORAGE_STACK="veteran-grave-storage-${ENVIRONMENT}"
API_STACK="veteran-grave-api-${ENVIRONMENT}"

# Check for SAM CLI
if ! command -v sam &> /dev/null; then
    echo "ERROR: AWS SAM CLI is required for deploying the API stack."
    echo "Install it with: pip install aws-sam-cli"
    echo ""
    echo "Alternatively, you can deploy Cognito and Storage stacks without SAM:"
    echo "  aws cloudformation deploy --template-file cognito.yaml ..."
    exit 1
fi

# Deploy Cognito Stack
echo ""
echo "Step 1/3: Deploying Cognito Stack..."
echo "--------------------------------------"

if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "WARNING: Google OAuth credentials not provided."
    echo "You can update the stack later with:"
    echo "  aws cloudformation update-stack --stack-name $COGNITO_STACK \\"
    echo "    --template-body file://cognito.yaml \\"
    echo "    --parameters ParameterKey=GoogleClientId,ParameterValue=YOUR_ID \\"
    echo "                 ParameterKey=GoogleClientSecret,ParameterValue=YOUR_SECRET"
    echo ""
    echo "Skipping Cognito deployment for now..."
else
    aws cloudformation deploy \
        --template-file cognito.yaml \
        --stack-name "$COGNITO_STACK" \
        --parameter-overrides \
            Environment="$ENVIRONMENT" \
            GoogleClientId="$GOOGLE_CLIENT_ID" \
            GoogleClientSecret="$GOOGLE_CLIENT_SECRET" \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset

    echo "Cognito stack deployed successfully!"
fi

# Deploy Storage Stack
echo ""
echo "Step 2/3: Deploying Storage Stack..."
echo "--------------------------------------"

aws cloudformation deploy \
    --template-file storage.yaml \
    --stack-name "$STORAGE_STACK" \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
    --no-fail-on-empty-changeset

echo "Storage stack deployed successfully!"

# Deploy API Stack (requires SAM)
echo ""
echo "Step 3/3: Deploying API Stack..."
echo "--------------------------------------"

# Check if Cognito stack exists
if aws cloudformation describe-stacks --stack-name "$COGNITO_STACK" &> /dev/null; then
    sam build --template-file api.yaml

    sam deploy \
        --template-file .aws-sam/build/template.yaml \
        --stack-name "$API_STACK" \
        --parameter-overrides \
            Environment="$ENVIRONMENT" \
            CognitoStackName="$COGNITO_STACK" \
            StorageStackName="$STORAGE_STACK" \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset \
        --resolve-s3

    echo "API stack deployed successfully!"
else
    echo "WARNING: Cognito stack not found. Deploy it first with Google credentials."
    echo "Skipping API deployment..."
fi

# Print outputs
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

echo "Stack Outputs:"
echo "--------------"

# Get Cognito outputs
if aws cloudformation describe-stacks --stack-name "$COGNITO_STACK" &> /dev/null; then
    echo ""
    echo "Cognito:"
    aws cloudformation describe-stacks --stack-name "$COGNITO_STACK" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
fi

# Get Storage outputs
echo ""
echo "Storage:"
aws cloudformation describe-stacks --stack-name "$STORAGE_STACK" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

# Get API outputs
if aws cloudformation describe-stacks --stack-name "$API_STACK" &> /dev/null; then
    echo ""
    echo "API:"
    aws cloudformation describe-stacks --stack-name "$API_STACK" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
fi

echo ""
echo "Next steps:"
echo "1. Update your mobile app with the API endpoint and Cognito IDs"
echo "2. Configure Google OAuth callback URL in Google Cloud Console"
echo "3. Test the API endpoints"
