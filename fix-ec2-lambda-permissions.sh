#!/bin/bash
# Fix EC2 Lambda invoke permissions

echo "🔐 Adding Lambda invoke permissions to EC2 role..."

# Get the EC2 instance role name
INSTANCE_ROLE_NAME="holowellness"

# Create Lambda invoke policy
cat > lambda-invoke-policy.json << 'LAMBDA_POLICY'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:ap-northeast-3:982081069800:function:holowellness-rag-indexer"
            ]
        }
    ]
}
LAMBDA_POLICY

# Create and attach the policy
POLICY_NAME="HolowellnessLambdaInvokePolicy"

# Check if policy exists
if aws iam get-policy --policy-arn "arn:aws:iam::982081069800:policy/${POLICY_NAME}" >/dev/null 2>&1; then
    echo "📋 Policy ${POLICY_NAME} already exists, updating..."
    
    # Create new version
    aws iam create-policy-version \
        --policy-arn "arn:aws:iam::982081069800:policy/${POLICY_NAME}" \
        --policy-document file://lambda-invoke-policy.json \
        --set-as-default
else
    echo "🆕 Creating new policy ${POLICY_NAME}..."
    
    # Create the policy
    aws iam create-policy \
        --policy-name "${POLICY_NAME}" \
        --policy-document file://lambda-invoke-policy.json \
        --description "Allows EC2 instance to invoke holowellness Lambda functions"
fi

# Attach policy to EC2 role
echo "🔗 Attaching policy to EC2 role ${INSTANCE_ROLE_NAME}..."
aws iam attach-role-policy \
    --role-name "${INSTANCE_ROLE_NAME}" \
    --policy-arn "arn:aws:iam::982081069800:policy/${POLICY_NAME}"

echo "✅ Lambda invoke permissions added successfully!"
echo "🔄 You may need to wait 1-2 minutes for permissions to propagate"

# Clean up
rm -f lambda-invoke-policy.json

echo ""
echo "🧪 Now you can test the Lambda function:"
echo "curl -X POST http://localhost:5000/api/rag/reindex-lambda"