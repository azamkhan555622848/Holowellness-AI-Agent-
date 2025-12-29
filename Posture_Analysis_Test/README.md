# Posture Analysis Test for Gemma RAG (curl-based)

Simple test suite that uses `curl` to send posture analysis queries to your Gemma RAG service.

## Quick Start

### Automated Test (All 3 Views)

```bash
chmod +x test_with_curl.sh
./test_with_curl.sh
```

This will automatically:
- Send front view query with image + metrics
- Send left view query with image + metrics  
- Send right view query with image + metrics
- Save responses to `front_response.json`, `left_response.json`, `right_response.json`

### Manual Testing (Step by Step)

```bash
# Show all curl commands
./manual_curl_commands.sh
```

Then copy and paste each command individually.

## Files

- **test_with_curl.sh** - Automated test runner (sends all 3 queries)
- **manual_curl_commands.sh** - Displays manual curl commands for copy-paste
- **test.txt** - JSON with posture metrics for all views
- **front_b27a3c9f_clinical.png** - Front view image
- **left_a1b6ab98_clinical.png** - Left view image
- **right_3a65a04f_clinical.png** - Right view image

## Configuration

Set custom endpoint:

```bash
export GEMMA_RAG_URL="http://your-server:8000/v1/rag/query"
./test_with_curl.sh
```

## What Gets Sent

Each request contains:

1. **Query** - Natural language question about posture
2. **Metrics** - JSON with posture measurements (angles, percentages, classifications)
3. **Image** - Base64-encoded clinical posture photo
4. **Settings** - `translate: true` (Traditional Chinese), `top_k: 5`

### Example Front View Metrics

```json
{
  "cervical_lateral_shift": {
    "value": 3.1,
    "unit": "%",
    "class": 1,
    "label": "Cervical lateral shift"
  },
  "pelvic_obliquity": {
    "value": 2.6,
    "unit": "deg",
    "class": 0
  },
  "knee_valgus_left": {...},
  "knee_valgus_right": {...}
}
```

## Expected Response

```json
{
  "content": "您的正面姿勢分析如下...",
  "thinking": "",
  "retrieved_context": "Source: posture_guidelines.pdf\n...",
  "sources": [
    {"id": 123, "meta": {"file": "clinical_doc.pdf"}}
  ],
  "reranked": false
}
```

## View Responses

```bash
# View just the content (Traditional Chinese response)
cat front_response.json | jq -r '.content'
cat left_response.json | jq -r '.content'
cat right_response.json | jq -r '.content'

# View full response with metadata
cat front_response.json | jq .
```

## Troubleshooting

### Service not reachable

```bash
# Test health endpoint
curl http://localhost:8000/health

# Check if service is running
ps aux | grep uvicorn
```

### Python not found

The scripts use `python3` to parse JSON. Install if needed:

```bash
# Ubuntu/Debian
sudo apt-get install python3

# macOS
brew install python3
```

### Base64 encoding fails

The script handles both Linux (`base64 -w 0`) and macOS (`base64 -i`) formats automatically.

## Dependencies

- `curl` - HTTP client
- `python3` - For JSON parsing
- `base64` - Image encoding (usually pre-installed)
- `jq` (optional) - For pretty JSON output

## Example Output

```
==========================================
🧪 Gemma RAG Multimodal Test (curl)
==========================================
📡 Endpoint: http://localhost:8000/v1/rag/query

🔍 Checking dependencies...
  ✅ curl
  ✅ python3
  ✅ base64

📋 Checking required files...
  ✅ test.txt
  ✅ front_b27a3c9f_clinical.png
  ✅ left_a1b6ab98_clinical.png
  ✅ right_3a65a04f_clinical.png

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Testing front view
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Query: Please analyze my frontal posture...
🖼️  Image: front_b27a3c9f_clinical.png
📷 Encoding image to base64...
✅ Image encoded: 245678 bytes
📊 Extracting metrics for front view...
✅ Extracted 7 metrics

🚀 Sending request to Gemma RAG service...
⏱️  Started at: 14:23:45
⏱️  Completed in: 4s

✅ Success (HTTP 200)

────────────────────────────────────────────────────────
📝 RAG Response:
────────────────────────────────────────────────────────
您的正面姿勢分析如下：

整體來看，您的姿勢大致保持平衡，但有幾個地方需要注意：

1. **頸椎側向偏移** (3.1%): 
   輕度偏移，略超出理想範圍...

2. **骨盆傾斜** (2.6°): 
   在正常範圍內...

3. **膝關節對齊**:
   - 左膝: 2.1° (輕度外翻)
   - 右膝: 2.3° (輕度外翻)
   ...

📚 Context length: 4523 chars
📖 Sources: 3 documents
────────────────────────────────────────────────────────

💾 Full response saved to: front_response.json
```

---

**Quick test:** `./test_with_curl.sh`

