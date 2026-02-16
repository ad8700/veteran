"""
AWS Configuration for Veteran Grave Marker App
"""

# Environment: 'dev' or 'prod'
ENVIRONMENT = 'dev'

# API Gateway
API_ENDPOINT = 'https://ljjhd2vvw5.execute-api.us-east-1.amazonaws.com/dev'

# Cognito
AWS_REGION = 'us-east-1'
USER_POOL_ID = 'us-east-1_FqxH0NHAV'
USER_POOL_CLIENT_ID = 'gs6v3qlgjgqpe66bkflhgg7mi'
IDENTITY_POOL_ID = 'us-east-1:59b9712a-6f88-49f2-b346-a91bd64da896'

# Cognito Hosted UI (for Google Sign-In)
COGNITO_DOMAIN = 'https://veteran-grave-marker-dev-926974878870.auth.us-east-1.amazoncognito.com'
REDIRECT_URI = 'veterangravemarker://callback'
