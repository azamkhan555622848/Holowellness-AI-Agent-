#!/usr/bin/env python3
"""
Test script to demonstrate OCR functionality
"""
import os
import sys
from datetime import datetime

# Add current directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

from enhanced_rag_qwen import EnhancedRAGSystem

def test_ocr_enhanced_processing():
    """Test OCR-enhanced document processing"""
    
    print(f"🔍 OCR-Enhanced RAG Test")
    print("=" * 50)
    print(f"🕒 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Use absolute path
    PDF_DIR = "/home/asus/Holowellness_Chatbot/Holowellness_Chatbot_version_1.0-master/backend/pdfs"
    
    try:
        print(f"\n📁 Processing PDFs from: {PDF_DIR}")
        print(f"📁 Directory exists: {os.path.exists(PDF_DIR)}")
        
        if os.path.exists(PDF_DIR):
            pdf_files = []
            for root, _, files in os.walk(PDF_DIR):
                for file in files:
                    if file.endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
            
            print(f"📄 Total PDF files found: {len(pdf_files)}")
            print("📋 Sample files:")
            for pdf in pdf_files[:5]:  # Show first 5
                print(f"   • {os.path.basename(pdf)}")
            if len(pdf_files) > 5:
                print(f"   ... and {len(pdf_files) - 5} more")
        
        print(f"\n🚀 Initializing Enhanced RAG system with OCR...")
        enhanced_rag = EnhancedRAGSystem(pdf_dir=PDF_DIR)
        
        print(f"\n✅ System initialized successfully!")
        print(f"📊 Total document chunks processed: {len(enhanced_rag.documents)}")
        print(f"🔧 Reranker available: {enhanced_rag.reranker is not None}")
        
        # Test a medical query
        test_query = "What are the symptoms of trigger points in muscles?"
        print(f"\n🏥 Testing query: {test_query}")
        
        response = enhanced_rag.generate_answer(test_query)
        
        print(f"\n💡 Response: {response['content'][:200]}...")
        print(f"📚 Sources found: {len(response.get('sources', []))}")
        
        if response.get('sources'):
            print(f"📖 Top sources:")
            for i, source in enumerate(response['sources'][:3], 1):
                score = source.get('rerank_score', 'N/A')
                file_name = source.get('file', 'Unknown')
                print(f"   {i}. {file_name} (Score: {score})")
        
        print(f"\n🎉 OCR-Enhanced RAG test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ocr_enhanced_processing() 