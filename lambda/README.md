# Lambda-based RAG Indexing

## Overview

This directory contains AWS Lambda function for offloading heavy document processing from EC2 to Lambda, solving disk space issues while maintaining professional reliability.

## Files

- `rag_indexer.py` - Main Lambda function with professional error handling
- `lambda_client.py` - EC2 integration client (located in ../backend/)
- `requirements.txt` - Optimized Lambda dependencies
- `build_package.sh` - Professional deployment package builder
- `deploy.sh` - Complete deployment automation

## Features

✅ **Professional Architecture**: Enterprise-grade error handling and monitoring
✅ **Memory Optimized**: Batched processing with resource monitoring
✅ **Free Tier Compatible**: $0/month cost using AWS free tier
✅ **Automatic Deployment**: Integrated with GitHub Actions
✅ **S3 Integration**: Downloads PDFs, uploads cache automatically

## How It Works

1. **Trigger**: EC2 calls `/api/rag/reindex-lambda` endpoint
2. **Lambda Processing**: Downloads PDFs from S3, processes in 10GB /tmp
3. **Upload Results**: Uploads vector indexes back to S3
4. **EC2 Integration**: Downloads fresh cache from S3

## Usage

### Automatic (GitHub Actions)
```bash
git push origin master
# Lambda function automatically deployed and updated
```

### Manual Testing
```bash
# Test Lambda function directly
aws lambda invoke \
  --function-name holowellness-rag-indexer \
  --payload '{}' \
  response.json

# Test via EC2 endpoint
curl -X POST http://your-ec2-ip/api/rag/reindex-lambda
```

## Configuration

Environment variables set automatically by GitHub Actions:

- `S3_BUCKET=holowellness`
- `S3_PDFS_PREFIX=rag_pdfs/`
- `S3_CACHE_PREFIX=cache/current/`
- `BATCH_SIZE=3`
- `MAX_MEMORY_MB=2800`

## Monitoring

### CloudWatch Logs
```bash
aws logs tail /aws/lambda/holowellness-rag-indexer --follow
```

### Function Status
```bash
aws lambda get-function --function-name holowellness-rag-indexer
```

## Cost Optimization

- **Lambda**: FREE (under 1M requests/month)
- **S3**: FREE (under 5GB storage)
- **Processing Time**: ~2-5 minutes per reindex
- **Total Monthly Cost**: $0.00

This solution eliminates the "No space left on device" errors while providing enterprise-grade reliability and monitoring.