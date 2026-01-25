"""
Script to demonstrate RAG indexing using cleaned content.
========================================================

This script runs the document pipeline and specifically logs
when it uses 'clean_content' from the LLM for ChromaDB indexing.
"""

import os
import sys
import asyncio
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from pipeline.document_pipeline import pipeline
from services.memory_service import get_indexed_documents
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler

# Configure logging with Rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("try_clean_indexing")
console = Console()

async def try_indexing(file_path):
    """
    Run the pipeline on a file and show RAG behavior.
    """
    if not os.path.exists(file_path):
        logger.error(f"❌ File not found: {file_path}")
        return

    session_id = f"test_{os.path.basename(file_path).split('.')[0]}"
    
    console.print(Panel(
        f"[bold cyan]🚀 Starting RAG Optimization Test[/bold cyan]\n"
        f"File: [yellow]{os.path.basename(file_path)}[/yellow]\n"
        f"Session: [magenta]{session_id}[/magenta]",
        title="Input",
        border_style="cyan"
    ))

    logger.info("⏳ Processing document (Extraction -> Cleaning -> Indexing)...")
    
    try:
        # Run the pipeline
        base_dir, result_ref = await pipeline(
            file_path, 
            author="Tester", 
            use_ocr_vlm=True, 
            session_id=session_id
        )
        
        console.print(f"\n[bold green]✅ Pipeline Complete![/bold green]")
        console.print(f"📁 Base Dir: {base_dir}")
        console.print(f"🔗 Result Ref: {result_ref}\n")
        
        # Verify the indexing in ChromaDB
        logger.info("🔍 Verifying ChromaDB chunks...")
        
        from services.memory_service import get_chroma_client
        vectorstore = get_chroma_client("global_memory")
        
        # Get chunks for this specific session
        results = vectorstore.get(where={"session_id": session_id})
        
        if results and results.get("ids"):
            count = len(results["ids"])
            console.print(f"[bold green]✨ Found {count} chunks indexed in ChromaDB for this session.[/bold green]")
            
            # Show a sample chunk to verify it's clean (no page numbers etc)
            sample = results["documents"][0]
            console.print(Panel(
                f"[bold]Sample Chunk Context:[/bold]\n\n{sample[:300]}...",
                title="RAG Quality Check",
                border_style="green"
            ))
            
            console.print("\n[bold blue]Note:[/bold] If you saw '🧹 Using cleaned content for RAG indexing...' in the logs above, then the optimization is working successfully!")
        else:
            logger.warning("⚠️ No chunks found for this session.")

    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")

if __name__ == "__main__":
    console.print("\n[bold cyan]📂 RAG Optimization Test Tool[/bold cyan]")
    
    test_file = None
    
    # 1. Check command line arguments first
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        # 2. Ask user for input interactively
        console.print("[yellow]Please enter the absolute path to the file you want to test:[/yellow]")
        test_file = input("👉 Path: ").strip()
        
        # Remove quotes if user copied path with quotes
        if (test_file.startswith('"') and test_file.endswith('"')) or \
           (test_file.startswith("'") and test_file.endswith("'")):
            test_file = test_file[1:-1]

    # Validate file exists
    if not test_file or not os.path.exists(test_file):
        console.print(f"\n[bold red]❌ Error:[/bold red] File not found or path is empty: [yellow]{test_file}[/yellow]")
        console.print("Please make sure to provide a valid absolute path.\n")
        sys.exit(1)
        
    asyncio.run(try_indexing(test_file))
