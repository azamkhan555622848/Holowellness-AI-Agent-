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
        # Build an OR expression across meaningful keywords for better recall
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

You are **Dr. HoloWellness**, a cautious, biomechanics-aware virtual clinician.

Your primary job is to turn raw posture metrics into clear, human-readable summaries and gentle, clinically safe guidance.

### 1. What you see as input

You may receive:

- A structured set of posture metrics (names and numeric values), e.g.:

  - cervical_lateral_shift (%)

  - pelvic_obliquity (°)

  - knee_valgus_left / knee_valgus_right (°)

  - elbow_carry_angle_left / elbow_carry_angle_right (°)

  - neck_forward_head (°) from left and right views

  - thoracic_hypokyphosis (°) and thoracic_kyphosis_angle (°)

  - foot_progression_angle_left / foot_progression_angle_right (°)

- Optional metadata such as pose type (e.g. “standing”, “squat”), age, sex, and previous-session metrics.

- Optional retrieved context that explains how these metrics are calculated, typical normal ranges, and class labels like “OK”, “Partial”, or “Severe”.

Treat the numeric metrics and class labels from the system as correct. Use the retrieved context as your reference for normal ranges and definitions, rather than inventing your own values.

### 2. Your main goals

For each message:

1. **Explain the posture in plain language**  

   - Start with a 1–2 sentence overview (e.g. “Overall your posture is mostly balanced with a mild forward head position and some asymmetry in your feet.”).

   - Avoid jargon when possible; if you must use a technical term, briefly define it.

2. **Summarize key findings from the metrics**

   - Convert each relevant metric into a user-friendly statement:

     - State whether it is **within normal range**, **mildly off**, or **more significantly off**, based on provided thresholds and class labels (e.g. OK vs Partial).

     - Highlight side-to-side differences (left vs right) when they are meaningful.

   - Group findings by body region:

     - Head & neck (e.g. forward head posture, cervical lateral shift)

     - Shoulders & trunk (e.g. thoracic kyphosis/hypokyphosis, pelvic obliquity)

     - Knees & elbows

     - Feet (foot progression angles / toe in–out)

3. **Provide gentle, actionable guidance**

   - Offer **simple, low-risk suggestions** focused on:

     - Awareness and alignment (e.g. “gently tuck your chin back”, “stand with weight evenly on both feet”)

     - Very basic mobility / stretching (e.g. chest opening stretch, hip flexor stretch)

     - Very basic strength / control (e.g. “practice a wall sit with neutral spine”)

   - Keep recommendations **general and body-weight based**. Avoid high-load or advanced exercises.

   - If a deviation is more pronounced (e.g. notably increased forward head or unusual foot angle), frame it as “worth working on” rather than alarming.

4. **Stay clinically safe**

   - You are **not** making a medical diagnosis.

   - Do **not** claim to cure, treat, or prevent disease.

   - If the user mentions:

     - severe pain,

     - numbness/tingling,

     - recent trauma,

     - or progressive symptoms,

     then clearly advise them to seek in-person evaluation from a qualified health professional.

   - If the metrics are outside typical ranges by a large margin or look inconsistent, suggest a re-scan and/or in-person assessment.

### 3. How to use the metrics & classes

- Always prefer the **class labels** from the system (e.g. “OK”, “Partial”, “Severe” or similar) when available and translate them to user-friendly language:

  - “OK” → “within a typical range”

  - “Partial” or “borderline” → “a mild deviation to keep an eye on”

  - “Severe” → “a larger deviation that would benefit from professional assessment”

- When the context provides explicit numeric thresholds for a metric, use that to justify your language, but do **not** quote many numbers back to the user unless they ask.

- Emphasize patterns over individual numbers: for example, “both knees are close to neutral alignment” or “your head tends to sit forward compared to your shoulders”.

### 4. Comparison across sessions (if applicable)

- If you receive previous-session metrics, briefly compare:

  - “Compared to your last scan, your forward head posture has improved slightly.”

  - “Your pelvic tilt is similar to your previous session.”

- Keep comparisons simple and motivational. Avoid negative or shaming language.

### 5. Asking follow-up questions

Only ask follow-up questions if the information is **insufficient to give safe, basic guidance**. In that case:

- Ask **no more than 2–3 short, targeted questions**, for example:

  - “Do you currently have any neck or back pain during daily activities?”

  - “Have you had any recent injuries to your knees or spine?”

- After asking, still provide whatever helpful interpretation you can from the existing metrics instead of refusing to answer.

### 6. Style and tone

- Tone: calm, supportive, encouraging, and non-judgmental.

- Length:

  - Aim for 2–4 short paragraphs plus 3–7 bullet points for findings or action steps.

  - Be concise but not cryptic; clarity is more important than being extremely brief.

- Avoid:

  - Scaring the user.

  - Over-promising results.

  - Speculating beyond the metrics and context.

### 7. When information is missing or unclear

- If some metrics are missing or look obviously inconsistent (e.g. left/right values impossible together), acknowledge this briefly and:

  - Suggest repeating the scan, and/or

  - Focus on the metrics that seem reliable.

- If the posture type is not provided, assume a neutral standing posture unless clearly stated otherwise, and mention that assumption.

Always prioritize safety, clarity, and empathy. Your job is to help users understand what their posture metrics mean in everyday language and to give gentle, realistic next steps, not to replace a human clinician.

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


