#!/usr/bin/env python3
import os
import time
import PyPDF2
import numpy as np
import requests
import json
import docx
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    PDFMINER_AVAILABLE = True
except Exception:
    PDFMINER_AVAILABLE = False
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

from PIL import Image
import io
import pickle
from pathlib import Path
import gzip
from typing import List, Dict, Tuple, Optional, Any
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import faiss
from dotenv import load_dotenv
import uuid
from datetime import datetime
from datetime import timedelta
import logging
import threading
import time as time_module
import re # Import regex module
# Use OpenRouter API instead of local Ollama
try:
    from openrouter_client import ollama
    print("Using OpenRouter API for LLM calls")
except ImportError:
    import ollama
    print("Using local Ollama (fallback)")
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_path = None
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

load_dotenv()

class RAGSystem:
    def __init__(self, pdf_directory=None, model_name="deepseek/deepseek-r1-distill-qwen-14b", embeddings_model="all-MiniLM-L6-v2", cache_dir="cache", init_embeddings=True, top_k=5):
        """
        Initializes the RAG system with Ollama and OCR capabilities.
        """
        self.pdf_directory = pdf_directory or os.path.join(os.path.dirname(__file__), "pdfs")
        self.model_name = model_name
        self.translator_model = "llama3f1-medical"  # Translation model
        self.embeddings_model_name = embeddings_model
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.chunk_size = 512
        self.chunk_overlap = 50
        self.top_k = top_k
        # Cap the total number of chunks to limit disk/RAM footprint
        try:
            self.max_chunks = int(os.getenv("RAG_MAX_CHUNKS", "3000"))
        except Exception:
            self.max_chunks = 3000

        self.vector_cache = os.path.join(self.cache_dir, "vector_index.faiss")
        # Use gzip to reduce disk usage for large corpora
        self.docs_cache = os.path.join(self.cache_dir, "documents.pkl.gz")
        self.bm25_cache = os.path.join(self.cache_dir, "bm25_index.pkl")
        
        self.embedder = None
        self.vector_store = None
        self.documents = []
        self.bm25_index = None
        
        # Initialize EasyOCR (lazy loading)
        self.ocr_reader = None
        
        if init_embeddings and self.pdf_directory:
            self._load_or_create_embeddings()

    def _init_ocr(self):
        """Initialize OCR reader only when needed"""
        if not EASYOCR_AVAILABLE:
            print("EasyOCR not available - OCR functionality disabled")
            return False
        if self.ocr_reader is None:
            print("Initializing EasyOCR...")
            self.ocr_reader = easyocr.Reader(['en'])  # Add more languages if needed: ['en', 'es', 'fr']
            print("EasyOCR initialized successfully")
        return True

    def _chunk_text(self, text: str) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        return chunks

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Enhanced PDF text extraction with OCR fallback for image-heavy pages
        """
        text = ""
        try:
            # First, try regular text extraction with PyPDF2
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                pages_needing_ocr = []
                
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text and len(page_text.strip()) > 50:  # If substantial text found
                        text += page_text + "\n"
                    else:
                        # Mark page for OCR if little/no text extracted
                        pages_needing_ocr.append(page_num)
                
                # If we have many pages that need OCR and pdfminer is available, try pdfminer full-doc extraction first
                if pages_needing_ocr and PDFMINER_AVAILABLE:
                    try:
                        alt_text = pdfminer_extract_text(file_path) or ""
                        if len(alt_text.strip()) > len(text.strip()):
                            text = alt_text
                            pages_needing_ocr = []  # satisfied using pdfminer
                    except Exception as e:
                        print(f"pdfminer extraction failed for {file_path}: {e}")
                # If still pages need OCR and OCR stack is available
                if pages_needing_ocr:
                    print(f"OCR needed for {len(pages_needing_ocr)} pages in {os.path.basename(file_path)}")
                    ocr_text = self._extract_text_with_ocr(file_path, pages_needing_ocr)
                    text += ocr_text
                
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            # If PyPDF2 fails completely, try pdfminer first, then OCR for entire document
            try:
                if PDFMINER_AVAILABLE:
                    text = pdfminer_extract_text(file_path) or ""
                if not text.strip():
                    print(f"Falling back to OCR for entire document: {os.path.basename(file_path)}")
                    text = self._extract_text_with_ocr(file_path)
            except Exception as ocr_error:
                print(f"OCR also failed for {file_path}: {ocr_error}")
        
        return text

    def _extract_text_with_ocr(self, file_path: str, specific_pages: List[int] = None) -> str:
        """
        Extract text using OCR from PDF pages
        """
        try:
            if not self._init_ocr():  # Initialize OCR if not already done
                return ""  # Return empty string if OCR not available
            
            if not PDF2IMAGE_AVAILABLE:
                print("pdf2image not available - cannot convert PDF to images for OCR")
                return ""
            
            # Convert PDF pages to images
            if specific_pages:
                # Convert only specific pages
                images = convert_from_path(file_path, first_page=min(specific_pages)+1, 
                                         last_page=max(specific_pages)+1)
                # Filter to only the pages we want
                images = [images[i - min(specific_pages)] for i in specific_pages if i - min(specific_pages) < len(images)]
            else:
                # Convert all pages
                images = convert_from_path(file_path)
            
            ocr_text = ""
            for i, image in enumerate(images):
                try:
                    # Use EasyOCR to extract text
                    results = self.ocr_reader.readtext(np.array(image))
                    page_text = " ".join([result[1] for result in results])
                    if page_text.strip():
                        ocr_text += f"Page {i+1} OCR: {page_text}\n"
                except Exception as e:
                    print(f"OCR failed for page {i+1}: {e}")
                    continue
            
            return ocr_text
            
        except Exception as e:
            print(f"OCR extraction failed for {file_path}: {e}")
            return ""

    def _extract_text_from_docx(self, file_path: str) -> str:
        try:
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return ""

    def _process_file(self, file_path: str, source_info: str):
        file_ext = os.path.splitext(file_path)[1].lower()
        text = ""
        
        print(f"Processing: {os.path.basename(file_path)}")
        
        if file_ext == '.pdf':
            text = self._extract_text_from_pdf(file_path)
        elif file_ext == '.docx':
            text = self._extract_text_from_docx(file_path)
        
        if text:
            chunks = self._chunk_text(text)
            added = 0
            for chunk in chunks:
                if len(self.documents) >= self.max_chunks:
                    print(f"Reached max chunks limit ({self.max_chunks}). Stopping ingestion.")
                    break
                self.documents.append({'text': chunk, 'source': source_info, 'file': os.path.basename(file_path)})
                added += 1
            print(f"Extracted {len(chunks)} chunks from {os.path.basename(file_path)} (added {added}, total {len(self.documents)})")

    def _ingest_documents(self):
        print("Processing documents...")
        for root, _, files in os.walk(self.pdf_directory):
            for file in files:
                if len(self.documents) >= self.max_chunks:
                    print(f"Global max chunks limit reached ({self.max_chunks}). Halting ingestion.")
                    return
                self._process_file(os.path.join(root, file), os.path.basename(root))

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Formats the retrieved chunks into a readable context string.
        Limits context size to prevent model hanging.
        """
        if not chunks:
            return "No relevant documents found."
        
        formatted_chunks = []
        total_length = 0
        max_context_length = 20000  # Increased to match Enhanced RAG
        
        for chunk in chunks:
            # Keep chunk size at 800 characters for good balance
            chunk_text = chunk['text'][:800] + "..." if len(chunk['text']) > 800 else chunk['text']
            formatted_chunk = f"Source: {chunk['file']} ({chunk['source']})\n{chunk_text}"
            
            if total_length + len(formatted_chunk) > max_context_length:
                break
                
            formatted_chunks.append(formatted_chunk)
            total_length += len(formatted_chunk)
        
        return "\n\n".join(formatted_chunks)

    def _hybrid_search(self, query: str) -> List[Dict[str, Any]]:
        """
        Performs a hybrid search using both BM25 and FAISS.
        """
        # Return empty results if no documents are available
        if not self.documents:
            print("Warning: No documents available for search")
            return []
        
        # Ensure BM25 index exists; build on demand if missing
        if self.bm25_index is None:
            try:
                tokenized_corpus = [doc['text'].split(" ") for doc in self.documents]
                self.bm25_index = BM25Okapi(tokenized_corpus)
            except Exception as e:
                print(f"Failed to build BM25 on demand: {e}")
            
        vector_results_indices = []
        # Vector search (FAISS) only if vector_store and embedder are available
        if self.vector_store is not None and self.embedder is not None:
            try:
                query_embedding = self.embedder.encode([query])
                D, I = self.vector_store.search(np.array(query_embedding, dtype=np.float32), k=self.top_k)
                vector_results_indices = I[0]
            except Exception as e:
                print(f"Vector search failed or unavailable, falling back to BM25 only: {e}")

        # Keyword search (BM25)
        tokenized_query = query.split(" ")
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_top_n_indices = np.argsort(bm25_scores)[::-1][:self.top_k]

        # Combine results
        combined_indices = list(set(vector_results_indices) | set(bm25_top_n_indices))
        # Preserve order by BM25 score primarily
        combined_indices = sorted(combined_indices, key=lambda idx: bm25_scores[idx] if idx < len(bm25_scores) else -1, reverse=True)
        final_ids = combined_indices[:self.top_k]
        return [self.documents[i] for i in final_ids if i < len(self.documents)]

    def _translate_to_traditional_chinese(self, english_content: str) -> str:
        """Translate English medical response to Traditional Chinese using llama3f1-medical model."""
        translation_prompt = f"""請將以下英文醫療建議翻譯成繁體中文。保持專業的醫療語調，並確保翻譯準確且易於理解：

原文：
{english_content}

繁體中文翻譯："""

        try:
            def call_translator():
                return ollama.chat(
                    model=self.translator_model,
                    messages=[{"role": "user", "content": translation_prompt}],
                    options={
                        "temperature": 0.1,  # Lower temperature for consistent translation
                        "top_p": 0.7,
                        # Allow configuring translation token budget via env; default higher to avoid truncation
                        "num_predict": int(os.getenv("RAG_TRANSLATION_MAX_TOKENS", "1200"))
                    }
                )
            
            # Use ThreadPoolExecutor for timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_translator)
                response = future.result(timeout=60)  # 60 second timeout
                translated_content = response.get('message', {}).get('content', '').strip()
                print(f"Translation complete: {len(translated_content)} characters")
                return translated_content
                
        except FutureTimeoutError as e:
            print(f"Translation timeout: {e}")
            return f"翻譯逾時：{english_content[:200]}..."  # Fallback: return truncated original
        except Exception as e:
            print(f"Translation error: {e}")
            return f"翻譯錯誤：{english_content}"  # Fallback: return original with error note

    def sanitize_output(self, text: str) -> str:
        """Remove chain-of-thought and internal markers from model output."""
        if not text:
            return ""
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'</?think>', '', cleaned).strip()
        sanitized_lines = []
        for line in cleaned.splitlines():
            ls = line.strip()
            if ls.startswith('ROUTING_HINTS:'):
                continue
            if ls.startswith('LONG_TERM_MEMORY:'):
                continue
            if re.match(r'^(Patient|Dr\. HoloWellness):', ls):
                continue
            sanitized_lines.append(line)
        return "\n".join(sanitized_lines).strip()

    def generate_answer(self, query: str, conversation_history: List[Dict[str, str]] = None, override_context: str = None, override_thinking: str = None, translate: bool = True, model: Optional[str] = None) -> Dict[str, str]:
        """
        Generates an answer using two-step pipeline: 
        1. deepseek-r1 for medical content generation (English)
        2. llama3f1-medical for Traditional Chinese translation
        """
        start_time = time.time()
        
        if override_context is not None:
            context = override_context
            internal_thinking = override_thinking if override_thinking else ""
            relevant_chunks = [] 
        else:
            relevant_chunks = self._hybrid_search(query)
            # Topic-aware gating via env hints injected into conversation history (ROUTING_HINTS)
            topic_reset = False
            if conversation_history:
                try:
                    last_sys = [m for m in conversation_history if m.get('role')=='system' and 'ROUTING_HINTS' in (m.get('content') or '')]
                    if last_sys:
                        hints = last_sys[-1].get('content','')
                        topic_reset = 'topic_reset=true' in hints
                except Exception:
                    topic_reset = False
            # If topic reset or query is clearly general, optionally suppress weakly relevant context
            def _looks_general(q: str) -> bool:
                ql = (q or '').lower()
                return any(p in ql for p in [
                    'how can you help', 'what can you do', 'in general',
                    'switch topic', 'new topic', 'change topic', 'talk about something else',
                    'general help', 'help in general'
                ])

            if topic_reset or _looks_general(query):
                # If we found fewer than 2 chunks or total context is tiny, skip RAG context entirely
                if len(relevant_chunks) < 2:
                    relevant_chunks = []
            context = self._format_context(relevant_chunks)
            internal_thinking = f"RAG Analysis:\nQuery: '{query}'\n"
            internal_thinking += f"Found {len(relevant_chunks)} relevant chunks.\n"

        # Build conversation context for prompt (exclude earlier system messages we insert)
        # Build conversation context if available
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            conversation_context = "\n\nPrevious conversation context:\n"
            # Keep a slightly longer window to avoid losing the prior Q/A that was just answered
            window = int(os.getenv("RAG_HISTORY_WINDOW", "10"))
            recent_history = conversation_history[-window:] if len(conversation_history) > window else conversation_history
            for msg in recent_history:
                role = "Patient" if msg.get('role') == 'user' else "Dr. HoloWellness"
                conversation_context += f"{role}: {msg.get('content', '')}\n"

        system_prompt = f"""You are Dr. HoloWellness, an experienced wellness/medical/fitness clinician. You are speaking directly to your patient in a professional consultation.

IMPORTANT: You must respond ONLY in English. Do not use any other language. Keep outputs compact and useful.

POLICY: Use your clinical judgment to decide whether to ask a concise list of follow-up questions first or provide a direct, structured answer immediately. If red flags are present, advise appropriate in-person or urgent care.

FOLLOW-UP QUESTIONS: When you determine more detail is required (e.g., onset, location, quality, severity, aggravating/relieving factors, red flags, past history, medications, functional impact), present 2-4 targeted questions in a clear numbered list so the patient can answer them in the next turn. After collecting sufficient detail, move on to the structured plan.

STRUCTURED ANSWER: When providing a full answer, follow this format concisely: (1) empathetic acknowledgment; (2) brief assessment referencing supplied details; (3) two specific, actionable recommendations; (4) one relevant follow-up question for monitoring or next steps.

DO NOT REPEAT QUESTIONS: If the patient already answered your earlier questions (e.g., they provided onset, location, severity), do not ask those again. Acknowledge the new information and proceed with assessment and guidance. Only ask new, non-duplicative questions if absolutely needed.

DO NOT REVEAL INTERNAL REASONING: Do not include your internal analysis, chain-of-thought, or planning. Do not preface with meta-explanations such as "I'm trying to figure out..." Provide only the patient-facing content.

TONE: Professional, warm, concise, evidence-informed, and safety-aware. Tailor advice to the patient's context (age, activity, conditions, medications). Minimize redundancy across turns.

Context (documents + pinned facts + recent conversation): {context}{conversation_context}

EXAMPLES (abbreviated):
- Direct question example:
  Patient: "Best stretch for tight hamstrings?"
  Doctor: Provide structured answer immediately.

- Intake-first example:
  Patient: "My knee hurts."
  Doctor: Ask 2-3 targeted questions (onset, location, severity) before giving recommendations.

NOW RESPOND: Choose whether to ask follow-ups or provide the structured plan based on the user's message and conversation so far."""

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history and len(conversation_history) > 0:
            # Keep the same window as used for context so the model sees both the Q and the user's answer
            window = int(os.getenv("RAG_HISTORY_WINDOW", "10"))
            recent_messages = conversation_history[-window:] if len(conversation_history) > window else conversation_history
            for msg in recent_messages:
                if msg.get('content'):
                    messages.append({
                        "role": msg.get('role', 'user'),
                        "content": msg.get('content', '')
                    })

        messages.append({"role": "user", "content": query})

        try:
            print("\n--- Step 1: Generating English Response with DeepSeek ---")
            print(f"Context length: {len(context)} characters")
            print(f"Query: {query}")
            print("Calling DeepSeek model...")

            def call_ollama():
                # More generous generation budget and relaxed stops to reduce truncation
                stop_list = ["<think>"]
                if os.getenv("RAG_STRICT_STOPS", "false").lower() == "true":
                    stop_list.extend(["Patient:", "Dr. HoloWellness:", "\n\n\n"])  # optional strict stops
                opts = {
                    "temperature": float(os.getenv("RAG_TEMPERATURE", "0.4")),
                    "top_p": float(os.getenv("RAG_TOP_P", "0.8")),
                    "num_predict": int(os.getenv("RAG_GENERATION_MAX_TOKENS", "900")),
                    "stop": stop_list
                }
                return ollama.chat(
                    model=(model or self.model_name),
                    messages=messages,
                    options=opts
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(call_ollama)
                response = future.result(timeout=90)
                english_content = response.get('message', {}).get('content', '').strip()
                english_content = self.sanitize_output(english_content)

                print(f"English Response: {english_content}")

            if translate:
                print("\n--- Step 2: Translating to Traditional Chinese ---")
                translated_content = self._translate_to_traditional_chinese(english_content)
            else:
                translated_content = english_content

        except FutureTimeoutError as e:
            error_message = f"Model timeout: {e}"
            print(error_message)
            translated_content = f"抱歉，AI模型回應時間過長，請稍後重試。" if translate else "Sorry, the AI model timed out. Please try again shortly."
            internal_thinking += f"\nTimeout Error: {e}"
        except Exception as e:
            error_message = f"Error communicating with Ollama: {e}"
            print(error_message)
            translated_content = f"抱歉，我在連接AI模型時遇到錯誤：{e}" if translate else f"Sorry, I encountered an error communicating with the AI model: {e}"
            internal_thinking += f"\nOllama Error: {e}"
        
        print("--- Two-Step Pipeline Complete ---\n")
        total_time = time.time() - start_time
        logging.info(f"Answer generated in {total_time:.2f} seconds")

        # Format retrieved context for display
        retrieved_context_text = self._format_context(relevant_chunks) if relevant_chunks else "No relevant documents found for this query."
        
        return {
            "thinking": internal_thinking,
            "content": translated_content,
            "retrieved_context": retrieved_context_text,
            "sources": relevant_chunks
        }

    def _load_or_create_embeddings(self):
        """
        Loads embeddings and indices from cache if they exist,
        otherwise creates them from the source documents.
        """
        self.embedder = SentenceTransformer(self.embeddings_model_name)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()

        docs_cache_exists = os.path.exists(self.docs_cache) or os.path.exists(self.docs_cache.replace('.gz', ''))
        if docs_cache_exists and os.path.exists(self.bm25_cache) and os.path.exists(self.vector_cache):
            print("Loading embeddings and indices from cache...")
            # Try gzipped documents first, fallback to plain pickle for backward compatibility
            docs_path = self.docs_cache if os.path.exists(self.docs_cache) else self.docs_cache.replace('.gz', '')
            try:
                if docs_path.endswith('.gz'):
                    with gzip.open(docs_path, 'rb') as f:
                        self.documents = pickle.load(f)
                else:
                    with open(docs_path, 'rb') as f:
                        self.documents = pickle.load(f)
            except Exception as e:
                print(f"Failed to load documents cache {docs_path}: {e}. Proceeding with empty docs.")
                self.documents = []
            with open(self.bm25_cache, 'rb') as f:
                self.bm25_index = pickle.load(f)
            self.vector_store = faiss.read_index(self.vector_cache)
            print(f"Loaded {len(self.documents)} documents from cache.")
        else:
            print("No cache found. Creating new embeddings and indices...")
            self._ingest_documents()
            self._save_embeddings()

    def _save_embeddings(self):
        """
        Creates and saves the embeddings and indices to the cache directory.
        """
        print("Saving embeddings and indices to cache...")
        
        if not self.documents:
            print("Warning: No documents found to create embeddings from.")
            # Create empty indices with default dimensions
            self.vector_store = faiss.IndexFlatL2(self.embedding_dim)
            faiss.write_index(self.vector_store, self.vector_cache)
            
            # Create empty BM25 index with dummy document to avoid division by zero
            self.bm25_index = BM25Okapi([["dummy"]])  # Single dummy document
            with open(self.bm25_cache, 'wb') as f:
                pickle.dump(self.bm25_index, f)
            return
        
        try:
            embeddings = self.embedder.encode([doc['text'] for doc in self.documents])
            embeddings_np = np.array(embeddings, dtype=np.float32)
            
            # Ensure we have valid embeddings
            if embeddings_np.size == 0 or len(embeddings_np.shape) != 2:
                print("Warning: Invalid embeddings created. Using default dimensions.")
                self.vector_store = faiss.IndexFlatL2(self.embedding_dim)
            else:
                self.vector_store = faiss.IndexFlatL2(embeddings_np.shape[1])
                self.vector_store.add(embeddings_np)
            
            faiss.write_index(self.vector_store, self.vector_cache)
        except Exception as e:
            # If saving vector index fails (e.g., ENOSPC), degrade to BM25-only retrieval
            print(f"Failed to build/save vector index, falling back to BM25-only: {e}")
            self.vector_store = None

        tokenized_corpus = [doc['text'].split(" ") for doc in self.documents]
        self.bm25_index = BM25Okapi(tokenized_corpus)
        with open(self.bm25_cache, 'wb') as f:
            pickle.dump(self.bm25_index, f)

        # Save documents compressed to reduce disk footprint
        with gzip.open(self.docs_cache, 'wb') as f:
            pickle.dump(self.documents, f)
            
        print(f"Saved {len(self.documents)} documents and their indices to cache.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
    
    try:
        rag = RAGSystem(PDF_DIR)
        
        while True:
            query = input("\nEnter your question (or 'quit' to exit): ").strip()
            if query.lower() in {"quit", "exit"}:
                break
            
            response = rag.generate_answer(query)
            
            print("\n--- Thinking Process ---")
            print(response["thinking"])
            print("\n--- Final Answer ---")
            print(response["content"])
            if response.get('sources'):
                print("\n--- Sources ---")
                for source in response['sources']:
                    print(f"- {source['file']}")
                    
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True) 