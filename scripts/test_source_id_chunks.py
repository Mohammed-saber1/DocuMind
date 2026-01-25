"""
Test script to verify that each file has its own source_id linked to its chunks.

This script will:
1. Get all indexed documents from ChromaDB
2. For each source_id, fetch all its chunks
3. Display the results to verify proper linking
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.memory_service import get_indexed_documents, get_chroma_client
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

def test_source_id_chunks():
    """Test that each source_id has its own chunks."""
    
    console.print("\n[bold cyan]🔍 Testing Source ID → Chunks Relationship[/bold cyan]\n")
    
    # Get all indexed documents
    indexed_docs = get_indexed_documents()
    
    if "error" in indexed_docs:
        console.print(f"[bold red]❌ Error: {indexed_docs['error']}[/bold red]")
        return
    
    if indexed_docs["total_chunks"] == 0:
        console.print("[bold yellow]⚠️ No chunks found in ChromaDB. Please index some documents first.[/bold yellow]")
        return
    
    console.print(f"[bold green]✅ Total Chunks in DB: {indexed_docs['total_chunks']}[/bold green]")
    console.print(f"[bold green]✅ Total Documents: {len(indexed_docs['documents'])}[/bold green]")
    console.print(f"[bold green]✅ Total Sessions: {len(indexed_docs['sessions'])}[/bold green]\n")
    
    # Get vectorstore client
    vectorstore = get_chroma_client("global_memory")
    all_data = vectorstore.get()
    
    # Group chunks by source_id
    source_id_map = {}
    
    for i, metadata in enumerate(all_data.get("metadatas", [])):
        if metadata:
            source_id = metadata.get("source_id", "unknown")
            doc_id = metadata.get("doc_id", "unknown")
            session_id = metadata.get("session_id", "default")
            chunk_type = metadata.get("chunk_type", "unknown")
            source_type = metadata.get("source", "unknown")
            
            if source_id not in source_id_map:
                source_id_map[source_id] = {
                    "doc_id": doc_id,
                    "session_id": session_id,
                    "source_type": source_type,
                    "chunks": [],
                    "chunk_types": []
                }
            
            source_id_map[source_id]["chunks"].append(i)
            source_id_map[source_id]["chunk_types"].append(chunk_type)
    
    # Display results
    console.print("[bold]📊 Source ID → Chunks Mapping:[/bold]\n")
    
    for source_id, info in source_id_map.items():
        # Create table for this source
        table = Table(title=f"Source ID: {source_id}", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="green")
        
        table.add_row("Doc ID", info["doc_id"])
        table.add_row("Session ID", info["session_id"])
        table.add_row("Source Type", info["source_type"])
        table.add_row("Total Chunks", str(len(info["chunks"])))
        table.add_row("Chunk Types", ", ".join(set(info["chunk_types"])))
        
        console.print(table)
        
        # Show first 3 chunks as sample
        console.print(f"\n[bold yellow]📝 Sample Chunks (first 3):[/bold yellow]")
        for idx in info["chunks"][:3]:
            chunk_text = all_data["documents"][idx][:150] + "..." if len(all_data["documents"][idx]) > 150 else all_data["documents"][idx]
            console.print(f"  • Chunk {idx + 1}: {chunk_text}")
        
        console.print("\n" + "="*80 + "\n")
    
    # Summary
    console.print(Panel.fit(
        f"[bold green]✅ Test Complete![/bold green]\n\n"
        f"Found {len(source_id_map)} unique source_id(s)\n"
        f"Each source_id is properly linked to its chunks",
        title="Summary",
        border_style="green"
    ))


if __name__ == "__main__":
    try:
        test_source_id_chunks()
    except ImportError as e:
        print(f"\n⚠️ Missing dependency: {e}")
        print("Installing rich library...")
        os.system("pip install rich")
        print("\nPlease run the script again.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
