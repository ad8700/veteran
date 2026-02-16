# Veteran Grave Marker - AWS Infrastructure

This directory contains CloudFormation templates and deployment scripts for the AWS backend.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Mobile App    │────▶│   API Gateway   │────▶│     Lambda      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
        ┌───────────────────────────────────────────────┼───────────┐
        │                       │                       │           │
        ▼                       ▼                       ▼           ▼
┌─────────────┐         ┌─────────────┐         ┌───────────┐
│   Cognito   │         │  DynamoDB   │         │    S3     │
│ User Pool   │         │   (Data)    │         │ (Photos)  │
└─────────────┘         └─────────────┘         └───────────┘
```

## Prerequisites

1. **AWS CLI** configured with credentials
2. **AWS SAM CLI** for Lambda deployment
   ```bash
   pip install aws-sam-cli
   ```

## Stacks

| Stack | Template | Description |
|-------|----------|-------------|
| cognito | `cognito.yaml` | Cognito User Pool, Identity Pool, Google IdP |
| storage | `storage.yaml` | DynamoDB table, S3 buckets |
| api | `api.yaml` | API Gateway, Lambda functions |

## Deployment

### Quick Start (PowerShell - Windows)

```powershell
cd infrastructure

# Deploy storage only (no Google OAuth yet)
.\deploy.ps1 -Environment dev

# Deploy with Google OAuth
.\deploy.ps1 -Environment dev -GoogleClientId "YOUR_CLIENT_ID" -GoogleClientSecret "YOUR_SECRET"
```

### Quick Start (Bash - Linux/Mac)

```bash
cd infrastructure
chmod +x deploy.sh

# Deploy with Google OAuth
./deploy.sh dev YOUR_GOOGLE_CLIENT_ID YOUR_GOOGLE_CLIENT_SECRET
```

### Manual Deployment

```bash
# 1. Deploy Storage
aws cloudformation deploy \
    --template-file storage.yaml \
    --stack-name veteran-grave-storage-dev \
    --parameter-overrides Environment=dev

# 2. Deploy Cognito
aws cloudformation deploy \
    --template-file cognito.yaml \
    --stack-name veteran-grave-cognito-dev \
    --parameter-overrides \
        Environment=dev \
        GoogleClientId=YOUR_ID \
        GoogleClientSecret=YOUR_SECRET \
    --capabilities CAPABILITY_NAMED_IAM

# 3. Build and Deploy API
sam build --template-file api.yaml
sam deploy \
    --stack-name veteran-grave-api-dev \
    --parameter-overrides \
        Environment=dev \
        CognitoStackName=veteran-grave-cognito-dev \
        StorageStackName=veteran-grave-storage-dev \
    --capabilities CAPABILITY_NAMED_IAM \
    --resolve-s3
```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth 2.0 Client IDs**
5. Application type: **Web application**
6. Add authorized redirect URI:
   ```
   https://veteran-grave-marker-dev-ACCOUNT_ID.auth.us-east-1.amazoncognito.com/oauth2/idpresponse
   ```
7. Copy the Client ID and Client Secret

## API Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/graves` | No | Create grave record |
| GET | `/graves` | No | List graves |
| GET | `/graves/{id}` | No | Get single grave |
| PUT | `/graves/{id}` | Yes | Update grave |
| DELETE | `/graves/{id}` | Yes | Delete grave |
| POST | `/graves/{id}/photo` | No | Get upload URL |
| GET | `/graves/{id}/photo` | No | Get download URL |
| POST | `/sync` | Yes | Sync offline data |
| GET | `/export` | Yes | Export to CSV |

## Environment Variables

Lambda functions use these environment variables:
- `ENVIRONMENT` - dev or prod
- `TABLE_NAME` - DynamoDB table name
- `PHOTOS_BUCKET` - S3 bucket for photos

## Cleanup

```bash
# Delete in reverse order
aws cloudformation delete-stack --stack-name veteran-grave-api-dev
aws cloudformation delete-stack --stack-name veteran-grave-cognito-dev
aws cloudformation delete-stack --stack-name veteran-grave-storage-dev
```

**Note:** S3 buckets must be emptied before stack deletion.
