#!/bin/bash
# Test Gemma RAG Service with curl - One query at a time
# Sends front, left, and right posture views separately

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
GEMMA_RAG_URL="${GEMMA_RAG_URL:-http://localhost:8000/v1/rag/query}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "🧪 Gemma RAG Multimodal Test (curl)"
echo "=========================================="
echo "📡 Endpoint: $GEMMA_RAG_URL"
echo ""

# Function to encode image to base64
encode_image() {
    local image_file="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        base64 -i "$image_file" | tr -d '\n'
    else
        # Linux
        base64 -w 0 "$image_file"
    fi
}

# Function to extract metrics for a specific view from test.txt
extract_metrics() {
    local view="$1"
    python3 -c "
import json
import sys
with open('test.txt', 'r') as f:
    data = json.load(f)
metrics = data.get('metrics_by_view', {}).get('$view', {})
print(json.dumps(metrics))
" 2>/dev/null || echo "{}"
}

# Function to send a single query
send_query() {
    local view="$1"
    local image_file="$2"
    local query="$3"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}🔍 Testing $view view${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Query: $query"
    echo "🖼️  Image: $image_file"
    
    # Check if image exists
    if [ ! -f "$image_file" ]; then
        echo -e "${RED}❌ Image not found: $image_file${NC}"
        return 1
    fi
    
    # Encode image
    echo "📷 Encoding image to base64..."
    IMAGE_BASE64=$(encode_image "$image_file")
    IMAGE_SIZE=${#IMAGE_BASE64}
    echo "✅ Image encoded: $IMAGE_SIZE bytes"
    
    # Extract metrics
    echo "📊 Extracting metrics for $view view..."
    METRICS=$(extract_metrics "$view")
    
    if [ "$METRICS" = "{}" ]; then
        echo -e "${YELLOW}⚠️  No metrics found for $view view${NC}"
    else
        METRICS_COUNT=$(echo "$METRICS" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
        echo "✅ Extracted $METRICS_COUNT metrics"
    fi
    
    # Build JSON payload
    echo "📦 Building request payload..."
    PAYLOAD=$(cat <<EOF
{
  "query": "$query",
  "history": [],
  "translate": true,
  "top_k": 5,
  "metrics": $METRICS,
  "image_base64": "$IMAGE_BASE64"
}
EOF
)
    
    # Save payload to temp file for curl
    TEMP_FILE=$(mktemp)
    echo "$PAYLOAD" > "$TEMP_FILE"
    
    # Send request
    echo ""
    echo "🚀 Sending request to Gemma RAG service..."
    echo "⏱️  Started at: $(date '+%H:%M:%S')"
    START_TIME=$(date +%s)
    
    RESPONSE=$(curl -s -X POST "$GEMMA_RAG_URL" \
        -H "Content-Type: application/json" \
        -d @"$TEMP_FILE" \
        --max-time 90 \
        -w "\nHTTP_STATUS:%{http_code}\n")
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Clean up temp file
    rm -f "$TEMP_FILE"
    
    # Extract HTTP status
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d':' -f2)
    RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
    
    echo "⏱️  Completed in: ${ELAPSED}s"
    echo ""
    
    # Check response
    if [ "$HTTP_STATUS" = "200" ]; then
        echo -e "${GREEN}✅ Success (HTTP $HTTP_STATUS)${NC}"
        echo ""
        echo "────────────────────────────────────────────────────────"
        echo "📝 RAG Response:"
        echo "────────────────────────────────────────────────────────"
        
        # Pretty print response content
        echo "$RESPONSE_BODY" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('content', 'No content'))
    print()
    print('📚 Context length:', len(data.get('retrieved_context', '')), 'chars')
    print('📖 Sources:', len(data.get('sources', [])), 'documents')
except:
    print(sys.stdin.read())
" 2>/dev/null || echo "$RESPONSE_BODY"
        
        echo "────────────────────────────────────────────────────────"
        
        # Save response to file
        OUTPUT_FILE="${view}_response.json"
        echo "$RESPONSE_BODY" > "$OUTPUT_FILE"
        echo ""
        echo "💾 Full response saved to: $OUTPUT_FILE"
        
        return 0
    else
        echo -e "${RED}❌ Failed (HTTP $HTTP_STATUS)${NC}"
        echo ""
        echo "Error response:"
        echo "$RESPONSE_BODY"
        return 1
    fi
}

# Main test execution
main() {
    # Check dependencies
    echo "🔍 Checking dependencies..."
    
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}❌ curl not found. Please install curl.${NC}"
        exit 1
    fi
    echo "  ✅ curl"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ python3 not found. Please install Python 3.${NC}"
        exit 1
    fi
    echo "  ✅ python3"
    
    if ! command -v base64 &> /dev/null; then
        echo -e "${RED}❌ base64 not found.${NC}"
        exit 1
    fi
    echo "  ✅ base64"
    
    # Check required files
    echo ""
    echo "📋 Checking required files..."
    
    if [ ! -f "test.txt" ]; then
        echo -e "${RED}❌ test.txt not found${NC}"
        exit 1
    fi
    echo "  ✅ test.txt"
    
    declare -A IMAGES=(
        ["front"]="front_b27a3c9f_clinical.png"
        ["left"]="left_a1b6ab98_clinical.png"
        ["right"]="right_3a65a04f_clinical.png"
    )
    
    for view in "${!IMAGES[@]}"; do
        if [ ! -f "${IMAGES[$view]}" ]; then
            echo -e "${RED}❌ ${IMAGES[$view]} not found${NC}"
            exit 1
        fi
        echo "  ✅ ${IMAGES[$view]}"
    done
    
    # Test queries for each view
    declare -A QUERIES=(
        ["front"]="Please analyze my frontal posture based on these measurements. What do you notice?"
        ["left"]="Please analyze my left side posture. What can you tell me about my alignment?"
        ["right"]="Please analyze my right side posture. Are there any concerns?"
    )
    
    # Run tests
    SUCCESS_COUNT=0
    FAIL_COUNT=0
    
    for view in front left right; do
        if send_query "$view" "${IMAGES[$view]}" "${QUERIES[$view]}"; then
            ((SUCCESS_COUNT++))
        else
            ((FAIL_COUNT++))
        fi
        
        # Wait between requests (except after last one)
        if [ "$view" != "right" ]; then
            echo ""
            echo -e "${YELLOW}⏳ Waiting 2 seconds before next request...${NC}"
            sleep 2
        fi
    done
    
    # Summary
    echo ""
    echo "=========================================="
    echo "📊 TEST SUMMARY"
    echo "=========================================="
    echo -e "${GREEN}✅ Successful: $SUCCESS_COUNT/3${NC}"
    
    if [ $FAIL_COUNT -gt 0 ]; then
        echo -e "${RED}❌ Failed: $FAIL_COUNT/3${NC}"
    fi
    
    echo ""
    echo "📁 Response files:"
    for view in front left right; do
        if [ -f "${view}_response.json" ]; then
            echo "  - ${view}_response.json"
        fi
    done
    
    echo ""
    echo "Done! 🎉"
}

# Run main function
main "$@"

