import os
import pickle
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class RAGGemmaSystem:
    def __init__(self, pdf_dir, init_embeddings=True):
        self.pdf_dir = pdf_dir
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.documents = []
        self.vector_index = None
        self.bm25_index = None
        
        # Load Gemma model and tokenizer
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.llm_tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")
        self.llm_model = AutoModelForCausalLM.from_pretrained(
            "google/gemma-2b-it",
            device_map="auto",
            torch_dtype=torch.bfloat16
        )

        self.cache_dir = "cache"
        self.vector_cache = os.path.join(self.cache_dir, "vector_index.faiss")
        self.docs_cache = os.path.join(self.cache_dir, "documents.pkl")
        self.bm25_cache = os.path.join(self.cache_dir, "bm25_index.pkl")
        os.makedirs(self.cache_dir, exist_ok=True)
        if init_embeddings:
            self._load_or_create_embeddings()

    def _generate_response(self, prompt: str) -> str:
        chat = [
            { "role": "user", "content": prompt },
        ]
        prompt_text = self.llm_tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        inputs = self.llm_tokenizer.encode(prompt_text, add_special_tokens=False, return_tensors="pt").to(self.device)
        outputs = self.llm_model.generate(input_ids=inputs, max_new_tokens=150)
        response = self.llm_tokenizer.decode(outputs[0])
        
        # Clean up the response
        response = response.replace(prompt_text, "").replace("<bos>", "").replace("<eos>", "")
        return response.strip()

    def _load_or_create_embeddings(self):
        # ... (rest of the file is the same)
        pass # Placeholder for brevity

    # All other methods from rag_qwen.py remain the same...
    # _ingest_documents, _hybrid_search, _format_context, generate_answer
    # I will copy them over in the next step. 