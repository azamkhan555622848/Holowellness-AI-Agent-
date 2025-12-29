# Test Lambda-based RAG Indexing

## Current Problem
Your RAG indexing failed (500 error) due to EC2 disk space issues, resulting in "No relevant documents found" for medical queries like hip injury recovery.

## Solution: Lambda-based Indexing

### 1. Test Lambda Function Directly
```bash
# Test the deployed Lambda function
aws lambda invoke \
  --function-name holowellness-rag-indexer \
  --payload '{"test": true}' \
  lambda-test-response.json

# Check response
cat lambda-test-response.json
```

### 2. Trigger Lambda RAG Indexing via EC2 API
```bash
# Replace YOUR_EC2_IP with your actual EC2 public IP
export EC2_IP="YOUR_EC2_IP"

# Test health endpoint first
curl -s http://$EC2_IP/health | jq '.'

# Check current RAG status (should show broken state)
curl -s http://$EC2_IP/api/rag/status | jq '.'

# Trigger Lambda-based reindexing (this will rebuild your document cache)
curl -X POST http://$EC2_IP/api/rag/reindex-lambda \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.'

# Monitor progress (run this every 30 seconds)
curl -s http://$EC2_IP/api/rag/status | jq '.'
```

### 3. Test Medical Query After Reindexing
```bash
# Test hip injury query that previously failed
curl -X POST http://$EC2_IP/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have hip injury what do you suggest for speedy recovery",
    "user_id": "test_user"
  }' | jq '.'
```

## Expected Results

### Before Lambda Reindexing:
- RAG status shows error or empty cache
- Medical queries return "No relevant documents found"
- Chat responses lack medical document context

### After Lambda Reindexing:
- RAG status shows successful indexing
- Document count > 0
- Cache size shows indexed content
- Medical queries retrieve relevant documents
- Hip injury query finds orthopedic/rehabilitation content

## Monitoring Lambda Execution

### CloudWatch Logs
```bash
# View Lambda execution logs
aws logs tail /aws/lambda/holowellness-rag-indexer --follow

# Get log groups
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/holowellness
```

### Lambda Function Status
```bash
# Check function configuration
aws lambda get-function --function-name holowellness-rag-indexer

# List recent invocations
aws lambda get-function --function-name holowellness-rag-indexer \
  --query 'Configuration.[LastModified,State,LastUpdateStatus]'
```

## Troubleshooting

### If Lambda Test Fails:
1. Check CloudWatch logs for detailed errors
2. Verify IAM permissions for S3 access
3. Ensure S3 bucket `holowellness` exists with PDFs

### If EC2 API Call Fails:
1. Verify EC2 instance is running
2. Check security groups allow HTTP traffic
3. Confirm `USE_LAMBDA_INDEXING=true` in environment

### If Reindexing is Slow:
- Lambda has 15-minute timeout
- Processing depends on PDF count and size
- Monitor CloudWatch for progress logs

## Success Indicators

✅ Lambda function responds without errors  
✅ `/api/rag/reindex-lambda` returns success  
✅ RAG status shows document_count > 0  
✅ Hip injury query retrieves medical documents  
✅ Chat responses include relevant citations  

## Cost Verification

After successful reindexing:
- Lambda execution: ~5-10 minutes = $0.00 (free tier)
- S3 storage: Medical PDFs + cache = $0.00 (under 5GB)
- **Total cost: $0.00**

Your disk space crisis is solved while maintaining professional medical search quality!