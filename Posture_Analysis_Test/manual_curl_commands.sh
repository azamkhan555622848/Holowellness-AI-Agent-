#!/bin/bash
# Manual curl commands for testing Gemma RAG with posture analysis
# You can copy and paste these commands one by one to test each view

# Set your Gemma RAG service URL
GEMMA_RAG_URL="${GEMMA_RAG_URL:-http://localhost:8000/v1/rag/query}"

echo "=========================================="
echo "Manual curl test commands"
echo "=========================================="
echo ""
echo "Gemma RAG URL: $GEMMA_RAG_URL"
echo ""
echo "Run these commands one by one:"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  TEST FRONT VIEW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat << 'EOF'
# Encode front image
FRONT_IMAGE=$(base64 -w 0 front_b27a3c9f_clinical.png 2>/dev/null || base64 -i front_b27a3c9f_clinical.png | tr -d '\n')

# Extract front metrics
FRONT_METRICS=$(python3 -c "
import json
with open('test.txt') as f:
    data = json.load(f)
print(json.dumps(data['metrics_by_view']['front']))
")

# Send request for front view
curl -X POST http://localhost:8000/v1/rag/query \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Please analyze my frontal posture based on these measurements. What do you notice?\",
    \"history\": [],
    \"translate\": true,
    \"top_k\": 5,
    \"metrics\": $FRONT_METRICS,
    \"image_base64\": \"$FRONT_IMAGE\"
  }" \
  | python3 -m json.tool > front_response.json

# View the response
echo "✅ Response saved to front_response.json"
cat front_response.json | python3 -c "import json,sys; print(json.load(sys.stdin)['content'])"
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  TEST LEFT VIEW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat << 'EOF'
# Encode left image
LEFT_IMAGE=$(base64 -w 0 left_a1b6ab98_clinical.png 2>/dev/null || base64 -i left_a1b6ab98_clinical.png | tr -d '\n')

# Extract left metrics
LEFT_METRICS=$(python3 -c "
import json
with open('test.txt') as f:
    data = json.load(f)
print(json.dumps(data['metrics_by_view']['left']))
")

# Send request for left view
curl -X POST http://localhost:8000/v1/rag/query \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Please analyze my left side posture. What can you tell me about my alignment?\",
    \"history\": [],
    \"translate\": true,
    \"top_k\": 5,
    \"metrics\": $LEFT_METRICS,
    \"image_base64\": \"$LEFT_IMAGE\"
  }" \
  | python3 -m json.tool > left_response.json

# View the response
echo "✅ Response saved to left_response.json"
cat left_response.json | python3 -c "import json,sys; print(json.load(sys.stdin)['content'])"
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  TEST RIGHT VIEW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cat << 'EOF'
# Encode right image
RIGHT_IMAGE=$(base64 -w 0 right_3a65a04f_clinical.png 2>/dev/null || base64 -i right_3a65a04f_clinical.png | tr -d '\n')

# Extract right metrics
RIGHT_METRICS=$(python3 -c "
import json
with open('test.txt') as f:
    data = json.load(f)
print(json.dumps(data['metrics_by_view']['right']))
")

# Send request for right view
curl -X POST http://localhost:8000/v1/rag/query \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Please analyze my right side posture. Are there any concerns?\",
    \"history\": [],
    \"translate\": true,
    \"top_k\": 5,
    \"metrics\": $RIGHT_METRICS,
    \"image_base64\": \"$RIGHT_IMAGE\"
  }" \
  | python3 -m json.tool > right_response.json

# View the response
echo "✅ Response saved to right_response.json"
cat right_response.json | python3 -c "import json,sys; print(json.load(sys.stdin)['content'])"
EOF

echo ""
echo "=========================================="
echo "📋 Quick Summary"
echo "=========================================="
echo ""
echo "After running all commands, view results:"
echo ""
echo "  cat front_response.json | jq -r '.content'"
echo "  cat left_response.json | jq -r '.content'"
echo "  cat right_response.json | jq -r '.content'"
echo ""

