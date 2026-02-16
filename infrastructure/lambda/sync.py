"""
Lambda handler for offline-first data synchronization
"""
import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])


def decimal_default(obj):
    """JSON serializer for Decimal types from DynamoDB"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


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
        'body': json.dumps(body, default=decimal_default)
    }


def get_user_id(event):
    """Extract user ID from Cognito claims, or return 'guest'"""
    try:
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        return claims.get('sub', 'guest')
    except Exception:
        return 'guest'


def sync_records(event, context):
    """
    POST /sync
    Synchronize records between mobile app and cloud

    Request body:
    {
        "last_sync": "2024-01-01T00:00:00Z",  // ISO timestamp of last sync
        "records": [                           // Records to upload
            {
                "local_id": "local-uuid",      // Local database ID
                "latitude": 39.123,
                "longitude": -98.456,
                ...
            }
        ]
    }

    Response:
    {
        "uploaded": 5,                         // Records uploaded
        "downloaded": [                        // Records modified since last_sync
            { ... }
        ],
        "sync_timestamp": "2024-01-15T12:00:00Z"
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = get_user_id(event)

        last_sync = body.get('last_sync')
        records_to_upload = body.get('records', [])

        sync_timestamp = datetime.utcnow().isoformat() + 'Z'
        uploaded_count = 0
        id_mapping = {}  # Map local_id to cloud id

        # Process uploads
        for record in records_to_upload:
            local_id = record.get('local_id')

            # Check if this local_id already exists (re-sync scenario)
            existing = None
            if local_id:
                # Scan for existing record with this local_id
                scan_result = table.scan(
                    FilterExpression=Attr('local_id').eq(local_id) & Attr('user_id').eq(user_id)
                )
                if scan_result.get('Items'):
                    existing = scan_result['Items'][0]

            if existing:
                # Update existing record
                cloud_id = existing['id']
                update_record(cloud_id, record, user_id, sync_timestamp)
            else:
                # Create new record
                cloud_id = str(uuid.uuid4())
                create_record(cloud_id, record, user_id, sync_timestamp, local_id)

            id_mapping[local_id] = cloud_id
            uploaded_count += 1

        # Fetch records modified since last_sync
        downloaded_records = []
        if last_sync:
            # Query for user's records updated after last_sync
            scan_result = table.scan(
                FilterExpression=Attr('user_id').eq(user_id) & Attr('updated_at').gt(last_sync)
            )
            downloaded_records = scan_result.get('Items', [])
        else:
            # First sync - get all user's records
            if user_id != 'guest':
                query_result = table.query(
                    IndexName='user-index',
                    KeyConditionExpression=Key('user_id').eq(user_id)
                )
                downloaded_records = query_result.get('Items', [])

        return response(200, {
            'uploaded': uploaded_count,
            'id_mapping': id_mapping,
            'downloaded': downloaded_records,
            'sync_timestamp': sync_timestamp
        })

    except json.JSONDecodeError:
        return response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Error during sync: {e}")
        import traceback
        traceback.print_exc()
        return response(500, {'error': str(e)})


def create_record(cloud_id, record, user_id, timestamp, local_id):
    """Create a new grave record in DynamoDB"""
    item = {
        'id': cloud_id,
        'local_id': local_id,
        'latitude': Decimal(str(record['latitude'])),
        'longitude': Decimal(str(record['longitude'])),
        'created_at': timestamp,
        'updated_at': timestamp,
        'user_id': user_id,
        'sync_status': 'synced'
    }

    # Optional fields
    optional_fields = [
        'veteran_name', 'branch_of_service', 'birth_year', 'death_year',
        'cemetery_name', 'notes', 'photo_key', 'accuracy'
    ]
    for field in optional_fields:
        if field in record and record[field] is not None:
            if field in ['birth_year', 'death_year']:
                item[field] = int(record[field])
            elif field in ['accuracy']:
                item[field] = Decimal(str(record[field]))
            else:
                item[field] = record[field]

    table.put_item(Item=item)


def update_record(cloud_id, record, user_id, timestamp):
    """Update an existing grave record in DynamoDB"""
    update_parts = ['#updated_at = :updated_at', '#sync_status = :sync_status']
    expression_names = {
        '#updated_at': 'updated_at',
        '#sync_status': 'sync_status'
    }
    expression_values = {
        ':updated_at': timestamp,
        ':sync_status': 'synced'
    }

    updatable_fields = [
        'veteran_name', 'branch_of_service', 'birth_year', 'death_year',
        'cemetery_name', 'notes', 'photo_key', 'latitude', 'longitude', 'accuracy'
    ]

    for field in updatable_fields:
        if field in record:
            update_parts.append(f'#{field} = :{field}')
            expression_names[f'#{field}'] = field

            if field in ['birth_year', 'death_year']:
                expression_values[f':{field}'] = int(record[field]) if record[field] else None
            elif field in ['latitude', 'longitude', 'accuracy']:
                expression_values[f':{field}'] = Decimal(str(record[field])) if record[field] else None
            else:
                expression_values[f':{field}'] = record[field]

    table.update_item(
        Key={'id': cloud_id},
        UpdateExpression='SET ' + ', '.join(update_parts),
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values
    )
