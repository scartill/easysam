import boto3
import random
import time
import os
import datetime

# Configuration from environment variables
TABLE_NAME = os.environ.get('TABLE_NAME')
REGION = os.environ.get('REGION', 'us-east-1')

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def main():
    print(f"Starting poller for table: {TABLE_NAME}")
    while True:
        try:
            random_num = random.randint(1, 1000)
            timestamp = datetime.datetime.now(datetime.UTC).isoformat()
            
            print(f"[{timestamp}] Writing random number {random_num} to DynamoDB...")
            
            table.put_item(
                Item={
                    'id': f'stat-{timestamp}',
                    'value': random_num,
                    'timestamp': timestamp
                }
            )
            
            # Sleep for 20 seconds
            time.sleep(20)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5) # Wait a bit before retrying

if __name__ == "__main__":
    main()
