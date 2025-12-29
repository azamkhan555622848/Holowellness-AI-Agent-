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


