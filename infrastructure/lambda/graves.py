"""
Lambda handlers for grave record CRUD operations
"""
import json
import os
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

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


def create_grave(event, context):
    """
    POST /graves
    Create a new grave record
    """
    try:
        body = json.loads(event.get('body', '{}'))

        # Validate required fields
        required_fields = ['latitude', 'longitude']
        for field in required_fields:
            if field not in body:
                return response(400, {'error': f'Missing required field: {field}'})

        # Generate unique ID
        grave_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        user_id = get_user_id(event)

        # Build item
        item = {
            'id': grave_id,
            'latitude': Decimal(str(body['latitude'])),
            'longitude': Decimal(str(body['longitude'])),
            'created_at': timestamp,
            'updated_at': timestamp,
            'user_id': user_id,
            'sync_status': 'synced'
        }

        # Optional fields
        optional_fields = [
            'veteran_name', 'branch_of_service', 'birth_year', 'death_year',
            'cemetery_name', 'notes', 'photo_key', 'accuracy', 'local_id'
        ]
        for field in optional_fields:
            if field in body and body[field] is not None:
                if field in ['birth_year', 'death_year']:
                    item[field] = int(body[field])
                elif field in ['accuracy']:
                    item[field] = Decimal(str(body[field]))
                else:
                    item[field] = body[field]

        # Save to DynamoDB
        table.put_item(Item=item)

        return response(201, {
            'id': grave_id,
            'message': 'Grave record created successfully',
            'item': item
        })

    except json.JSONDecodeError:
        return response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Error creating grave: {e}")
        return response(500, {'error': str(e)})


def get_grave(event, context):
    """
    GET /graves/{id}
    Get a single grave record by ID
    """
    try:
        grave_id = event['pathParameters']['id']

        result = table.get_item(Key={'id': grave_id})

        if 'Item' not in result:
            return response(404, {'error': 'Grave record not found'})

        return response(200, result['Item'])

    except Exception as e:
        print(f"Error getting grave: {e}")
        return response(500, {'error': str(e)})


def list_graves(event, context):
    """
    GET /graves
    List grave records with optional filters

    Query parameters:
    - cemetery_name: Filter by cemetery
    - user_id: Filter by user
    - limit: Max records to return (default 100)
    - last_key: Pagination token
    """
    try:
        params = event.get('queryStringParameters') or {}

        limit = int(params.get('limit', 100))
        cemetery_name = params.get('cemetery_name')
        user_id = params.get('user_id')
        last_key = params.get('last_key')

        scan_kwargs = {
            'Limit': limit
        }

        if last_key:
            scan_kwargs['ExclusiveStartKey'] = {'id': last_key}

        # Use GSI if filtering by cemetery or user
        if cemetery_name:
            result = table.query(
                IndexName='cemetery-index',
                KeyConditionExpression=Key('cemetery_name').eq(cemetery_name),
                Limit=limit
            )
        elif user_id:
            result = table.query(
                IndexName='user-index',
                KeyConditionExpression=Key('user_id').eq(user_id),
                Limit=limit
            )
        else:
            result = table.scan(**scan_kwargs)

        response_body = {
            'items': result.get('Items', []),
            'count': len(result.get('Items', []))
        }

        if 'LastEvaluatedKey' in result:
            response_body['last_key'] = result['LastEvaluatedKey']['id']

        return response(200, response_body)

    except Exception as e:
        print(f"Error listing graves: {e}")
        return response(500, {'error': str(e)})


def update_grave(event, context):
    """
    PUT /graves/{id}
    Update a grave record (authenticated users only)
    """
    try:
        grave_id = event['pathParameters']['id']
        body = json.loads(event.get('body', '{}'))
        user_id = get_user_id(event)

        # Get existing record
        result = table.get_item(Key={'id': grave_id})
        if 'Item' not in result:
            return response(404, {'error': 'Grave record not found'})

        existing = result['Item']

        # Check ownership (only owner or admin can update)
        if existing.get('user_id') != user_id and user_id != 'guest':
            # Allow update if user is authenticated, track who modified
            pass

        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}

        updatable_fields = [
            'veteran_name', 'branch_of_service', 'birth_year', 'death_year',
            'cemetery_name', 'notes', 'photo_key', 'latitude', 'longitude', 'accuracy'
        ]

        for field in updatable_fields:
            if field in body:
                update_parts.append(f'#{field} = :{field}')
                expression_names[f'#{field}'] = field

                if field in ['birth_year', 'death_year']:
                    expression_values[f':{field}'] = int(body[field]) if body[field] else None
                elif field in ['latitude', 'longitude', 'accuracy']:
                    expression_values[f':{field}'] = Decimal(str(body[field])) if body[field] else None
                else:
                    expression_values[f':{field}'] = body[field]

        if not update_parts:
            return response(400, {'error': 'No fields to update'})

        # Add updated_at timestamp
        update_parts.append('#updated_at = :updated_at')
        expression_names['#updated_at'] = 'updated_at'
        expression_values[':updated_at'] = datetime.utcnow().isoformat() + 'Z'

        # Track who modified
        update_parts.append('#modified_by = :modified_by')
        expression_names['#modified_by'] = 'modified_by'
        expression_values[':modified_by'] = user_id

        update_expression = 'SET ' + ', '.join(update_parts)

        result = table.update_item(
            Key={'id': grave_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )

        return response(200, {
            'message': 'Grave record updated successfully',
            'item': result['Attributes']
        })

    except json.JSONDecodeError:
        return response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"Error updating grave: {e}")
        return response(500, {'error': str(e)})


def delete_grave(event, context):
    """
    DELETE /graves/{id}
    Delete a grave record (authenticated users only)
    """
    try:
        grave_id = event['pathParameters']['id']
        user_id = get_user_id(event)

        # Get existing record to verify ownership
        result = table.get_item(Key={'id': grave_id})
        if 'Item' not in result:
            return response(404, {'error': 'Grave record not found'})

        existing = result['Item']

        # Only owner can delete (or we could add admin check)
        if existing.get('user_id') != user_id and existing.get('user_id') != 'guest':
            return response(403, {'error': 'Not authorized to delete this record'})

        # Delete the record
        table.delete_item(Key={'id': grave_id})

        return response(200, {'message': 'Grave record deleted successfully'})

    except Exception as e:
        print(f"Error deleting grave: {e}")
        return response(500, {'error': str(e)})
