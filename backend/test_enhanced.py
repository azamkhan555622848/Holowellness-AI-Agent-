#!/usr/bin/env python3

from enhanced_rag_qwen import EnhancedRAGSystem
import os

def test_enhanced_response():
    PDF_DIR = os.path.join(os.path.dirname(__file__), 'pdfs')
    print(f"Testing Enhanced RAG System...")
    
    try:
        rag = EnhancedRAGSystem(pdf_dir=PDF_DIR)
        response = rag.generate_answer('test knee pain', [])
        
        print(f"Response keys: {list(response.keys())}")
        print(f"Has thinking: {'thinking' in response}")
        print(f"Has retrieved_context: {'retrieved_context' in response}")
        print(f"Has num_sources: {'num_sources' in response}")
        
        if 'thinking' in response:
            print(f"Thinking length: {len(response['thinking'])}")
        if 'retrieved_context' in response:
            print(f"Retrieved context length: {len(response['retrieved_context'])}")
        if 'content' in response:
            print(f"Content preview: {response['content'][:100]}...")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_enhanced_response() 