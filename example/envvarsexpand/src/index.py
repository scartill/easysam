import os
import json

def handler(event, context):
    local_var = os.environ.get('LOCAL_VAR', 'unknown')
    return {
        'statusCode': 200,
        'body': json.dumps({'local_var': local_var})
    }
