from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
from typing import List, Dict, Any

import boto3
from PyPDF2 import PdfReader
from docx import Document


def chunk_text(text: str, *, tokens: int = 450, overlap: int = 70) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    step = max(tokens - overlap, 50)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + tokens])
        if chunk:
            chunks.append(chunk)
    return chunks


def extract_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    text = []
    for page in reader.pages:
        try:
            text.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(text)


def extract_docx_bytes(data: bytes) -> str:
    fh = io.BytesIO(data)
    doc = Document(fh)
    return "\n".join(p.text for p in doc.paragraphs)


def build_sqlite(db_path: str, docs: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE docs(id INTEGER PRIMARY KEY, text TEXT NOT NULL, meta JSON);")
    conn.execute("CREATE VIRTUAL TABLE docs_fts USING fts5(text, content='docs', content_rowid='id');")
    # BM25-only: no sqlite-vec table

    cur = conn.cursor()
    for doc in docs:
        text = doc["text"]
        meta = json.dumps(doc.get("meta", {}))
        cur.execute("INSERT INTO docs(text, meta) VALUES (?, ?)", (text, meta))
        rowid = cur.lastrowid
        cur.execute("INSERT INTO docs_fts(rowid, text) VALUES (?, ?)", (rowid, text))
    conn.commit()
    conn.close()


def load_docs_from_s3(bucket: str, prefix: str) -> List[Dict[str, Any]]:
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    out: List[Dict[str, Any]] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not (key.lower().endswith(".pdf") or key.lower().endswith(".docx")):
                continue
            data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            if key.lower().endswith(".pdf"):
                text = extract_pdf_bytes(data)
            else:
                text = extract_docx_bytes(data)
            for chunk in chunk_text(text):
                out.append({"text": chunk, "meta": {"file": os.path.basename(key)}})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-bucket", required=True)
    ap.add_argument("--docs-prefix", required=True)
    ap.add_argument("--out-bucket", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--local", default="/tmp/rag.sqlite")
    args = ap.parse_args()

    docs = load_docs_from_s3(args.docs_bucket, args.docs_prefix)
    build_sqlite(args.local, docs)

    s3 = boto3.client("s3")
    out_key = f"{args.out_prefix.rstrip('/')}/rag.sqlite"
    s3.upload_file(args.local, args.out_bucket, out_key)
    print(f"Uploaded to s3://{args.out_bucket}/{out_key}")


if __name__ == "__main__":
    main()


