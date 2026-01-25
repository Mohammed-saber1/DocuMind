import logging
import json
from typing import List, Dict, Any, Tuple
from langchain_text_splitters import TokenTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
from core.config import get_settings

# Configuration
def get_embeddings():
    """Initialize Ollama Embeddings."""
    settings = get_settings()
    return OllamaEmbeddings(
        model=settings.llm.embedding_model,
        base_url=settings.llm.base_url
    )

def token_splitter_chunking(original_text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> List[str]:
    """
    Split text into token-based chunks using LangChain's TokenTextSplitter.
    """
    logger.info(f"Splitting text with TokenTextSplitter (size={chunk_size}, overlap={chunk_overlap})")
    text_splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # We use create_documents but return just the strings as requested
    chunks = text_splitter.create_documents([original_text])
    return [chunk.page_content for chunk in chunks]

def semantic_chunking(original_text: str) -> List[str]:
    """
    Perform semantic-aware text chunking using embedding similarity.
    """
    logger.info("Splitting text with SemanticChunker")
    embeddings = get_embeddings()
    
    # SemanticChunker automatically calculates boundaries based on cosine similarity
    text_splitter = SemanticChunker(embeddings=embeddings)
    
    chunks = text_splitter.create_documents([original_text])
    return [chunk.page_content for chunk in chunks]

def process_document_for_rag(text_content: str, method: str = "token", **kwargs) -> List[str]:
    """
    Main entry point to chunk a document based on preferred method.
    """
    if method == "semantic":
        return semantic_chunking(text_content)
    else:
        chunk_size = kwargs.get("chunk_size", 512)
        chunk_overlap = kwargs.get("chunk_overlap", 64)
        return token_splitter_chunking(text_content, chunk_size, chunk_overlap)


def create_excel_chunks(base_dir: str, source: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Create row-based chunks from Excel/CSV tables.
    
    Each row becomes a searchable chunk with format:
    "Column1: value1, Column2: value2, Column3: value3"
    
    Args:
        base_dir: Document base directory containing tables.json
        source: Source type ("excel" or "csv")
        
    Returns:
        Tuple of (chunks, metadata) where:
        - chunks: List of text chunks (one per row)
        - metadata: List of metadata dicts (one per chunk)
    """
    tables_path = os.path.join(base_dir, "tables", "tables.json")
    
    if not os.path.exists(tables_path):
        return [], []
    
    with open(tables_path, "r", encoding="utf-8") as f:
        tables_data = json.load(f)
    
    chunks = []
    metadata = []
    
    for table in tables_data:
        sheet_name = table.get("sheet", table.get("name", "Unknown"))
        headers = table.get("headers", [])
        data_rows = table.get("data", [])
        
        # Skip if no headers or data
        if not headers or not data_rows:
            continue
        
        # Create a chunk for each row
        for row_idx, row in enumerate(data_rows, start=1):
            # Build searchable text: "Name: John, Age: 30, Country: USA"
            row_parts = []
            row_metadata = {
                "sheet": sheet_name,
                "row_number": row_idx + 1,  # +1 because row 1 is header
            }
            
            for col_idx, header in enumerate(headers):
                if col_idx < len(row):
                    value = row[col_idx]
                    if value and str(value).strip():
                        # Add to searchable text
                        row_parts.append(f"{header}: {value}")
                        
                        # Add to metadata with sanitized key
                        # Convert "First Name" -> "first_name"
                        meta_key = header.lower().replace(" ", "_").replace("-", "_")
                        # Limit key length and remove special chars
                        meta_key = "".join(c for c in meta_key if c.isalnum() or c == "_")[:50]
                        row_metadata[meta_key] = str(value)
            
            if row_parts:
                # Create the chunk text
                chunk_text = f"[{sheet_name} - Row {row_idx + 1}] " + ", ".join(row_parts)
                chunks.append(chunk_text)
                metadata.append(row_metadata)
    
    return chunks, metadata


def create_enhanced_excel_summary(base_dir: str) -> str:
    """
    Create a summary text from Excel tables for additional context.
    
    This can be used alongside row chunks to provide high-level overview.
    
    Args:
        base_dir: Document base directory
        
    Returns:
        Summary text describing the tables
    """
    tables_path = os.path.join(base_dir, "tables", "tables.json")
    
    if not os.path.exists(tables_path):
        return ""
    
    with open(tables_path, "r", encoding="utf-8") as f:
        tables_data = json.load(f)
    
    summary_parts = []
    
    for table in tables_data:
        sheet_name = table.get("sheet", table.get("name", "Unknown"))
        headers = table.get("headers", [])
        num_rows = table.get("rows", 0)
        
        if headers:
            summary_parts.append(
                f"Sheet '{sheet_name}' contains {num_rows} rows with columns: {', '.join(headers)}"
            )
    
    return "\n".join(summary_parts)
