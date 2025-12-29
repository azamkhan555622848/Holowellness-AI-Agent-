from __future__ import annotations

import os
import boto3


def download_sqlite(db_local_path: str, bucket: str, prefix: str) -> None:
    os.makedirs(os.path.dirname(db_local_path), exist_ok=True)
    key = f"{prefix.rstrip('/')}/rag.sqlite"
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, db_local_path)


def upload_sqlite(db_local_path: str, bucket: str, prefix: str) -> None:
    key = f"{prefix.rstrip('/')}/rag.sqlite"
    s3 = boto3.client("s3")
    s3.upload_file(db_local_path, bucket, key)


