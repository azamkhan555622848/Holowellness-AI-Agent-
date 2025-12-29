# HoloWellness Chatbot - Quick Deployment Guide

## Prerequisites
- AWS Account (ID: 982081069800)
- AWS CLI installed and configured
- Your OpenRouter API key: `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`

## Quick Deployment (2 Commands)

### Step 1: Setup AWS Infrastructure
```bash
cd deploy
./aws-setup.sh
```
This will:
- Create EC2 t3.small instance
- Setup security groups  
- Create SSH key pair
- Configure basic server setup

### Step 2: Deploy Application
```bash
# SSH into your new instance (IP will be shown after Step 1)
ssh -i holowellness-key.pem ubuntu@YOUR_INSTANCE_IP

# Clone and run deployment
git clone https://github.com/azamkhan555622848/Holowellness_Chatbot_version_1.0.git
cd Holowellness_Chatbot_version_1.0/deploy
./deploy-app.sh
```

## What Gets Deployed
- ✅ OpenRouter API integration (cloud-based LLM)
- ✅ MongoDB Atlas connection (existing cluster)
- ✅ S3 PDF synchronization (existing bucket)
- ✅ Production Flask app with Gunicorn
- ✅ Nginx reverse proxy
- ✅ Health checks and monitoring
- ✅ Systemd service management

## Access Your Application
After deployment, access via:
- **Health Check**: `http://YOUR_IP/health`
- **API Endpoint**: `http://YOUR_IP/api/chat`
- **Full Application**: `http://YOUR_IP/`

## Configuration
The app uses these environment variables (pre-configured):
- OpenRouter API key (for LLM calls)
- MongoDB Atlas connection (your existing cluster)
- AWS S3 credentials (for PDF storage)

## Monitoring
```bash
# Check service status
sudo systemctl status holowellness

# View logs
sudo journalctl -f -u holowellness

# Restart if needed
sudo systemctl restart holowellness
```

## Cost Estimate
- **EC2 t3.small**: ~$15/month
- **Data transfer**: ~$5/month
- **OpenRouter API**: Pay per use
- **Total**: ~$20-25/month + API usage

## Security Notes
- SSH access via key pair only
- MongoDB uses existing Atlas cluster
- Environment variables stored securely
- Health checks for monitoring

## Support
If deployment fails:
1. Check logs: `sudo journalctl -u holowellness`
2. Verify environment: `cat /opt/holowellness/backend/.env`
3. Test health: `curl http://localhost/health`