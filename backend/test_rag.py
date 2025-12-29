#!/usr/bin/env python3

from enhanced_rag_qwen import EnhancedRAGSystem
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rag_retrieval():
    try:
        # Initialize RAG system
        PDF_DIR = os.path.join(os.path.dirname(__file__), 'pdfs')
        print(f'PDF directory: {PDF_DIR}')
        
        rag = EnhancedRAGSystem(pdf_dir=PDF_DIR)
        print(f'Documents loaded: {len(rag.documents)}')
        print(f'Vector index type: {type(rag.vector_store)}')
        
        # Test queries
        test_queries = [
            'knee pain treatment',
            'knee injury recovery',
            'physical therapy for knee',
            'how to treat knee pain',
            'rehabilitation exercises'
        ]
        
        for query in test_queries:
            print(f'\n=== Testing query: "{query}" ===')
            try:
                # Test retrieval
                results = rag._enhanced_hybrid_search(query)
                print(f'Retrieved {len(results)} documents')
                
                if results:
                    for i, doc in enumerate(results):
                        score = doc.get('rerank_score', 'N/A')
                        print(f'Doc {i+1}: Score={score}')
                        print(f'  File: {doc.get("file", "Unknown")}')
                        print(f'  Text preview: {doc.get("text", "")[:150]}...')
                else:
                    print('No documents retrieved!')
                
                # Test full answer generation
                print(f'\n--- Testing full answer generation ---')
                response = rag.generate_answer(query, [])
                print(f'Response keys: {response.keys()}')
                print(f'Content length: {len(response.get("content", ""))}')
                print(f'Content preview: {response.get("content", "")[:200]}...')
                
            except Exception as e:
                print(f'Error with query "{query}": {e}')
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f'Error initializing RAG system: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_rag_retrieval() 