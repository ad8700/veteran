"""
Lambda handler for exporting grave data to CSV
"""
import csv
import io
import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

# S3 for storing export files
s3 = boto3.client('s3')
PHOTOS_BUCKET = os.environ['PHOTOS_BUCKET']


def decimal_default(obj):
    """JSON serializer for Decimal types from DynamoDB"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def response(status_code, body, content_type='application/json'):
    """Create API Gateway response"""
    headers = {
        'Content-Type': content_type,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

    if content_type == 'text/csv':
        headers['Content-Disposition'] = 'attachment; filename="veteran_graves_export.csv"'
        return {
            'statusCode': status_code,
            'headers': headers,
            'body': body
        }

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, default=decimal_default)
    }


def export_graves(event, context):
    """
    GET /export
    Export grave records to CSV format

    Query parameters:
    - format: 'csv' (default) or 'json'
    - cemetery_name: Filter by cemetery
    - start_date: Filter records created after this date (ISO format)
    - end_date: Filter records created before this date (ISO format)
    - include_photos: 'true' to include photo URLs (requires pre-signing)
    """
    try:
        params = event.get('queryStringParameters') or {}

        export_format = params.get('format', 'csv')
        cemetery_name = params.get('cemetery_name')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        include_photos = params.get('include_photos', 'false').lower() == 'true'

        # Fetch records
        if cemetery_name:
            result = table.query(
                IndexName='cemetery-index',
                KeyConditionExpression=Key('cemetery_name').eq(cemetery_name)
            )
            items = result.get('Items', [])

            # Handle pagination
            while 'LastEvaluatedKey' in result:
                result = table.query(
                    IndexName='cemetery-index',
                    KeyConditionExpression=Key('cemetery_name').eq(cemetery_name),
                    ExclusiveStartKey=result['LastEvaluatedKey']
                )
                items.extend(result.get('Items', []))
        else:
            result = table.scan()
            items = result.get('Items', [])

            # Handle pagination
            while 'LastEvaluatedKey' in result:
                result = table.scan(ExclusiveStartKey=result['LastEvaluatedKey'])
                items.extend(result.get('Items', []))

        # Filter by date range
        if start_date:
            items = [i for i in items if i.get('created_at', '') >= start_date]
        if end_date:
            items = [i for i in items if i.get('created_at', '') <= end_date]

        # Generate photo URLs if requested
        if include_photos:
            for item in items:
                if item.get('photo_key'):
                    try:
                        item['photo_url'] = s3.generate_presigned_url(
                            'get_object',
                            Params={
                                'Bucket': PHOTOS_BUCKET,
                                'Key': item['photo_key']
                            },
                            ExpiresIn=86400  # 24 hours
                        )
                    except Exception:
                        item['photo_url'] = None

        if export_format == 'json':
            return response(200, {
                'count': len(items),
                'records': items
            })

        # Generate CSV
        csv_output = generate_csv(items, include_photos)

        return response(200, csv_output, content_type='text/csv')

    except Exception as e:
        print(f"Error exporting graves: {e}")
        import traceback
        traceback.print_exc()
        return response(500, {'error': str(e)})


def generate_csv(items, include_photos=False):
    """Generate CSV string from grave records"""
    output = io.StringIO()

    # Define CSV columns
    columns = [
        'id',
        'veteran_name',
        'branch_of_service',
        'birth_year',
        'death_year',
        'cemetery_name',
        'latitude',
        'longitude',
        'accuracy',
        'notes',
        'created_at',
        'updated_at',
        'user_id'
    ]

    if include_photos:
        columns.append('photo_url')

    writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()

    for item in items:
        # Convert Decimal to float for CSV
        row = {}
        for col in columns:
            value = item.get(col)
            if isinstance(value, Decimal):
                row[col] = float(value)
            else:
                row[col] = value
        writer.writerow(row)

    return output.getvalue()
