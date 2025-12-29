#!/usr/bin/env python3
"""
Fitness-Focused Enhanced RAG Test Suite
Tests the Cross-Encoder enhanced RAG system with realistic fitness injury and wellness questions
"""

import time
import sys
import os
from datetime import datetime

# --- Absolute Path Configuration ---
# The user has provided the correct absolute path.
PDF_DIR_ABSOLUTE = "/home/asus/Holowellness_Chatbot/Holowellness_Chatbot_version_1.0-master/backend/pdfs"
# Get the directory where this script is located to fix imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

def print_header(title):
    """Print a formatted header"""
    print(f"\n🏋️ {title}")
    print("=" * 60)

def print_section(title):
    """Print a formatted section header"""
    print(f"\n💪 {title}")

def test_dependencies():
    """Test if all required dependencies are available"""
    print_section("Testing Dependencies...")
    
    dependencies = [
        ('sentence_transformers', 'sentence_transformers'),
        ('faiss', 'faiss'),
        ('numpy', 'numpy'),
        ('torch', 'torch'),
        ('transformers', 'transformers'),
        ('CrossEncoder', 'sentence_transformers.CrossEncoder')
    ]
    
    missing_deps = []
    for name, import_path in dependencies:
        try:
            if '.' in import_path:
                module, attr = import_path.rsplit('.', 1)
                exec(f"from {module} import {attr}")
            else:
                exec(f"import {import_path}")
            print(f"✅ {name}")
        except ImportError as e:
            print(f"❌ {name}: {e}")
            missing_deps.append(name)
    
    if missing_deps:
        print(f"\n❌ Missing dependencies: {', '.join(missing_deps)}")
        return False
    else:
        print(f"\n✅ All fitness RAG dependencies are available!")
        return True

def test_enhanced_rag_initialization():
    """Test Enhanced RAG system initialization"""
    print_section("Testing Enhanced RAG Initialization...")
    
    try:
        from enhanced_rag_qwen import EnhancedRAGSystem
        
        # Use the absolute path for the PDF directory provided by the user
        pdf_dir = PDF_DIR_ABSOLUTE
        print(f"📁 PDF Directory: {pdf_dir}")
        print(f"📁 Directory exists: {os.path.exists(pdf_dir)}")
        
        if os.path.exists(pdf_dir):
            pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
            print(f"📄 PDF files found: {len(pdf_files)}")
            for pdf in pdf_files:
                print(f"   📋 {pdf}")
        else:
            print(f"⚠️  PDF Directory not found! Please check the path.")

        
        # THIS IS THE FIX: Use 'pdf_dir' instead of 'pdf_directory'
        enhanced_rag = EnhancedRAGSystem(pdf_dir=pdf_dir)
        
        print(f"✅ Enhanced RAG system initialized successfully")
        print(f"🔧 Reranker available: {enhanced_rag.reranker is not None}")
        if enhanced_rag.reranker:
            print(f"🎯 Reranker model: {enhanced_rag.reranker_model_name}")
        
        return enhanced_rag
    
    except Exception as e:
        print(f"❌ Enhanced RAG initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_fitness_queries(enhanced_rag):
    """Test the system with realistic fitness injury and wellness questions"""
    print_section("Testing Fitness Injury & Wellness Queries...")
    
    # Realistic fitness and injury questions
    fitness_queries = [
        "I have pain in my knee after running, what should I do?",
        "How can I prevent shoulder injuries during weightlifting?",
        "What are the best exercises for lower back pain relief?",
        "I pulled my hamstring during a workout, how do I recover?",
        "How do I strengthen my core to prevent back injuries?",
        "What should I eat after a workout for muscle recovery?",
        "I have tennis elbow pain, what exercises can help?",
        "How can I improve my flexibility to prevent injuries?",
        "What are signs of overtraining and how to avoid it?",
        "How do I warm up properly before exercising?"
    ]
    
    results = []
    
    for i, query in enumerate(fitness_queries, 1):
        print(f"\n🏃 Query {i}: {query}")
        
        start_time = time.time()
        try:
            response = enhanced_rag.generate_answer(query)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            sources_used = len(response.get('sources', []))
            has_reranking = response.get('reranked', False)
            thinking = response.get('thinking', 'No thinking process available')
            
            print(f"⏱️ Response time: {response_time:.2f} seconds")
            print(f"🔧 Reranked: {has_reranking}")
            print(f"📚 Sources: {sources_used}")
            print(f"🧠 Thinking: {thinking[:100]}..." if len(thinking) > 100 else f"🧠 Thinking: {thinking}")
            
            # Show first part of response
            llm_response = response.get('content', 'No response generated')
            preview = llm_response[:150] + "..." if len(llm_response) > 150 else llm_response
            print(f"💡 Response: {preview}")
            
            # Show sources if available
            if sources_used > 0:
                print("📖 Sources used:")
                for j, source in enumerate(response.get('sources', [])[:3], 1):
                    score = source.get('rerank_score', 'N/A')
                    content_preview = source.get('text', '')[:80] + "..."
                    print(f"   {j}. Score: {score:.3f} | {content_preview}")
            
            results.append({'query': query, 'success': True, 'response_time': response_time, 'sources_used': sources_used, 'reranked': has_reranking})
            
            print("✅ Query processed successfully")
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            results.append({
                'query': query,
                'response_time': 0,
                'sources_used': 0,
                'reranked': False,
                'success': False,
                'error': str(e)
            })
    
    return results

def test_cross_encoder_reranking(enhanced_rag):
    """Test Cross-Encoder reranking functionality specifically"""
    print_section("Testing Cross-Encoder Reranking...")
    
    if not enhanced_rag.reranker:
        print("❌ No reranker available for testing")
        return
    
    # Test query
    test_query = "I have knee pain after running"
    print(f"📝 Test Query: {test_query}")
    
    # Create some mock documents for reranking test
    mock_documents = [
        {"text": "Running can cause knee pain due to overuse, improper form, or inadequate warm-up. Rest and ice are recommended.", "score": 0.7},
        {"text": "Knee injuries are common in sports. Prevention includes proper stretching and strength training.", "score": 0.6},
        {"text": "Physical therapy exercises can help strengthen the muscles around the knee joint.", "score": 0.8},
        {"text": "Diet and nutrition play important roles in overall health and wellness.", "score": 0.3},
        {"text": "Weight training requires proper form to prevent injuries and maximize results.", "score": 0.4}
    ]
    
    print(f"📚 Testing with {len(mock_documents)} documents")
    
    try:
        start_time = time.time()
        reranked_docs = enhanced_rag._rerank_documents(test_query, mock_documents)
        end_time = time.time()
        
        print(f"✅ Cross-Encoder reranking completed in {end_time - start_time:.3f} seconds")
        print(f"🔢 Reranked documents: {len(reranked_docs)}")
        
        if reranked_docs:
            print("📊 Top reranked results:")
            for i, doc in enumerate(reranked_docs[:3], 1):
                score = doc.get('rerank_score', doc.get('score', 'N/A'))
                content_preview = doc.get('text', '')[:60] + "..."
                print(f"   {i}. Score: {score:.3f} | {content_preview}")
        
    except Exception as e:
        print(f"❌ Cross-Encoder reranking failed: {e}")
        import traceback
        traceback.print_exc()

def analyze_results(results):
    """Analyze and display test results"""
    print_section("Fitness Test Results Analysis...")
    
    successful_queries = [r for r in results if r['success']]
    failed_queries = [r for r in results if not r['success']]
    
    if successful_queries:
        avg_response_time = sum(r['response_time'] for r in successful_queries) / len(successful_queries)
        avg_sources = sum(r['sources_used'] for r in successful_queries) / len(successful_queries)
        reranked_count = sum(1 for r in successful_queries if r['reranked'])
        
        print(f"📊 Success Rate: {len(successful_queries)}/{len(results)} ({len(successful_queries)/len(results)*100:.1f}%)")
        print(f"⏱️ Average Response Time: {avg_response_time:.2f} seconds")
        print(f"📚 Average Sources Used: {avg_sources:.1f}")
        print(f"🔧 Queries Using Reranking: {reranked_count}/{len(successful_queries)}")
        
        if failed_queries:
            print(f"\n❌ Failed Queries ({len(failed_queries)}):")
            for failed in failed_queries:
                print(f"   • {failed['query'][:50]}... - {failed.get('error', 'Unknown error')}")
    else:
        print("❌ No successful queries to analyze")

def main():
    """Main test function"""
    print_header("Fitness-Focused Enhanced RAG Test Suite")
    print(f"🕒 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test dependencies
    if not test_dependencies():
        print("❌ Cannot continue without required dependencies")
        sys.exit(1)
    
    # Test Enhanced RAG initialization
    enhanced_rag = test_enhanced_rag_initialization()
    if not enhanced_rag:
        print("❌ Cannot continue without Enhanced RAG system")
        sys.exit(1)
    
    # Test Cross-Encoder reranking
    test_cross_encoder_reranking(enhanced_rag)
    
    # Test fitness queries
    results = test_fitness_queries(enhanced_rag)
    
    # Analyze results
    analyze_results(results)
    
    print_header("Fitness RAG Test Suite Completed!")
    print(f"🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n💡 Key Fitness Features Tested:")
    print(f"✅ Cross-Encoder reranking for injury queries")
    print(f"✅ Fitness-specific question processing")
    print(f"✅ Injury prevention and recovery guidance")
    print(f"✅ Workout and exercise recommendations")
    print(f"✅ Performance analysis for wellness queries")

if __name__ == "__main__":
    main() 