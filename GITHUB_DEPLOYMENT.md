# GitHub Actions Deployment Guide

## 🚀 Automated AWS Deployment with GitHub Actions

This guide explains how to deploy your HoloWellness Chatbot to AWS using GitHub Actions - no local AWS CLI installation required!

## ✅ Prerequisites

1. **GitHub Repository**: Your code in https://github.com/azamkhan555622848/Holowellness_Chatbot_version_1.0
2. **AWS Account**: Access to create EC2 instances, S3 buckets, etc.
3. **AWS IAM User**: With programmatic access (Access Key ID and Secret)

## 🔐 Step 1: Create AWS IAM User

1. Go to AWS Console → IAM → Users → Create User
2. User name: `github-actions-deployment`
3. Attach policies:
   - `AmazonEC2FullAccess`
   - `AmazonS3FullAccess`
   - `IAMFullAccess`
   - `AmazonVPCFullAccess`
4. Create Access Key → Save the Access Key ID and Secret Access Key

## 🔒 Step 2: Configure GitHub Secrets

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Create these secrets:

| Secret Name | Value | Description |
|-------------|--------|-------------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | Your AWS Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | `abc123...` | Your AWS Secret Access Key |
| `AWS_REGION` | `ap-northeast-3` | AWS region (Osaka) |
| `AWS_SSH_PRIVATE_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | SSH private key (generated during deployment) |

**Note**: The SSH private key will be generated automatically during first deployment.

## 🛠️ Step 3: Configure Environment Variables

The deployment uses these environment variables (pre-configured in the workflow):

- **OpenRouter API**: Already configured with your API key
- **MongoDB Atlas**: Update with your connection string if needed
- **Region**: Set to `ap-northeast-3` (Osaka)

## 🚀 Step 4: Deploy

### Option A: Automatic Deployment (Recommended)
1. **Push code to main/master branch**:
   ```bash
   git add .
   git commit -m "Add GitHub Actions deployment"
   git push origin main
   ```

2. **Watch deployment**: Go to GitHub repository → **Actions** tab

### Option B: Manual Deployment
1. Go to GitHub repository → **Actions** tab
2. Select "Deploy HoloWellness Chatbot to AWS" workflow
3. Click **Run workflow** → **Run workflow**

## 📊 Step 5: Monitor Deployment

The GitHub Actions workflow will:

1. ✅ **Setup Environment** (Node.js, Python, AWS CLI)
2. ✅ **Build Frontend** (React TypeScript)
3. ✅ **Package Backend** (Python Flask)
4. ✅ **Create AWS Infrastructure** (EC2, Security Groups, SSH Keys)
5. ✅ **Deploy Application** (Copy files, start services)
6. ✅ **Health Check** (Verify deployment)

## 🎯 Step 6: Access Your Application

After successful deployment, you'll see:

```
🎉 Deployment completed successfully!
📍 Instance IP: 54.123.456.789
🔗 Health Check: http://54.123.456.789/health
🤖 API Endpoint: http://54.123.456.789/api/chat
🌐 Application: http://54.123.456.789/
```

## 🔍 Troubleshooting

### Common Issues:

1. **AWS Credentials Error**:
   - Verify GitHub secrets are set correctly
   - Check IAM user has required permissions

2. **SSH Key Error**:
   - First deployment will generate SSH key automatically
   - For subsequent deployments, add the private key to GitHub secrets

3. **Deployment Fails**:
   - Check **Actions** tab → Click on failed workflow → View logs
   - Common fixes: Update IAM permissions, check region availability

### View Logs:
```bash
# SSH into EC2 instance (IP from deployment summary)
ssh -i holowellness-key.pem ubuntu@YOUR_INSTANCE_IP

# Check application logs
sudo journalctl -f -u holowellness

# Check service status
sudo systemctl status holowellness
```

## 💡 Benefits of GitHub Actions Deployment

✅ **No Local Setup**: No AWS CLI installation required  
✅ **Automated**: Deploys on every push to main branch  
✅ **Consistent**: Same environment every time  
✅ **Scalable**: Easy to modify and extend  
✅ **Secure**: Credentials stored as GitHub secrets  
✅ **Traceable**: Full deployment logs and history  

## 🔄 Updating Your Application

Simply push code to your main branch:

```bash
git add .
git commit -m "Update application"
git push origin main
```

GitHub Actions will automatically:
1. Build the new version
2. Deploy to your existing EC2 instance
3. Restart services
4. Verify health

## 🛑 Cleanup

To remove AWS resources:

1. Go to AWS Console → EC2 → Terminate instance
2. Go to AWS Console → S3 → Delete deployment buckets
3. Or run cleanup from GitHub Actions (add cleanup workflow if needed)

## 📞 Support

If you encounter issues:
1. Check GitHub Actions logs
2. Review AWS CloudFormation events
3. SSH into EC2 and check application logs