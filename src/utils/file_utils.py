"""File and folder utility functions for document extraction."""

import json
import os
import uuid


def create_document_folder(file_path: str):
    """
    Create folder structure for extracted document.

    Returns:
        tuple: (doc_name, base_dir, text_dir, image_dir)
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    short_id = str(uuid.uuid4())[:8]
    doc_name = f"{base_name}__{short_id}"

    base_dir = os.path.join("temp", "documents", doc_name)
    text_dir = os.path.join(base_dir, "text")
    image_dir = os.path.join(base_dir, "images")

    os.makedirs(text_dir, exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)

    return doc_name, base_dir, text_dir, image_dir


def save_text(text_dir, text):
    """Save extracted text to content.txt file."""
    path = os.path.join(text_dir, "content.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.strip())
    return path


def save_metadata(base_dir, metadata):
    """Save document metadata to JSON file."""
    with open(os.path.join(base_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def save_tables(base_dir, tables_data):
    """Save extracted tables as JSON."""
    tables_dir = os.path.join(base_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)

    with open(os.path.join(tables_dir, "tables.json"), "w", encoding="utf-8") as f:
        json.dump(tables_data, f, indent=2, ensure_ascii=False)


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA-256 hash of a file's content.
    Used for RAG deduplication.
    """
    import hashlib

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
