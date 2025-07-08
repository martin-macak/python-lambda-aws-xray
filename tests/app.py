def lambda_handler(event, _):
    print(event)
    return {
        "statusCode": 200,
        "body": "Hello, World!"
    }