#!/bin/bash
# AWS Infrastructure Setup Script for HoloWellness Chatbot
# Run this script to create AWS infrastructure

set -e  # Exit on any error

echo "🚀 HoloWellness Chatbot - AWS Infrastructure Setup"
echo "================================================="

# Configuration
REGION="ap-northeast-3"  # Osaka region (matches your S3 bucket)
KEY_NAME="holowellness-key"
SECURITY_GROUP_NAME="holowellness-sg"
INSTANCE_TYPE="t3.small"
INSTANCE_NAME="HoloWellness-Server"

echo "📋 Configuration:"
echo "   Region: $REGION"
echo "   Instance Type: $INSTANCE_TYPE"
echo "   Key Name: $KEY_NAME"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first:"
    echo "   curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip'"
    echo "   unzip awscliv2.zip"
    echo "   sudo ./aws/install"
    exit 1
fi

# Check if AWS is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run:"
    echo "   aws configure"
    echo "   Then provide your AWS credentials"
    exit 1
fi

echo "✅ AWS CLI configured and working"

# Step 1: Create Key Pair
echo ""
echo "🔑 Step 1: Creating SSH Key Pair..."

# Delete existing key pair if it exists (we need to recreate to get the private key)
if aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION &> /dev/null; then
    echo "   Deleting existing key pair '$KEY_NAME'..."
    aws ec2 delete-key-pair --key-name $KEY_NAME --region $REGION
fi

# Create new key pair and save private key
echo "   Creating new key pair..."
aws ec2 create-key-pair --key-name $KEY_NAME --region $REGION --output text --query 'KeyMaterial' > ${KEY_NAME}.pem
chmod 400 ${KEY_NAME}.pem
echo "   ✅ Key pair created: ${KEY_NAME}.pem"

# Step 2: Create Security Group
echo ""
echo "🛡️  Step 2: Creating Security Group..."
if aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --region $REGION &> /dev/null; then
    echo "   Security group '$SECURITY_GROUP_NAME' already exists"
    SG_ID=$(aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --region $REGION --query 'SecurityGroups[0].GroupId' --output text)
else
    SG_ID=$(aws ec2 create-security-group --group-name $SECURITY_GROUP_NAME --description "HoloWellness Chatbot Security Group" --region $REGION --query 'GroupId' --output text)
    
    # Add security group rules
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $REGION
    
    echo "   ✅ Security group created: $SG_ID"
fi

# Step 3: Get Latest Ubuntu AMI
echo ""
echo "💿 Step 3: Getting latest Ubuntu 22.04 LTS AMI..."
AMI_ID=$(aws ec2 describe-images \
    --owners 099720109477 \
    --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" \
    --query 'Images|sort_by(@, &CreationDate)|[-1].ImageId' \
    --output text \
    --region $REGION)

echo "   AMI ID: $AMI_ID"

# Step 4: Launch EC2 Instance
echo ""
echo "🖥️  Step 4: Launching EC2 Instance..."

# Create user data script
cat > user-data.sh << 'EOF'
#!/bin/bash
# Initial server setup for HoloWellness Chatbot

# Update system
apt-get update && apt-get upgrade -y

# Install essential packages
apt-get install -y python3 python3-pip python3-venv nginx git curl unzip

# Install Node.js (for frontend build if needed)
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# Create application directory
mkdir -p /opt/holowellness
chown ubuntu:ubuntu /opt/holowellness

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws/

echo "✅ Server setup complete" > /var/log/user-data.log
EOF

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --user-data file://user-data.sh \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --region $REGION \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "   ✅ Instance launched: $INSTANCE_ID"

# Step 5: Wait for instance to be running
echo ""
echo "⏳ Step 5: Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get instance details
INSTANCE_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "   ✅ Instance is running!"
echo "   Public IP: $INSTANCE_IP"

# Cleanup
rm -f user-data.sh

# Summary
echo ""
echo "🎉 AWS Infrastructure Setup Complete!"
echo "=================================="
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $INSTANCE_IP"
echo "SSH Key: ${KEY_NAME}.pem"
echo "Security Group: $SG_ID"
echo ""
echo "📝 Next Steps:"
echo "1. Wait 2-3 minutes for instance initialization to complete"
echo "2. SSH into the server:"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@$INSTANCE_IP"
echo "3. Run the application deployment script"
echo ""
echo "🔗 Save this information for deployment!"

# Save instance info for deployment
cat > instance-info.txt << EOF
INSTANCE_ID=$INSTANCE_ID
INSTANCE_IP=$INSTANCE_IP
KEY_NAME=$KEY_NAME
REGION=$REGION
SECURITY_GROUP_ID=$SG_ID
EOF

echo "📄 Instance information saved to: instance-info.txt"