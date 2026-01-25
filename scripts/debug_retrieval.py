import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.memory_service import get_chroma_client
from rich.console import Console

console = Console()

def debug_retrieval(session_id, source_id):
    console.print(f"\n[bold cyan]🔍 Debugging Retrieval for:[/bold cyan]")
    console.print(f"  Session ID: {session_id}")
    console.print(f"  Source ID:  {source_id}\n")
    
    vectorstore = get_chroma_client("global_memory")
    
    # 1. Check all entries for this source_id
    console.print("[bold yellow]1. Checking source_id only...[/bold yellow]")
    results_source = vectorstore.get(where={"source_id": source_id})
    count_source = len(results_source.get("ids", []))
    console.print(f"   Found {count_source} chunks.")
    
    # 2. Check all entries for this session_id
    console.print("\n[bold yellow]2. Checking session_id only...[/bold yellow]")
    results_session = vectorstore.get(where={"session_id": session_id})
    count_session = len(results_session.get("ids", []))
    console.print(f"   Found {count_session} chunks.")
    
    # 3. Check combined filter using $and (This is often required for multiple filters in Chroma)
    console.print("\n[bold yellow]3. Checking combined filter ($and)...[/bold yellow]")
    try:
        results_combined = vectorstore.get(where={"$and": [{"session_id": session_id}, {"source_id": source_id}]})
        count_combined = len(results_combined.get("ids", []))
        console.print(f"   Found {count_combined} chunks using $and.")
    except Exception as e:
        console.print(f"   ❌ Error with $and: {e}")

    # 4. Check current filter style (plain dict)
    console.print("\n[bold yellow]4. Checking plain dict filter...[/bold yellow]")
    try:
        results_plain = vectorstore.get(where={"session_id": session_id, "source_id": source_id})
        count_plain = len(results_plain.get("ids", []))
        console.print(f"   Found {count_plain} chunks using plain dict.")
    except Exception as e:
        console.print(f"   ❌ Error with plain dict: {e}")

    # 5. Print metadata fields from one chunk if found
    if count_source > 0:
        console.print("\n[bold green]✅ Sample Metadata from index:[/bold green]")
        console.print(results_source["metadatas"][0])

if __name__ == "__main__":
    # Based on user's input
    S_ID = "session_testpdfs"
    SRC_ID = "9a5cd1f5_About Us Aitech__816c0aa9"
    debug_retrieval(S_ID, SRC_ID)
