#!/bin/bash

# Professional Lambda deployment script
set -e

# Configuration
FUNCTION_NAME="holowellness-rag-indexer"
REGION="ap-northeast-3"
ROLE_NAME="holowellness-lambda-role"
S3_BUCKET="holowellness"

echo "🚀 Deploying Lambda function: $FUNCTION_NAME"

# Build package
echo "📦 Building deployment package..."
./build_package.sh

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    echo "🔄 Updating existing function..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://rag_indexer.zip \
        --region $REGION
        
    # Update function configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --memory-size 3008 \
        --timeout 900 \
        --ephemeral-storage Size=10240 \
        --environment Variables="{
            S3_BUCKET=$S3_BUCKET,
            S3_PDFS_PREFIX=rag_pdfs/,
            S3_CACHE_PREFIX=cache/current/,
            BATCH_SIZE=1,
            MAX_MEMORY_MB=2800,
            MIN_TEXT_CHARS=300
        }" \
        --region $REGION
        
else
    echo "🆕 Creating new function..."
    
    # Create IAM role if it doesn't exist
    if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
        echo "🔐 Creating IAM role..."
        
        # Create trust policy
        cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

        # Create execution policy
        cat > execution-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::$S3_BUCKET",
                "arn:aws:s3:::$S3_BUCKET/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords"
            ],
            "Resource": "*"
        }
    ]
}
EOF

        # Create role
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file://trust-policy.json
            
        # Attach policies
        aws iam put-role-policy \
            --role-name $ROLE_NAME \
            --policy-name "${ROLE_NAME}-execution-policy" \
            --policy-document file://execution-policy.json
            
        # Wait for role to be ready
        sleep 10
        
        # Clean up policy files
        rm trust-policy.json execution-policy.json
    fi
    
    # Get role ARN
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
    
    # Create function
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.9 \
        --role $ROLE_ARN \
        --handler rag_indexer.lambda_handler \
        --zip-file fileb://rag_indexer.zip \
        --memory-size 3008 \
        --timeout 900 \
        --ephemeral-storage Size=10240 \
        --environment Variables="{
            S3_BUCKET=$S3_BUCKET,
            S3_PDFS_PREFIX=rag_pdfs/,
            S3_CACHE_PREFIX=cache/current/,
            BATCH_SIZE=1,
            MAX_MEMORY_MB=2800,
            MIN_TEXT_CHARS=300
        }" \
        --tracing-config Mode=Active \
        --region $REGION
fi

# Create API Gateway trigger (optional)
echo "🌐 Setting up API Gateway..."
# This would create an API Gateway endpoint to trigger the function

echo "✅ Lambda function deployed successfully!"
echo "📋 Function details:"
aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.[FunctionName,Runtime,MemorySize,Timeout]' --output table

echo "🔗 To trigger manually:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --region $REGION output.json"