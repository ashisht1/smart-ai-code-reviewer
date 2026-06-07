#!/usr/bin/env python3
import os
import time
import zipfile
import json
import boto3
from botocore.exceptions import ClientError

ROLE_NAME = "smart-code-reviewer-lambda-role"
FUNCTION_NAME = "smart-code-reviewer"
REGION = "us-east-1" # Default region, can be overridden by AWS_DEFAULT_REGION

def create_deployment_zip():
    print("Creating deployment zip...")
    zip_path = "deployment.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write("lambda_function.py")
        z.write("index.html")
    print("Zip created: deployment.zip")
    return zip_path

def get_or_create_iam_role():
    iam = boto3.client("iam")
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        role = iam.get_role(RoleName=ROLE_NAME)
        print(f"Role {ROLE_NAME} already exists.")
        return role["Role"]["Arn"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            print(f"Creating IAM role {ROLE_NAME}...")
            role = iam.create_role(
                RoleName=ROLE_NAME,
                AssumeRolePolicyDocument=json.dumps(trust_policy)
            )
            print("Attaching basic execution policy...")
            iam.attach_role_policy(
                RoleName=ROLE_NAME,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
            # Wait for IAM role replication propagation
            print("Waiting 10 seconds for role propagation...")
            time.sleep(10)
            return role["Role"]["Arn"]
        else:
            raise e

def deploy_lambda(zip_path, role_arn, api_key):
    # Determine region from env or fall back to default
    region = os.getenv("AWS_DEFAULT_REGION", os.getenv("AWS_REGION", REGION))
    print(f"Deploying to region: {region}")
    
    awslambda = boto3.client("lambda", region_name=region)
    
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    env_vars = {}
    if api_key:
        env_vars["GEMINI_API_KEY"] = api_key
        print("Embedding GEMINI_API_KEY into Lambda configuration.")
    else:
        print("⚠️ Warning: GEMINI_API_KEY is not set in your local environment. You will need to add it to your Lambda configuration manually to run AI reviews.")

    try:
        # Check if function exists
        awslambda.get_function(FunctionName=FUNCTION_NAME)
        print(f"Function {FUNCTION_NAME} exists. Updating code...")
        awslambda.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_bytes
        )
        # Update environment variables
        awslambda.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Environment={"Variables": env_vars}
        )
        print("Update completed successfully.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"Function {FUNCTION_NAME} not found. Creating new Lambda function...")
            awslambda.create_function(
                FunctionName=FUNCTION_NAME,
                Runtime="python3.11",
                Role=role_arn,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": zip_bytes},
                Description="Serverless Code Reviewer UI & Backend",
                Timeout=30, # Max timeout for AI queries
                MemorySize=128,
                Environment={"Variables": env_vars}
            )
            print("Creation completed successfully.")
        else:
            raise e

    # Create or Get Function URL
    print("Configuring Lambda Function URL (Public Access)...")
    url_config = None
    try:
        url_config = awslambda.create_function_url_config(
            FunctionName=FUNCTION_NAME,
            AuthType="NONE"
        )
        print("Function URL configuration created.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            url_config = awslambda.get_function_url_config(
                FunctionName=FUNCTION_NAME
            )
            print("Function URL configuration already exists.")
        else:
            raise e

    # Grant Public Permissions to Function URL
    try:
        awslambda.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId="FunctionURLAllowPublicAccess",
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE"
        )
        print("Public invoke permission granted.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            print("Public invoke permission already configured.")
        else:
            raise e

    function_url = url_config["FunctionUrl"]
    print(f"\n🎉 Successfully deployed!")
    print(f"👉 Live Application URL: {function_url}\n")
    return function_url

def main():
    zip_path = create_deployment_zip()
    role_arn = get_or_create_iam_role()
    api_key = os.getenv("GEMINI_API_KEY", "")
    deploy_lambda(zip_path, role_arn, api_key)

if __name__ == "__main__":
    main()
