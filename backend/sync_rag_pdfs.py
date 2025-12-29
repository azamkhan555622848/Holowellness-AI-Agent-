import boto3
import os

# Configuration via environment variables
# - RAG_S3_BUCKET: S3 bucket name (default: holowellness)
# - RAG_S3_PREFIX: folder prefix to look for PDFs (default: '')
# - AWS credentials/region are taken from the default boto3 credential chain

S3_BUCKET = os.getenv("RAG_S3_BUCKET", "holowellness")
S3_PREFIX = os.getenv("RAG_S3_PREFIX", "")  # e.g. 'rag_pdfs/' or '' for bucket root
DEST_DIR = os.path.join(os.path.dirname(__file__), "pdfs")  # Backend's pdfs folder

# Use default credential chain (env vars, instance profile, etc.)
s3 = boto3.client("s3")

def sync_pdfs_from_s3() -> None:
    os.makedirs(DEST_DIR, exist_ok=True)
    s3_files = set()

    paginator = s3.get_paginator("list_objects_v2")
    print(f"Syncing PDFs from s3://{S3_BUCKET}/{S3_PREFIX} -> {DEST_DIR}")

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".pdf"):
                continue
            filename = os.path.basename(key)
            if not filename:
                continue
            s3_files.add(filename)
            dest_path = os.path.join(DEST_DIR, filename)
            if not os.path.exists(dest_path) or os.path.getsize(dest_path) != obj.get("Size", 0):
                print(f"Downloading {key} -> {dest_path}")
                s3.download_file(S3_BUCKET, key, dest_path)

    # Delete local PDFs not in S3 under the given prefix
    local_files = {f for f in os.listdir(DEST_DIR) if f.lower().endswith(".pdf")}
    files_to_delete = local_files - s3_files
    for filename in files_to_delete:
        local_path = os.path.join(DEST_DIR, filename)
        print(f"Deleting local file not in S3 prefix: {filename}")
        try:
            os.remove(local_path)
        except FileNotFoundError:
            pass

    # Also remove any old vector caches so the app can rebuild fresh
    cache_dir = os.path.join(os.path.dirname(__file__), "cache")
    for fname in ("vector_index.faiss", "documents.pkl", "bm25_index.pkl"):
        fpath = os.path.join(cache_dir, fname)
        if os.path.exists(fpath):
            print(f"Deleting old cache file: {fpath}")
            try:
                os.remove(fpath)
            except Exception as e:
                print(f"Warning: could not delete {fpath}: {e}")

if __name__ == "__main__":
    print("Syncing PDFs from S3...")
    sync_pdfs_from_s3()
    print("Done! All PDFs are synced to the 'pdfs' folder.")
