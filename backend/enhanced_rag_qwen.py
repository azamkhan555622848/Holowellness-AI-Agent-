#!/usr/bin/env python3
"""
Enhanced RAG System with Cross-Encoder Reranking
"""
import os
import time
import numpy as np
from typing import List, Dict, Optional, Any
import logging
from rag_qwen import RAGSystem
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

class EnhancedRAGSystem(RAGSystem):
    """
    Implements two-stage retrieval:
    1. Hybrid search (Vector + BM25) to cast a wide net.
    2. Cross-Encoder reranking to select the most relevant results.
    """
    def __init__(self, pdf_dir: str, reranker_model='cross-encoder/ms-marco-MiniLM-L-6-v2'):
        super().__init__(pdf_dir, init_embeddings=False)
        
        self.reranker_model_name = reranker_model
        self.reranker = None
        
        self.first_stage_k = 100  # More candidates for reranking
        self.final_k = 10         # More final results
        self.score_threshold = 0.3  # More balanced threshold for better retrieval
        
        self._load_or_create_embeddings()
        self._init_reranker()
        
        logger.info(f"Enhanced RAG System initialized with Cross-Encoder: {self.reranker_model_name}")

    def _init_reranker(self):
        try:
            logger.info("Loading Cross-Encoder reranker model...")
            self.reranker = CrossEncoder(self.reranker_model_name)
            logger.info("Cross-Encoder reranker model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            self.reranker = None

    def _hybrid_search_candidates(self, query: str) -> List[Dict[str, Any]]:
        if self.vector_store is None or self.bm25_index is None:
            logger.warning("Indexes not created. Returning empty list.")
            return []
            
        query_embedding = self.embedder.encode([query])
        D, I = self.vector_store.search(np.array(query_embedding, dtype=np.float32), self.first_stage_k)
        vector_results_indices = I[0]

        tokenized_query = query.split(" ")
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_top_n_indices = np.argsort(bm25_scores)[::-1][:self.first_stage_k]

        combined_indices = list(set(vector_results_indices) | set(bm25_top_n_indices))
        
        return [self.documents[i] for i in combined_indices if i < len(self.documents)]

    def _rerank_documents(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.reranker or not candidates:
            return candidates[:self.final_k]
            
        pairs = [[query, doc['text']] for doc in candidates]
        scores = self.reranker.predict(pairs)
        
        for doc, score in zip(candidates, scores):
            doc['rerank_score'] = score
            
        candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        # Always return at least the top results, ignore threshold for now
        logger.info(f"Reranked {len(candidates)} documents, returning top {self.final_k}")
        return candidates[:self.final_k]

    def _enhanced_hybrid_search(self, query: str) -> List[Dict[str, Any]]:
        candidates = self._hybrid_search_candidates(query)
        return self._rerank_documents(query, candidates)

    def _format_context_enhanced(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Formats the retrieved chunks with aggressive size limiting for DeepSeek stability.
        """
        if not chunks:
            return "No relevant context found."
        
        formatted_chunks = []
        total_length = 0
        max_context_length = 20000  # Increased context limit now that DeepSeek is working
        
        for chunk in chunks:
            # Increased chunk size to 800 characters for better information
            chunk_text = chunk['text'][:800] + "..." if len(chunk['text']) > 800 else chunk['text']
            formatted_chunk = f"[Source: {chunk['file']}]\n{chunk_text}"
            
            if total_length + len(formatted_chunk) > max_context_length:
                print(f"Context limit reached at {total_length} characters, stopping at chunk {len(formatted_chunks)}")
                break
                
            formatted_chunks.append(formatted_chunk)
            total_length += len(formatted_chunk)
        
        result = "\n\n".join(formatted_chunks)
        print(f"Enhanced context size: {len(result)} characters from {len(chunks)} chunks")
        return result

    def generate_answer(self, query: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generates an answer using the enhanced two-stage retrieval process.
        """
        relevant_chunks = self._enhanced_hybrid_search(query)
        
        # Add a guard for when no relevant documents are found
        if not relevant_chunks:
            thinking_process = (
                f"Enhanced RAG Analysis:\n"
                f"Query: '{query}'\n"
                f"Result: No relevant documents found after retrieval and reranking."
            )
            return {
                "thinking": thinking_process,
                "content": "I could not find any relevant information in the provided documents to answer your question.",
                "retrieved_context": "No relevant documents found for this query.",
                "sources": [],
                "reranked": self.reranker is not None
            }
            
        context = self._format_context_enhanced(relevant_chunks)
        
        internal_thinking = (
            f"Enhanced RAG Analysis:\n"
            f"Query: '{query}'\n"
            f"Stage 1: Retrieved candidates.\n"
            f"Stage 2: Reranked to {len(relevant_chunks)} documents."
        )

        # Call the parent's generate_answer, passing the enhanced context
        parent_response = super().generate_answer(
            query,
            conversation_history,
            override_context=context,
            override_thinking=internal_thinking
        )
        
        # Extract thinking tags from content and format the response
        content = parent_response.get('content', '')
        thinking_content = ''
        clean_content = content
        
        # No filtering - use content directly
        clean_content = content
        
        # Format retrieved context
        retrieved_context = ""
        if relevant_chunks:
            retrieved_context = "\n\n".join([
                f"**Source: {chunk['file']}**\n{chunk['text'][:300]}..." 
                if len(chunk['text']) > 300 
                else f"**Source: {chunk['file']}**\n{chunk['text']}"
                for chunk in relevant_chunks
            ])
        
        # Add enhanced information to the final response
        parent_response['thinking'] = thinking_content if thinking_content else parent_response.get('thinking', '')
        parent_response['content'] = clean_content
        parent_response['retrieved_context'] = retrieved_context
        parent_response['reranked'] = self.reranker is not None
        parent_response['sources'] = relevant_chunks
        parent_response['num_sources'] = len(relevant_chunks)
        return parent_response

def create_enhanced_rag_system(pdf_dir: str) -> EnhancedRAGSystem:
    return EnhancedRAGSystem(pdf_dir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
    
    try:
        enhanced_rag = EnhancedRAGSystem(PDF_DIR)
        
        while True:
            user_query = input("\nEnter your question (or 'quit' to exit): ").strip()
            if user_query.lower() in {"quit", "exit"}:
                break
            
            response = enhanced_rag.generate_answer(user_query)
            
            print("\n--- Thinking Process ---")
            print(response["thinking"])
            print("\n--- Final Answer ---")
            print(response["content"])
            if response.get('sources'):
                print("\n--- Sources ---")
                for source in response['sources']:
                    print(f"- {source['file']} (Score: {source.get('rerank_score', 'N/A'):.2f})")
                    
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True) 