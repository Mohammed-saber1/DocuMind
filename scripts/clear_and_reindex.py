"""
Clear ChromaDB Script
=====================

Use this script to delete all chunks from ChromaDB so you can re-index 
your Excel files with the new row-based chunking strategy.

Usage:
    python clear_and_reindex.py
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.memory_service import get_indexed_documents, delete_collection


def main():
    print("=" * 60)
    print("Clear ChromaDB Tool")
    print("=" * 60)
    
    # Show all indexed documents
    print("\n📋 Current indexed documents in ChromaDB:")
    docs_info = get_indexed_documents()
    
    if docs_info.get("total_chunks", 0) == 0:
        print("   ✅ ChromaDB is empty. No documents indexed yet.")
        print("\n💡 Upload your Excel files through the API to index them.")
        return
    
    print(f"   Total chunks: {docs_info['total_chunks']}")
    print(f"\n   Documents:")
    for doc in docs_info.get("documents", []):
        print(f"   - {doc['source']}: {doc['doc_id']} ({doc['chunks']} chunks) [session: {doc['session_id']}]")
    
    # Confirm deletion
    print("\n" + "=" * 60)
    confirm = input("⚠️  Clear ALL ChromaDB data? (yes/no): ").strip().lower()
    
    if confirm == "yes":
        print("\n🗑️ Deleting ChromaDB collection...")
        delete_collection("global_memory")
        print("✅ ChromaDB cleared successfully!")
        print("\n" + "=" * 60)
        print("📝 Next Steps:")
        print("1. Re-upload your Excel files through the API")
        print("2. New files will be indexed with row-based chunking")
        print("3. Test your queries - they should work correctly now!")
        print("=" * 60)
    else:
        print("❌ Cancelled. ChromaDB unchanged.")


if __name__ == "__main__":
    main()
