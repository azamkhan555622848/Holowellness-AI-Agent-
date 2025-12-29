RAG S3 Sync Configuration
=========================

The backend can automatically synchronize PDFs from S3 and rebuild the vector indices.

Environment variables:
- RAG_SYNC_ON_START=true|false (default: true)
- RAG_S3_BUCKET (default: holowellness)
- RAG_S3_PREFIX (default: empty; e.g. set to `rag_pdfs/` to read from a folder)

Manual reindex:
- POST /api/rag/reindex

Notes:
- Credentials are resolved using the standard AWS chain (instance profile, env vars, etc.).
- After sync, the app deletes local FAISS/BM25 caches so embeddings are rebuilt with the new PDFs on next startup.

