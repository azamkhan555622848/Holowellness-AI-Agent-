import os
import json
import hashlib
from typing import Dict

import boto3


def _s3_client():
    return boto3.client("s3")


def _config():
    # Accept multiple env var names for bucket for compatibility with Lambda deploys
    bucket = os.getenv("S3_CACHE_BUCKET") or os.getenv("RAG_S3_BUCKET") or os.getenv("S3_BUCKET")
    prefix = os.getenv("S3_CACHE_PREFIX", "cache/current/")
    delete_local = os.getenv("S3_CACHE_DELETE_LOCAL", "true").lower() == "true"
    return bucket, prefix.rstrip("/") + "/", delete_local


def _enabled() -> bool:
    bucket, _, _ = _config()
    return bool(bucket)


def _sha256_file(path: str) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _manifest_key(prefix: str) -> str:
    return f"{prefix}manifest.json"


def _keys(prefix: str) -> Dict[str, str]:
    # Primary artifacts; vector index is optional and may be absent
    return {
        "documents": f"{prefix}documents.pkl.gz",
        "bm25": f"{prefix}bm25_index.pkl",
        "faiss": f"{prefix}vector_index.faiss",
    }


def _local_paths(rag) -> Dict[str, str]:
    return {
        "documents": rag.docs_cache,
        "bm25": rag.bm25_cache,
        "faiss": rag.vector_cache,
    }


def try_download_caches(rag) -> bool:
    """Attempt to download caches from S3 if manifest matches current config.
    Returns True if caches were successfully downloaded; False otherwise.
    """
    if not _enabled():
        return False
    bucket, prefix, _ = _config()
    s3 = _s3_client()

    # Read manifest if present; be tolerant of schema differences
    manifest = {}
    try:
        obj = s3.get_object(Bucket=bucket, Key=_manifest_key(prefix))
        manifest = json.loads(obj["Body"].read().decode("utf-8"))
    except Exception:
        manifest = {}

    keys = _keys(prefix)
    paths = _local_paths(rag)
    os.makedirs(os.path.dirname(paths["documents"]), exist_ok=True)

    # Download available artifacts; vector index is optional
    ok = False
    # Always try documents and bm25
    for name in ("documents", "bm25"):
        key = keys[name]
        dest = paths[name]
        try:
            s3.download_file(bucket, key, dest)
            ok = True
        except Exception:
            # If either is missing, keep going; we'll fall back to local build
            pass

    # Try vector index (FAISS) if present; ignore if missing
    try:
        s3.download_file(bucket, keys["faiss"], paths["faiss"])
        ok = True
    except Exception:
        pass

    return ok


def try_upload_caches(rag) -> bool:
    """Upload local caches to S3 and write manifest. Optionally delete local files."""
    if not _enabled():
        return False
    bucket, prefix, delete_local = _config()
    s3 = _s3_client()

    keys = _keys(prefix)
    paths = _local_paths(rag)

    # Build manifest with checksums and config
    manifest = {
        "config": {
            "embeddings_model": rag.embeddings_model_name,
            "chunk_size": rag.chunk_size,
            "chunk_overlap": rag.chunk_overlap,
        },
        "files": {},
    }

    for name in ("documents", "bm25", "faiss"):
        local_path = paths[name]
        if not os.path.exists(local_path):
            continue
        s3.upload_file(local_path, bucket, keys[name])
        try:
            manifest["files"][name] = {
                "sha256": _sha256_file(local_path),
                "size": os.path.getsize(local_path),
                "key": keys[name],
            }
        except Exception:
            pass

    # Write manifest
    body = json.dumps(manifest).encode("utf-8")
    s3.put_object(Bucket=bucket, Key=_manifest_key(prefix), Body=body, ContentType="application/json")

    # Optionally delete local caches to save space
    if delete_local:
        for name in ("documents", "bm25", "faiss"):
            p = paths[name]
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
    return True


