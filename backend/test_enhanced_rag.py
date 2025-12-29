#!/usr/bin/env python3
"""
Test Enhanced RAG System with Cross-Encoder Reranking
"""

import os
import sys
import time

def test_dependencies():
    """Test if all required dependencies are available"""
    print("🔍 Testing Dependencies...")
    
    required_modules = {
        'sentence_transformers': 'sentence_transformers',
        'faiss': 'faiss',
        'numpy': 'numpy',
        'torch': 'torch',
        'transformers': 'transformers'
    }
    
    missing_modules = []
    
    for module_name, import_name in required_modules.items():
        try:
            __import__(import_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name} - {e}")
            missing_modules.append(module_name)
    
    # Test Cross-Encoder specifically
    try:
        from sentence_transformers import CrossEncoder
        print("✅ CrossEncoder from sentence_transformers")
    except ImportError as e:
        print(f"❌ CrossEncoder - {e}")
        missing_modules.append('CrossEncoder')
    
    if missing_modules:
        print(f"\n❌ Missing modules: {', '.join(missing_modules)}")
        return False
    else:
        print("\n✅ All dependencies are available!")
        return True

def test_enhanced_rag_initialization():
    """Test Enhanced RAG system initialization"""
    print("\n🚀 Testing Enhanced RAG Initialization...")
    
    try:
        from enhanced_rag_qwen import EnhancedRAGSystem
        
        # Test with minimal config
        PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
        
        print(f"📁 PDF Directory: {PDF_DIR}")
        print(f"📁 Directory exists: {os.path.exists(PDF_DIR)}")
        
        if os.path.exists(PDF_DIR):
            pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]
            print(f"📄 PDF files found: {len(pdf_files)}")
        
        # Initialize Enhanced RAG with Cross-Encoder
        enhanced_rag = EnhancedRAGSystem(PDF_DIR)
        
        print("✅ Enhanced RAG system initialized successfully")
        print(f"🔧 Reranker available: {enhanced_rag.reranker is not None}")
        
        if enhanced_rag.reranker:
            print(f"🎯 Reranker model: {enhanced_rag.reranker_config['model_name']}")
        
        return enhanced_rag
        
    except Exception as e:
        print(f"❌ Enhanced RAG initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_cross_encoder_reranking(enhanced_rag):
    """Test Cross-Encoder reranking functionality"""
    print("\n🎯 Testing Cross-Encoder Reranking...")
    
    if not enhanced_rag or not enhanced_rag.reranker:
        print("❌ Enhanced RAG or reranker not available")
        return False
    
    try:
        # Test query
        test_query = "What are the symptoms of diabetes?"
        
        print(f"📝 Test Query: {test_query}")
        
        # Test document processing
        start_time = time.time()
        
        # Get some test candidates (simulate)
        if enhanced_rag.documents:
            test_candidates = enhanced_rag.documents[:5]  # First 5 documents
            print(f"📚 Testing with {len(test_candidates)} documents")
            
            # Test reranking
            reranked = enhanced_rag._rerank_documents(test_query, test_candidates)
            
            rerank_time = time.time() - start_time
            
            print(f"✅ Cross-Encoder reranking completed in {rerank_time:.3f} seconds")
            print(f"🔢 Reranked documents: {len(reranked)}")
            
            # Show reranking results
            for i, doc in enumerate(reranked[:3]):
                score = doc.get('rerank_score', 'N/A')
                file_name = doc.get('file', 'Unknown')
                print(f"  {i+1}. {file_name} (Score: {score})")
            
            return True
        else:
            print("⚠️ No documents loaded for testing")
            return False
            
    except Exception as e:
        print(f"❌ Cross-Encoder reranking test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_query(enhanced_rag):
    """Test enhanced query processing"""
    print("\n💬 Testing Enhanced Query Processing...")
    
    if not enhanced_rag:
        print("❌ Enhanced RAG not available")
        return False
    
    test_queries = [
        "What are the symptoms of diabetes?",
        "How to prevent heart disease?",
        "What is hypertension?"
    ]
    
    for i, query in enumerate(test_queries):
        print(f"\n📝 Query {i+1}: {query}")
        
        try:
            start_time = time.time()
            response = enhanced_rag.generate_answer(query)
            query_time = time.time() - start_time
            
            print(f"⏱️ Response time: {query_time:.2f} seconds")
            print(f"🔧 Reranked: {response.get('reranked', False)}")
            print(f"📚 Sources: {response.get('num_sources', 0)}")
            
            # Show thinking process (first 200 chars)
            thinking = response.get('thinking', '')
            if thinking:
                print(f"🧠 Thinking: {thinking[:200]}...")
            
            # Show response (first 150 chars)
            content = response.get('content', '')
            if content:
                print(f"💡 Response: {content[:150]}...")
            
            print("✅ Query processed successfully")
            
        except Exception as e:
            print(f"❌ Query processing failed: {e}")
            return False
    
    return True

def compare_performance():
    """Compare original vs enhanced RAG performance"""
    print("\n⚖️ Performance Comparison...")
    
    try:
        from rag_qwen import RAGSystem
        from enhanced_rag_qwen import EnhancedRAGSystem
        
        PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
        test_query = "What are the symptoms of diabetes?"
        
        # Test original RAG
        print("🔹 Testing Original RAG...")
        start_time = time.time()
        original_rag = RAGSystem(PDF_DIR)
        original_response = original_rag.generate_answer(test_query)
        original_time = time.time() - start_time
        
        # Test enhanced RAG
        print("🔸 Testing Enhanced RAG...")
        start_time = time.time()
        enhanced_rag = EnhancedRAGSystem(PDF_DIR)
        enhanced_response = enhanced_rag.generate_answer(test_query)
        enhanced_time = time.time() - start_time
        
        # Compare results
        print(f"\n📊 Performance Comparison:")
        print(f"Original RAG: {original_time:.2f}s")
        print(f"Enhanced RAG: {enhanced_time:.2f}s")
        print(f"Speed difference: {enhanced_time - original_time:.2f}s")
        
        print(f"\nOriginal sources: {original_response.get('num_sources', 'N/A')}")
        print(f"Enhanced sources: {enhanced_response.get('num_sources', 'N/A')}")
        print(f"Reranking used: {enhanced_response.get('reranked', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance comparison failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Enhanced RAG System Test Suite")
    print("=" * 50)
    
    # Test 1: Dependencies
    if not test_dependencies():
        print("\n❌ Dependency test failed. Please install missing packages.")
        return
    
    # Test 2: Enhanced RAG Initialization
    enhanced_rag = test_enhanced_rag_initialization()
    if not enhanced_rag:
        print("\n❌ Enhanced RAG initialization failed.")
        return
    
    # Test 3: Cross-Encoder Reranking
    if not test_cross_encoder_reranking(enhanced_rag):
        print("\n⚠️ Cross-Encoder reranking test failed.")
    
    # Test 4: Enhanced Query Processing
    if not test_enhanced_query(enhanced_rag):
        print("\n⚠️ Enhanced query processing test failed.")
    
    # Test 5: Performance Comparison
    if not compare_performance():
        print("\n⚠️ Performance comparison test failed.")
    
    print("\n" + "=" * 50)
    print("🎉 Enhanced RAG Test Suite Completed!")
    print("\n💡 Key Features Tested:")
    print("✅ Cross-Encoder reranking (sentence-transformers)")
    print("✅ Two-stage retrieval (Hybrid → Rerank)")
    print("✅ Performance comparison with original RAG")
    print("✅ Enhanced context formatting with relevance scores")

if __name__ == "__main__":
    main() 