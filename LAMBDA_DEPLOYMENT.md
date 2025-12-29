# Professional Lambda-based RAG Indexing Deployment

## Overview

This solution offloads heavy document processing from your EC2 instance to AWS Lambda, solving disk space issues while maintaining professional-grade reliability and monitoring.

## Architecture Benefits

✅ **Cost Effective**: ~$0/month (free tier) vs $60/month for larger EC2
✅ **Scalable**: Handles unlimited document sizes in Lambda /tmp
✅ **Reliable**: Professional error handling and retry logic
✅ **Monitored**: CloudWatch logging and X-Ray tracing
✅ **Fast**: No local disk I/O bottlenecks

## Deployment Steps

### 🚀 Automated GitHub Actions Deployment (Recommended)

Since you have AWS Lambda Full Access permissions configured, deployment is fully automated:

```bash
# 1. Commit and push your changes
git add .
git commit -m "Add Lambda-based RAG indexing to solve disk space issues"
git push origin master

# 2. GitHub Actions will automatically:
#    - Build Lambda deployment package
#    - Create/update Lambda function
#    - Deploy EC2 application updates
#    - Test Lambda function

# 3. Monitor deployment
# Go to: https://github.com/your-username/Holowellness_Chatbot_version_1.0/actions
```

### 🔧 Manual Deployment (Alternative)

If you prefer manual deployment:

```bash
# 1. Deploy Lambda Function
cd lambda/
chmod +x build_package.sh deploy.sh
./deploy.sh

# 2. Deploy EC2 application
./deploy/deploy-app.sh
```

### ✅ Verify Deployment

After GitHub Actions completes:

```bash
# Check Lambda function exists
aws lambda get-function --function-name holowellness-rag-indexer

# Test Lambda endpoint
curl -X POST http://your-ec2-ip/api/rag/reindex-lambda \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 4. Test Lambda Indexing

```bash
# Test the new Lambda endpoint
curl -X POST http://your-ec2-ip/api/rag/reindex-lambda \
  -H "Content-Type: application/json" \
  -d '{}'

# Monitor progress
curl -s http://your-ec2-ip/api/rag/status | jq '.'
```

## Usage

### Automatic Failover

The system provides intelligent failover:

1. **Primary**: Lambda indexing (if enabled)
2. **Fallback**: Local EC2 indexing (if Lambda fails)
3. **Graceful**: Always returns meaningful errors

### Manual Control

```bash
# Use Lambda indexing (recommended)
curl -X POST /api/rag/reindex-lambda

# Use local indexing (legacy)
curl -X POST /api/rag/reindex

# Check status
curl -X GET /api/rag/status
```

### Environment Flags

```bash
# Enable Lambda indexing
USE_LAMBDA_INDEXING=true

# Disable for testing (uses local)
USE_LAMBDA_INDEXING=false
```

## Monitoring & Troubleshooting

### CloudWatch Logs

```bash
# View Lambda logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/holowellness

# Tail logs
aws logs tail /aws/lambda/holowellness-rag-indexer --follow
```

### Performance Metrics

```bash
# Check Lambda performance
aws lambda get-function --function-name holowellness-rag-indexer
aws cloudwatch get-metric-statistics --namespace AWS/Lambda
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Function not found" | Deploy Lambda function first |
| "Invalid user_id" | Update request format |
| "No space left" | Lambda should handle this |
| Timeout | Increase Lambda timeout (max 15min) |

## Cost Optimization

### Free Tier Usage

- **Lambda**: 1M requests/month FREE
- **S3**: 5GB storage FREE  
- **CloudWatch**: Basic logging FREE

### Estimated Costs

| Component | Monthly Cost |
|-----------|--------------|
| Lambda executions | $0.00 (under free tier) |
| S3 storage | $0.00 (under 5GB) |
| Data transfer | $0.00 (minimal) |
| **Total** | **$0.00** |

## Security

### IAM Permissions

Lambda function has minimal required permissions:
- S3: GetObject, PutObject, ListBucket  
- CloudWatch: CreateLogGroup, PutLogEvents
- X-Ray: PutTraceSegments

### Best Practices

✅ No hardcoded credentials
✅ Least privilege IAM roles
✅ Encrypted S3 storage
✅ VPC isolation (optional)
✅ Request validation

## Backup Strategy

### Automatic S3 Backup

Lambda automatically uploads:
- Vector indexes → S3
- Document cache → S3  
- Manifest metadata → S3

### Recovery Process

```bash
# If Lambda fails, EC2 can download existing cache
curl -X POST /api/rag/download-cache

# Manual S3 restore
aws s3 sync s3://holowellness/cache/current/ ./cache/
```

## Migration Path

### Phase 1: Parallel Deployment
- Deploy Lambda alongside existing system
- Test with `/api/rag/reindex-lambda`
- Verify document retrieval works

### Phase 2: Switch Default
- Set `USE_LAMBDA_INDEXING=true`
- Monitor for 24 hours
- Keep local indexing as fallback

### Phase 3: Cleanup
- Remove local indexing complexity
- Optimize EC2 instance size
- Clean up unnecessary dependencies

## Support

### Logs to Check

1. **Lambda Logs**: CloudWatch → `/aws/lambda/holowellness-rag-indexer`
2. **EC2 Logs**: `journalctl -u holowellness -f`  
3. **S3 Access**: CloudTrail (if enabled)

### Key Metrics

- Lambda Duration: < 900 seconds
- Memory Usage: < 3008 MB
- S3 Upload Size: ~100-500 MB
- Document Count: Should match PDF count

This professional implementation solves your disk space crisis while providing enterprise-grade reliability and monitoring.