"""
Lambda handlers for photo upload/download pre-signed URLs
"""
import json
import os
from datetime import datetime

import boto3

# Initialize S3
s3 = boto3.client('s3')
PHOTOS_BUCKET = os.environ['PHOTOS_BUCKET']

# Initialize DynamoDB for updating photo_key
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])


def response(status_code, body):
    """Create API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body)
    }


def get_upload_url(event, context):
    """
    POST /graves/{id}/photo
    Generate a pre-signed URL for uploading a photo

    Request body (optional):
    - content_type: MIME type (default: image/jpeg)
    """
    try:
        grave_id = event['pathParameters']['id']

        # Verify grave exists
        result = table.get_item(Key={'id': grave_id})
        if 'Item' not in result:
            return response(404, {'error': 'Grave record not found'})

        # Parse request body
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])

        content_type = body.get('content_type', 'image/jpeg')

        # Generate S3 key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        photo_key = f"graves/{grave_id}/{timestamp}.jpg"

        # Generate pre-signed URL for upload
        upload_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': PHOTOS_BUCKET,
                'Key': photo_key,
                'ContentType': content_type
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )

        # Update the grave record with the photo key
        table.update_item(
            Key={'id': grave_id},
            UpdateExpression='SET photo_key = :pk, updated_at = :ua',
            ExpressionAttributeValues={
                ':pk': photo_key,
                ':ua': datetime.utcnow().isoformat() + 'Z'
            }
        )

        return response(200, {
            'upload_url': upload_url,
            'photo_key': photo_key,
            'expires_in': 3600,
            'content_type': content_type
        })

    except json.JSONDecodeError:
        return response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Error generating upload URL: {e}")
        return response(500, {'error': str(e)})


def get_download_url(event, context):
    """
    GET /graves/{id}/photo
    Generate a pre-signed URL for downloading a photo
    """
    try:
        grave_id = event['pathParameters']['id']

        # Get grave record to find photo key
        result = table.get_item(Key={'id': grave_id})
        if 'Item' not in result:
            return response(404, {'error': 'Grave record not found'})

        item = result['Item']
        photo_key = item.get('photo_key')

        if not photo_key:
            return response(404, {'error': 'No photo associated with this grave record'})

        # Verify photo exists in S3
        try:
            s3.head_object(Bucket=PHOTOS_BUCKET, Key=photo_key)
        except s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                return response(404, {'error': 'Photo file not found in storage'})
            raise

        # Generate pre-signed URL for download
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': PHOTOS_BUCKET,
                'Key': photo_key
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )

        return response(200, {
            'download_url': download_url,
            'photo_key': photo_key,
            'expires_in': 3600
        })

    except Exception as e:
        print(f"Error generating download URL: {e}")
        return response(500, {'error': str(e)})
