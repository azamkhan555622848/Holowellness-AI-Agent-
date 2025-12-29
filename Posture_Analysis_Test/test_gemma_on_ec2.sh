#!/bin/bash
# Simple test script to run ON the Gemma RAG EC2 instance
# Tests the service with a small sample query (no images)

GEMMA_RAG_URL="http://127.0.0.1:9000/v1/rag/query"

echo "=========================================="
echo "Testing Gemma RAG Service on EC2"
echo "=========================================="
echo "Endpoint: $GEMMA_RAG_URL"
echo ""

# Test 1: Health check
echo "1. Health Check"
echo "----------------------------------------"
curl -s http://127.0.0.1:9000/health | python3 -m json.tool || echo "Health check failed"
echo ""
echo ""

# Test 2: Simple query without image/metrics
echo "2. Simple Text Query (No Image)"
echo "----------------------------------------"
curl -X POST "$GEMMA_RAG_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is good posture?",
    "history": [],
    "translate": false,
    "top_k": 3
  }' | python3 -c "import json,sys; data=json.load(sys.stdin); print('Content:', data.get('content', 'No content')[:200]); print('Sources:', len(data.get('sources', [])))" 2>/dev/null || echo "Query failed"
echo ""
echo ""

# Test 3: Query with metrics (no image)
echo "3. Query with Sample Metrics (No Image)"
echo "----------------------------------------"
curl -X POST "$GEMMA_RAG_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze my posture based on these measurements",
    "history": [],
    "translate": true,
    "top_k": 3,
    "metrics": {
      "cervical_lateral_shift": {
        "value": 3.1,
        "unit": "%",
        "class": 1,
        "label": "Cervical lateral shift"
      },
      "pelvic_obliquity": {
        "value": 2.6,
        "unit": "deg",
        "class": 0,
        "label": "Pelvic obliquity"
      }
    }
  }' | python3 -c "import json,sys; data=json.load(sys.stdin); print('Content:', data.get('content', 'No content')[:300]); print('Sources:', len(data.get('sources', [])))" 2>/dev/null || echo "Query with metrics failed"
echo ""
echo ""

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. If all tests pass, configure nginx to expose the service"
echo "2. Or open port 9000 in security group"
echo "3. Then test from your local machine"

