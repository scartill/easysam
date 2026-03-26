def handler(event, context):
    print("Local lambda schedule!")
    return {"statusCode": 200, "body": "Local"}
