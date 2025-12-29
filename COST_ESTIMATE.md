## HoloWellness Chatbot – Production Cost Estimate (expanded)

Assumptions (editable)
- Region: ap-northeast-3 (Osaka)
- Runtime: 30 days/month
- Messages per user per day: 10
- Avg tokens per interaction (prompt + response): 800
- S3 storage used: 10 GB; Egress to Internet: 30 GB/month (~1 GB/day)
- Scenarios: 100 and 200 active users (proxy for concurrency)
- Pricing placeholders (verify with your account/provider):
  - gpt-oss-20b: $10 per 1M tokens ($0.01/1K)
  - gpt-oss-120b: $20 per 1M tokens ($0.02/1K)
  - meta-llama/llama-3.1-8b-instruct: $0.20 per 1M ($0.0002/1K)
  - qwen/qwen2.5-7b-instruct: $0.15 per 1M ($0.00015/1K)
  - deepseek/deepseek-r1-distill-qwen-14b: $0.60 per 1M ($0.0006/1K)
  - mistralai/mistral-7b-instruct: $0.30 per 1M ($0.0003/1K)
  - mistralai/mixtral-8x7b-instruct: $2.00 per 1M ($0.002/1K)

Notes
- “AWS = free tier” means EC2 cost = $0 if eligible; otherwise see Upgrade sections below.
- API spend is driven by total tokens, not peak concurrency.

Token math
- Tokens per user per month = 800 × 10 × 30 = 240,000
- For N users: monthly tokens = 240,000 × N
  - 100 users → 24,000,000 tokens (24M)
  - 200 users → 48,000,000 tokens (48M)

EC2 (on‑demand, Linux, estimates)
- t3.small ≈ $0.0264/hour → ~$19/month
- t3.medium ≈ $0.0528/hour → ~$38/month

Other AWS
- S3 Standard 10 GB → ~$0.23/month
- Data transfer out 30 GB (first 1 GB free, $0.09/GB thereafter) → ~$2.61/month

---

### API cost by model (24M / 48M tokens per month)

| Model | Price per 1M | 24M tokens | 48M tokens |
|---|---:|---:|---:|
| meta-llama/llama-3.1-8b-instruct | $0.20 | $4.80 | $9.60 |
| qwen/qwen2.5-7b-instruct | $0.15 | $3.60 | $7.20 |
| mistralai/mistral-7b-instruct | $0.30 | $7.20 | $14.40 |
| deepseek/deepseek-r1-distill-qwen-14b | $0.60 | $14.40 | $28.80 |
| mistralai/mixtral-8x7b-instruct | $2.00 | $48.00 | $96.00 |
| gpt-oss-20b | $10.00 | $240.00 | $480.00 |
| gpt-oss-120b | $20.00 | $480.00 | $960.00 |

> Replace prices with your provider’s current rates; calculations scale linearly.

---

### Totals (Infra + API)

Infra constants
- Free tier infra subtotal: S3 $0.23 + Egress $2.61 = **$2.84**
- Upgrade t3.small subtotal: **$21.84** (adds ~$19 EC2)
- Upgrade t3.medium subtotal: **$40.84** (adds ~$38 EC2)

100 users (24M tokens)
- Free tier totals: add $2.84 to API row
- Upgrade (t3.small): add $21.84 to API row

200 users (48M tokens)
- Free tier totals: add $2.84 to API row
- Upgrade (t3.medium): add $40.84 to API row (more headroom)

Examples
- 100 users, llama‑3.1‑8b: $4.80 + $2.84 = **$7.64/mo** (free tier) or $26.64/mo (t3.small)
- 200 users, deepseek‑r1‑distill‑qwen‑14b: $28.80 + $40.84 = **$69.64/mo** (t3.medium)
- 200 users, gpt‑oss‑120b: $960 + $40.84 = **$1,000.84/mo** (t3.medium)

---

### Cost‑reduction techniques (stackable)

- Retrieval/context trimming
  - Limit context to ~4–6k chars; reduce `final_k` (we set 4). Saves 30–50% tokens.
- Response length control
  - Set max_tokens 400–600 for Q&A. Saves 20–40% tokens.
- Two‑stage model routing
  - Default to 7B/8B; promote to bigger (14B/70B/120B) only when needed. Saves 60–85% on average.
- Response caching
  - Cache by normalized question + top‑k doc IDs + model. 70–90% hit rate on FAQ → near‑zero cost for repeats.
- Quantized/self‑hosted fallback
  - For heavy traffic, serve a local 7B/8B (GGUF/Q4/GPTQ/EXL2) with llama.cpp or vLLM. API spend → $0; infra only.

---

### Self‑hosting (optional, no per‑token fees)

Baseline GPU node (examples)
- g5.2xlarge (~$1.0/h) → ~$720/mo; with 20% overhead → **~$864/mo**
- Can serve 7B/8B efficiently (vLLM/AWQ) or 14B with lower throughput; add autoscaling for peaks.

CPU‑only (very low throughput, for dev)
- t3.medium ~$38/mo; run 7B GGUF Q4 via llama.cpp; acceptable for small internal loads.

When to choose self‑hosting
- High monthly tokens (e.g., 500M+) where API > GPU infra; need strict data residency; or want consistent latency.

---

### How to adapt this sheet
- CostAPI = (Users × msgs/day × tokens/interaction × 30 ÷ 1,000,000) × price_per_1M.
- Swap instance types; monthly ≈ hourly_price × 720.
- Scale S3 and egress linearly with actual usage.




# Add/ensure in override: RAG_SYNC_ON_START=true
sudo mkdir -p /etc/systemd/system/holowellness.service.d
sudo bash -lc 'cat >/etc/systemd/system/holowellness.service.d/override.conf <<EOF
[Service]
Environment=RAG_SYNC_ON_START=true
EOF'

sudo systemctl daemon-reload
sudo systemctl restart holowellness