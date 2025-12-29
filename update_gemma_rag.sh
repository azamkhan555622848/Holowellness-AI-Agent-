#!/bin/bash
set -e

# Define paths
APP_DIR="/opt/gemma-rag"
BACKUP_DIR="/opt/gemma-rag/backup_$(date +%Y%m%d_%H%M%S)"

echo "🚀 Updating Gemma RAG Service..."

# 1. Backup current key files
echo "📦 Backing up current files to $BACKUP_DIR..."
mkdir -p $BACKUP_DIR
cp $APP_DIR/app/main.py $BACKUP_DIR/
cp $APP_DIR/rag/sqlite_engine.py $BACKUP_DIR/
cp $APP_DIR/.env $BACKUP_DIR/

# 2. Update sqlite_engine.py with multimodal support
echo "📝 Updating sqlite_engine.py..."
cat << 'PYTHON_EOF' > $APP_DIR/"rag/sqlite_engine.py
from __future__ import annotations

import os
import json
import sqlite3
import logging
from typing import Any, Dict, List, Optional

import boto3
import re

from .openrouter_client import OpenRouterClient


logger = logging.getLogger(__name__)


class SQLiteRAG:
    def __init__(
        self,
        *,
        db_path: str,
        index_bucket: Optional[str],
        index_prefix: str,
        sqlite_vec_so_path: str | None,  # unused in BM25-only mode
        openrouter: OpenRouterClient,
        topk: int = None,
        final_topn: int = None,
    ) -> None:
        self.db_path = db_path
        self.index_bucket = index_bucket
        self.index_prefix = index_prefix.rstrip("/") + "/"
        self.openrouter = openrouter
        self.topk = topk or int(os.getenv("RAG_TOPK", "50"))
        self.final_topn = final_topn or int(os.getenv("RAG_FINAL_TOPN", "10"))

        self._ensure_db_local()
        self.conn = self._open_sqlite()

    # ---------- Index bootstrap ----------
    def _ensure_db_local(self) -> None:
        if os.path.exists(self.db_path):
            return
        if not self.index_bucket:
            raise RuntimeError("Index not present and no index bucket configured")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        s3 = boto3.client("s3")
        key = f"{self.index_prefix}rag.sqlite"
        logger.info("Downloading rag.sqlite from s3://%s/%s", self.index_bucket, key)
        s3.download_file(self.index_bucket, key, self.db_path)

    def reload_index(self) -> None:
        if not self.index_bucket:
            raise RuntimeError("No index bucket configured")
        s3 = boto3.client("s3")
        key = f"{self.index_prefix}rag.sqlite"
        logger.info("Reloading rag.sqlite from s3://%s/%s", self.index_bucket, key)
        s3.download_file(self.index_bucket, key, self.db_path)
        try:
            self.conn.close()
        except Exception:
            pass
        self.conn = self._open_sqlite()

    # ---------- SQLite helpers ----------
    def _open_sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return conn

    def _bm25_candidates(self, query: str, k: int) -> List[int]:
        # Build an OR expression across meaningful keywords for broader recall
        tokens = re.findall(r"\w+", query.lower())
        keywords = [t for t in tokens if len(t) >= 3]
        if not keywords:
            return []
        match_expr = " OR ".join(keywords)

        # FTS5 MATCH with OR; inline LIMIT to avoid param near MATCH
        fts_sql = (
            f"SELECT rowid, bm25(docs_fts) AS score FROM docs_fts "
            f"WHERE docs_fts MATCH '{match_expr}' ORDER BY score LIMIT {int(k)}"
        )
        cur = self.conn.execute(fts_sql)
        ids = [r[0] for r in cur.fetchall()]

        # Fallback: LIKE search if FTS returns nothing
        if not ids:
            like_clause = " OR ".join(["text LIKE ?"] * len(keywords))
            like_params = [f"%{t}%" for t in keywords]
            like_sql = f"SELECT id FROM docs WHERE {like_clause} LIMIT {int(k)}"
            cur = self.conn.execute(like_sql, like_params)
            ids = [r[0] for r in cur.fetchall()]

        return ids

    def _fetch_docs(self, ids: List[int]) -> List[Dict[str, Any]]:
        if not ids:
            return []
        placeholders = ",".join(["?"] * len(ids))
        sql = f"SELECT id, text, meta FROM docs WHERE id IN ({placeholders})"
        cur = self.conn.execute(sql, ids)
        out: List[Dict[str, Any]] = []
        for id_, text, meta in cur.fetchall():
            out.append({"id": id_, "text": text, "meta": json.loads(meta) if meta else None})
        return out

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "No relevant documents found."
        formatted: List[str] = []
        total = 0
        max_len = 1500 * 6
        for ch in chunks:
            txt = ch["text"]
            snippet = (txt[:800] + "...") if len(txt) > 800 else txt
            source = ch.get("meta", {}).get("file", "")
            block = f"Source: {source}\n{snippet}"
            if total + len(block) > max_len:
                break
            formatted.append(block)
            total += len(block)
        return "\n\n".join(formatted)

    # ---------- Public API ----------
    def stats(self) -> Dict[str, Any]:
        try:
            cur = self.conn.execute("SELECT COUNT(*) FROM docs")
            (n_docs,) = cur.fetchone()
        except Exception:
            n_docs = 0
        return {"documents": n_docs, "index_bucket": self.index_bucket, "index_prefix": self.index_prefix}

    def generate_answer(
        self,
        *,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        translate: bool = True,
        top_k: int = 5,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        k = max(self.topk, top_k)
        bm25_ids = self._bm25_candidates(query, k)
        final_ids = bm25_ids[: self.final_topn]
        docs = self._fetch_docs(final_ids)

        context = self._format_context(docs)

        sys_prompt = """
**重要：您必須全程使用繁體中文回覆。不可使用英文。**
**IMPORTANT: You MUST respond ENTIRELY in Traditional Chinese (繁體中文). Do NOT use English.**

您是 **何樂威醫師 (Dr. HoloWellness)**，一位謹慎、具備生物力學專業知識的虛擬臨床醫師。

您的主要任務是將原始姿勢數據轉化為清晰、易懂的摘要，並提供溫和、臨床安全的指導建議。

### 1. 您會收到的輸入

您可能會收到：

- 一組結構化的姿勢數據（名稱和數值），例如：
  - cervical_lateral_shift 頸椎側向偏移 (%)
  - pelvic_obliquity 骨盆傾斜 (°)
  - knee_valgus_left / knee_valgus_right 膝外翻左/右 (°)
  - elbow_carry_angle_left / elbow_carry_angle_right 肘關節提攜角左/右 (°)
  - neck_forward_head 頭部前傾 (°) 來自左側和右側視圖
  - thoracic_hypokyphosis 胸椎後凸不足 (°) 和 thoracic_kyphosis_angle 胸椎後凸角度 (°)
  - foot_progression_angle_left / foot_progression_angle_right 足部前進角左/右 (°)

- 可選的元數據，如姿勢類型（如「站立」、「深蹲」）、年齡、性別和先前的測量數據。

- 可選的檢索上下文，解釋這些數據如何計算、典型的正常範圍，以及分類標籤如「OK」、「Partial」或「Severe」。

將系統提供的數值和分類標籤視為正確。使用檢索的上下文作為正常範圍和定義的參考，而不是自行發明數值。

### 2. 您的主要目標

對於每條訊息：

1. **用白話文解釋姿勢**
   - 以1-2句話概述開始（例如：「整體來看，您的姿勢大致平衡，但頭部有些前傾，雙腳有些不對稱。」）
   - 盡量避免專業術語；如果必須使用技術術語，請簡要定義。

2. **總結數據的主要發現**
   - 將每個相關數據轉換為用戶友好的陳述：
     - 說明是否**在正常範圍內**、**輕微偏差**或**明顯偏差**，基於提供的閾值和分類標籤。
     - 當有意義時，強調左右兩側的差異。
   - 按身體區域分組發現：
     - 頭部和頸部（如頭部前傾、頸椎側向偏移）
     - 肩膀和軀幹（如胸椎後凸/後凸不足、骨盆傾斜）
     - 膝蓋和肘部
     - 足部（足部前進角/內八/外八）

3. **提供溫和、可行的指導**
   - 提供**簡單、低風險的建議**，專注於：
     - 姿勢覺察和對齊（如「輕輕收下巴」、「雙腳均勻站立」）
     - 非常基礎的活動度/伸展（如擴胸伸展、髖屈肌伸展）
     - 非常基礎的力量/控制（如「練習靠牆半蹲，保持脊柱中立」）
   - 保持建議**一般化且以自身體重為主**。避免高負荷或進階運動。
   - 如果偏差較明顯（如頭部前傾增加或足部角度異常），將其描述為「值得關注改善」而非令人擔憂。

4. **保持臨床安全**
   - 您**不是**在做醫療診斷。
   - **不要**聲稱可以治癒、治療或預防疾病。
   - 如果用戶提到：
     - 嚴重疼痛
     - 麻木/刺痛
     - 近期外傷
     - 或漸進性症狀
     則明確建議他們尋求合格醫療專業人員的現場評估。
   - 如果數據明顯超出典型範圍或看起來不一致，建議重新掃描和/或進行現場評估。

### 3. 如何使用數據和分類

- 始終優先使用系統的**分類標籤**（如「OK」、「Partial」、「Severe」或類似），並將其翻譯為用戶友好的繁體中文：
  - "OK" → 「在正常範圍內」
  - "Partial" 或 "borderline" → 「有輕微偏差，值得留意」
  - "Severe" → 「有較大偏差，建議尋求專業評估」

- 當上下文提供明確的數值閾值時，用它來支持您的說法，但**不要**向用戶引用太多數字，除非他們要求。

- 強調模式而非個別數字：例如「雙膝接近中立位置」或「您的頭部相對於肩膀有前傾的傾向」。

### 4. 跨療程比較（如適用）

- 如果您收到先前療程的數據，簡要比較：
  - 「與上次掃描相比，您的頭部前傾姿勢略有改善。」
  - 「您的骨盆傾斜與上次療程相似。」
- 保持比較簡單且具激勵性。避免負面或羞辱性語言。

### 5. 提問後續問題

僅在資訊**不足以提供安全、基本指導**時才提問。在這種情況下：
- 最多問**2-3個簡短、有針對性的問題**，例如：
  - 「您目前在日常活動中是否有頸部或背部疼痛？」
  - 「您最近是否有膝蓋或脊柱受傷？」
- 提問後，仍然根據現有數據提供任何可能有幫助的解釋，而不是拒絕回答。

### 6. 風格和語氣

- 語氣：冷靜、支持、鼓勵、不批判。
- 長度：
  - 目標是2-4個短段落加上3-7個要點用於發現或行動步驟。
  - 簡潔但不神秘；清晰比極度簡短更重要。
- 避免：
  - 嚇唬用戶。
  - 過度承諾結果。
  - 超出數據和上下文進行推測。

### 7. 當資訊缺失或不清楚時

- 如果某些數據缺失或明顯不一致（如左右值不可能同時存在），簡要承認這一點並：
  - 建議重新掃描，和/或
  - 專注於看起來可靠的數據。
- 如果未提供姿勢類型，假設為中立站姿，除非明確說明否則，並提及該假設。

始終優先考慮安全、清晰和同理心。您的工作是幫助用戶用日常語言理解他們的姿勢數據意味著什麼，並給出溫和、現實的下一步建議，而不是取代人類臨床醫師。

**再次提醒：您的回覆必須全程使用繁體中文。**
"""
        messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]
        if conversation_history:
            for m in conversation_history[-6:]:
                if m.get("content"):
                    messages.append({"role": m.get("role", "user"), "content": m["content"]})

        # Build user content with optional metrics and image (OpenAI-style multimodal content)
        user_parts: List[Dict[str, Any]] = []
        text_blocks: List[str] = [f"Context:\n{context}", f"Question: {query}"]
        if metrics:
            try:
                pretty_metrics = json.dumps(metrics, ensure_ascii=False, indent=2)
            except Exception:
                pretty_metrics = str(metrics)
            text_blocks.insert(1, f"Metrics (from system):\n{pretty_metrics}")
        user_parts.append({"type": "text", "text": "\n\n".join(text_blocks)})
        if image_url:
            user_parts.append({"type": "image_url", "image_url": {"url": image_url}})
        elif image_base64:
            user_parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}})

        if len(user_parts) == 1 and user_parts[0].get("type") == "text":
            messages.append({"role": "user", "content": user_parts[0]["text"]})
        else:
            messages.append({"role": "user", "content": user_parts})

        resp = self.openrouter.chat(messages)
        content = resp.get("message", {}).get("content", "")

        return {
            "content": content,
            "thinking": "",
            "retrieved_context": context,
            "sources": [{"id": d["id"], "meta": d.get("meta")} for d in docs],
            "reranked": False,
        }
PYTHON_EOF

# 3. Update app/main.py to parse new inputs
echo "📝 Updating app/main.py..."
cat << 'PYTHON_EOF' > $APP_DIR/app/main.py
from __future__ import annotations

import os
import logging
from typing import List, Optional, Dict, Any

import orjson
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from rag.sqlite_engine import SQLiteRAG
from rag.openrouter_client import OpenRouterClient

try:
    import sentry_sdk  # type: ignore
    if os.getenv("SENTRY_DSN"):
        sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))
except Exception:
    pass


class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    query: str
    history: Optional[List[Message]] = None
    translate: Optional[bool] = True
    top_k: Optional[int] = 5
    # New: optional multimodal inputs
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    content: str
    thinking: Optional[str] = None
    retrieved_context: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    reranked: Optional[bool] = False


def _json_dumps(v, *, default=None):
    return orjson.dumps(v, default=default).decode()


app = FastAPI()

logger = logging.getLogger("gemma-rag-service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


# Environment-driven configuration
DB_LOCAL_PATH = os.getenv("RAG_SQLITE_PATH", "/opt/gemma-rag/rag.sqlite")
SQLITE_VEC_SO_PATH = os.getenv("SQLITE_VEC_SO_PATH", "/opt/sqlite-vec/sqlite-vec0.so")
INDEX_BUCKET = os.getenv("RAG_INDEX_BUCKET")
INDEX_PREFIX = os.getenv("RAG_INDEX_PREFIX", "indexes/current/")


# Initialize engine and client once
openrouter = OpenRouterClient(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    model=os.getenv("OPENROUTER_MODEL", "google/gemma-2b-it"),
)
rag_engine = SQLiteRAG(
    db_path=DB_LOCAL_PATH,
    index_bucket=INDEX_BUCKET,
    index_prefix=INDEX_PREFIX,
    sqlite_vec_so_path=SQLITE_VEC_SO_PATH,
    openrouter=openrouter,
)


@app.get("/health")
def health():
    try:
        stats = rag_engine.stats()
        return {"status": "ok", **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rag/query", response_model=QueryResponse)
def query(req: QueryRequest):
    if not req.query or not str(req.query).strip():
        raise HTTPException(status_code=400, detail="query is required")
    try:
        result = rag_engine.generate_answer(
            query=req.query,
            conversation_history=[m.model_dump() for m in (req.history or [])],
            translate=bool(req.translate) if req.translate is not None else True,
            top_k=req.top_k or 5,
            image_url=req.image_url,
            image_base64=req.image_base64,
            metrics=req.metrics,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/v1/rag/query failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/rag/reload")
def reload_index():
    try:
        rag_engine.reload_index()
        return {"status": "ok", "message": "Index reloaded"}
    except Exception as e:
        logger.exception("/v1/rag/reload failed")
        raise HTTPException(status_code=500, detail=str(e))
PYTHON_EOF

# 4. Restart service
echo "🔄 Restarting gemma-rag service..."
sudo systemctl restart gemma-rag
sleep 3
systemctl status gemma-rag --no-pager

echo "✅ Gemma RAG Service updated successfully!"

