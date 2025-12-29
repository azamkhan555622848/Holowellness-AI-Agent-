# HoloWellness Chatbot - AWS Deployment Plan

## Overview
This document outlines the complete deployment strategy for migrating the HoloWellness chatbot from local development to AWS cloud infrastructure using OpenRouter API for LLM calls.

## Current Architecture vs Target Architecture

### Current Setup
- **LLM**: Local Ollama with DeepSeek-R1 model
- **Backend**: Flask application on local machine
- **Database**: Local MongoDB instance
- **Frontend**: React application (local development)
- **Documents**: Local PDF processing with RAG

### Target Architecture
```
Internet → CloudFront (CDN) → Application Load Balancer → EC2 Instance
                                                              ↓
                                                      Nginx → Gunicorn → Flask App
                                                              ↓
                                                    MongoDB Atlas (Cloud Database)
                                                              ↓
                                                    OpenRouter API (LLM Calls)
```

## Phase 1: Pre-Deployment Preparation

### 1.1 Code Modifications Required

#### Backend Changes
- [ ] Replace Ollama client with OpenRouter API client
- [ ] Update model names and API endpoints
- [ ] Add environment variable management
- [ ] Configure production logging
- [ ] Add health check endpoints
- [ ] Update CORS settings for production domain

#### Key Files to Modify:
- `rag_qwen.py` - Replace Ollama calls with OpenRouter
- `enhanced_rag_qwen.py` - Update API integration
- `app.py` - Add production configurations
- `memory_manager.py` - Update MongoDB connection string

### 1.2 Environment Variables Setup
```bash
# API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Database Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/holowellness
MONGODB_DATABASE=holowellness_prod

# Application Configuration
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=https://yourdomain.com

# AWS Configuration (if needed)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

### 1.3 Dependencies Update
Create `requirements-prod.txt`:
```
Flask==2.3.3
gunicorn==21.2.0
pymongo==4.5.0
sentence-transformers==2.2.2
faiss-cpu==1.7.4
numpy==1.24.3
pandas==2.0.3
scikit-learn==1.3.0
openai==1.3.7
python-dotenv==1.0.0
flask-cors==4.0.0
rank-bm25==0.2.2
langchain==0.0.335
langchain-core==0.0.12
langchain-openai==0.0.2
tiktoken==0.5.1
PyPDF2==3.0.1
python-docx==0.8.11
Pillow==10.0.1
```

## Phase 2: AWS Infrastructure Setup

### 2.1 EC2 Instance Configuration

#### Instance Specifications
- **Type**: `t3.large` (2 vCPU, 8GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 50GB GP3 SSD
- **Security Group**: Custom security group (see below)

#### Security Group Rules
```
Inbound:
- SSH (22) from your IP
- HTTP (80) from anywhere (0.0.0.0/0)
- HTTPS (443) from anywhere (0.0.0.0/0)
- Custom TCP (8000) from ALB only (for health checks)

Outbound:
- All traffic to anywhere (for API calls and updates)
```

### 2.2 Database Migration to MongoDB Atlas

#### Setup Steps
1. Create MongoDB Atlas account
2. Create cluster (M0 Free Tier or M10 for production)
3. Configure network access (add EC2 IP)
4. Create database user
5. Export local data and import to Atlas

#### Migration Commands
```bash
# Export from local MongoDB
mongodump --host localhost:27017 --db holowellness --out ./backup

# Import to Atlas
mongorestore --uri "mongodb+srv://username:password@cluster.mongodb.net/holowellness_prod" ./backup/holowellness
```

### 2.3 Application Load Balancer (Optional but Recommended)
- **Type**: Application Load Balancer
- **Scheme**: Internet-facing
- **Target Group**: EC2 instance on port 80
- **Health Check**: `/health` endpoint

## Phase 3: Application Deployment

### 3.1 Server Setup Script
```bash
#!/bin/bash
# server_setup.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv nginx

# Install Node.js for frontend (if needed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Create application user
sudo useradd -m -s /bin/bash holowellness
sudo usermod -aG sudo holowellness

# Create application directory
sudo mkdir -p /opt/holowellness
sudo chown holowellness:holowellness /opt/holowellness
```

### 3.2 Application Deployment Script
```bash
#!/bin/bash
# deploy.sh

# Navigate to application directory
cd /opt/holowellness

# Clone repository
git clone https://github.com/azamkhan555622848/Holowellness_Chatbot_version_1.0.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-prod.txt

# Set up environment variables
cp .env.example .env
# Edit .env with production values

# Create systemd service
sudo cp deploy/holowellness.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable holowellness
```

### 3.3 Systemd Service Configuration
Create `/etc/systemd/system/holowellness.service`:
```ini
[Unit]
Description=HoloWellness Chatbot
After=network.target

[Service]
Type=exec
User=holowellness
Group=holowellness
WorkingDirectory=/opt/holowellness/backend
ExecStart=/opt/holowellness/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --timeout 300 app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

Environment=FLASK_ENV=production
EnvironmentFile=/opt/holowellness/.env

[Install]
WantedBy=multi-user.target
```

### 3.4 Nginx Configuration
Create `/etc/nginx/sites-available/holowellness`:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # API routes
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Frontend (if serving from same server)
    location / {
        root /opt/holowellness/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

## Phase 4: Code Migration Implementation

### 4.1 OpenRouter Integration
Replace Ollama calls in `rag_qwen.py`:

```python
import openai
import os
from typing import Dict, List, Any

class OpenRouterLLM:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.model_name = "deepseek/deepseek-r1"  # or preferred model
    
    def chat(self, messages: List[Dict], options: Dict = None) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=options.get("temperature", 0.4),
                max_tokens=options.get("num_predict", 300),
                top_p=options.get("top_p", 0.8)
            )
            
            return {
                "message": {
                    "content": response.choices[0].message.content
                }
            }
        except Exception as e:
            print(f"OpenRouter API error: {e}")
            return {"message": {"content": "I apologize, but I'm having trouble processing your request right now. Please try again."}}
```

### 4.2 Production Configuration
Update `app.py` for production:

```python
import os
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# Production configuration
if os.getenv('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    CORS(app, origins=os.getenv('CORS_ORIGINS', '').split(','))
else:
    app.config['DEBUG'] = True
    CORS(app)

# Add health check endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'holowellness-api'}, 200
```

## Phase 5: Deployment Checklist

### Pre-Deployment
- [ ] OpenRouter API key obtained and tested
- [ ] MongoDB Atlas cluster created and configured
- [ ] Domain name registered and DNS configured
- [ ] SSL certificate ready (Let's Encrypt)
- [ ] Environment variables defined
- [ ] Code modifications completed and tested locally

### Infrastructure Setup
- [ ] EC2 instance launched with correct specifications
- [ ] Security groups configured
- [ ] Elastic IP allocated (optional but recommended)
- [ ] Load balancer configured (if using)

### Application Deployment
- [ ] Server dependencies installed
- [ ] Application code deployed
- [ ] Environment variables configured
- [ ] Database connection tested
- [ ] SSL certificate installed
- [ ] Nginx configured and tested
- [ ] Systemd service created and started

### Post-Deployment Testing
- [ ] API endpoints responding correctly
- [ ] Chat functionality working
- [ ] Memory/conversation history working
- [ ] Document retrieval functioning
- [ ] SSL certificate valid
- [ ] Performance monitoring setup

### Monitoring and Maintenance
- [ ] CloudWatch monitoring configured
- [ ] Log rotation setup
- [ ] Backup strategy implemented
- [ ] Auto-scaling policies (if needed)
- [ ] Update procedures documented

## Phase 6: Cost Optimization

### Estimated Monthly Costs (USD)
- **EC2 t3.large**: ~$60/month
- **MongoDB Atlas M10**: ~$57/month (or M0 free tier)
- **OpenRouter API**: Variable based on usage (~$10-50/month)
- **Data Transfer**: ~$5-15/month
- **Total**: ~$130-180/month (can be reduced with reserved instances)

### Cost Optimization Strategies
1. Use EC2 Reserved Instances for 30-50% savings
2. Start with MongoDB Atlas M0 (free tier)
3. Implement request caching to reduce API calls
4. Use CloudFront CDN for static content
5. Monitor and optimize API usage patterns

## Phase 7: Scaling Considerations

### Horizontal Scaling
- Use Auto Scaling Groups with multiple EC2 instances
- Implement session-based load balancing
- Consider containerization with ECS or EKS

### Performance Optimization
- Implement Redis for caching frequent queries
- Use CloudFront CDN for global content delivery
- Optimize database queries and indexing
- Implement connection pooling

## Security Considerations

### Application Security
- Environment variables for all secrets
- HTTPS enforcement
- CORS properly configured
- Input validation and sanitization
- Rate limiting implementation

### Infrastructure Security
- VPC with private subnets
- Security groups with minimal access
- Regular security updates
- WAF implementation (optional)
- Monitoring and alerting

## Rollback Plan

### If Deployment Fails
1. Revert DNS to point to old system
2. Restore database from backup
3. Debug issues on staging environment
4. Redeploy with fixes

### Emergency Procedures
- Keep old system running during initial deployment
- Implement health checks and automatic failover
- Document all configuration changes
- Maintain backup of working configuration

---

## Quick Start Commands

```bash
# 1. Launch EC2 instance and SSH in
ssh -i your-key.pem ubuntu@your-ec2-ip

# 2. Run setup script
wget https://raw.githubusercontent.com/your-repo/deploy/setup.sh
chmod +x setup.sh && ./setup.sh

# 3. Deploy application
git clone https://github.com/your-repo/holowellness-chatbot.git
cd holowellness-chatbot
./deploy.sh

# 4. Start services
sudo systemctl start holowellness
sudo systemctl start nginx

# 5. Install SSL certificate
sudo certbot --nginx -d your-domain.com
```

This deployment plan provides a comprehensive roadmap for migrating your HoloWellness chatbot to AWS with professional-grade infrastructure and monitoring capabilities.