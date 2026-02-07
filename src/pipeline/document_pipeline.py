"""
Document Processing Pipeline ⚡
==============================

This module contains the core business logic for the DocuMind system.
It acts as the central orchestrator that takes a raw file and transforms it
into structured, searchable data.

The Pipeline Workflow:
----------------------
1. **Input Type Detection**: Identifies if the input is a file, URL, or YouTube link.
2. **Extraction**: Delegates to the specific extractor in `src/extractors/`.
3. **Smart Image Analysis**:
   - Runs OCR (Optical Character Recognition) on all extracted images.
   - If OCR confidence is high, it uses the text.
   - If OCR confidence is low, it falls back to VLM (Vision Language Model).
4. **Asset Management**: Saves all extracted images to a persistent assets folder.
5. **Structuring**: Uses an LLM Agent to organize the data into JSON.
6. **Persistence**:
   - Saves structured data to `MongoDB`.
   - Index chunks into `VectorDB` for RAG.

Supported Inputs:
- Files: PDF, DOCX, XLSX, XLS, CSV, PPTX, Images, Video, Audio
- URLs: Web pages (scraped)
- YouTube: Video transcription via Whisper

"""

import json
import os

from extractors.excel_extractor import extract_csv, extract_excel
from extractors.image_extractor import extract_image
from extractors.media_extractor import extract_media
from extractors.pdf_extractor import extract_pdf
from extractors.ppt_extractor import extract_ppt
from extractors.url_extractor import extract_url
from extractors.word_extractor import extract_word
from extractors.youtube_extractor import extract_youtube
from services.llm_service import analyze_tables_with_llm, run_agent
from services.media_service import is_media_file


async def pipeline(
    file_path=None,
    url=None,
    youtube_url=None,
    author="",
    use_ocr_vlm=True,
    save_to_mongo=True,
    session_id=None,
    user_description=None,
):
    """
    Execute the main document processing pipeline (Async).

    This function is the entry point for processing a single input. It handles
    file extraction, URL scraping, YouTube transcription, OCR/VLM/LLM processing,
    and data persistence. All input types converge into the same processing flow.

    Args:
        file_path (str, optional): Absolute path to the file to be processed.
        url (str, optional): Web URL to scrape and process.
        youtube_url (str, optional): YouTube video URL to transcribe.
        author (str): Name of the document author (metadata).
        use_ocr_vlm (bool): If True, enables OCR and VLM processing for images.
        save_to_mongo (bool): If True, saves the final result to MongoDB.
        session_id (str, optional): Unique ID to group files (e.g., a single upload batch).
        user_description (str, optional): Custom description provided by user during upload.

    Returns:
        tuple:
            - base_dir (str): The directory where artifacts for this doc are stored.
            - result_ref (str): The MongoDB ObjectId (if saved) or the path to the JSON.

    Raises:
        ValueError: If the input type is not supported or no input provided.
    """
    # Determine input type and get file extension if applicable
    input_type = None
    ext = None

    if youtube_url:
        input_type = "youtube"
        print(f"🎬 Processing YouTube URL: {youtube_url}")
    elif url:
        input_type = "url"
        print(f"🌐 Processing Web URL: {url}")
    elif file_path:
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        # Check if it's a media file
        if is_media_file(file_path):
            input_type = "media"
            print(f"🎬 Processing media file: {os.path.basename(file_path)}")
        else:
            input_type = "file"
    else:
        raise ValueError("No input provided. Specify file_path, url, or youtube_url.")

    # =======================================================================
    # ENHANCEMENT: Fast-Track Indexing (Skip Processing for Re-uploads) ⚡
    # Only applicable for file inputs
    # =======================================================================
    file_hash = None
    if input_type in ["file", "media"] and file_path:
        from services.db_service import get_document_by_hash, save_to_mongodb
        from services.memory_service import (
            check_hash_exists,
            get_chunks_by_hash,
            index_chunks,
        )
        from utils.file_utils import calculate_file_hash

        file_hash = calculate_file_hash(file_path)

        # 1. Check if hash exists in CURRENT SESSION (exact duplicate in same session)
        if check_hash_exists(file_hash, session_id=session_id):
            print(f"♻️ File already indexed in this session {session_id}. Skipping.")
            return "fast_tracked", session_id

        # 2. Check if hash exists GLOBALLY (file uploaded by another user/session)
        if check_hash_exists(file_hash):
            print(
                f"⚡ File exists globally. Fast-tracking indexing for session {session_id}..."
            )

            # A. Copy ChromaDB chunks with new session_id
            data = get_chunks_by_hash(file_hash)
            if data and data.get("chunks"):
                # Get original source_id from first chunk's metadata
                original_source_id = (
                    data["metadata"][0].get("source_id", "unknown")
                    if data["metadata"]
                    else "unknown"
                )

                new_metadata = []
                for meta in data["metadata"]:
                    new_meta = meta.copy()
                    new_meta["session_id"] = session_id or "default"
                    new_metadata.append(new_meta)

                index_chunks(data["chunks"], metadata=new_metadata)
                print(
                    f"✅ Instant RAG indexing complete (Copied {len(data['chunks'])} chunks)"
                )

                # B. Copy MongoDB record if available
                existing_doc = get_document_by_hash(file_hash)
                if existing_doc:
                    temp_parsed_path = os.path.join(
                        os.path.dirname(file_path), "temp_structured.json"
                    )
                    with open(temp_parsed_path, "w", encoding="utf-8") as f:
                        json.dump(existing_doc, f, indent=2, ensure_ascii=False)

                    mongo_id = save_to_mongodb(temp_parsed_path, session_id=session_id)
                    os.remove(temp_parsed_path)
                    print(f"✅ Instant MongoDB entry created (Session: {session_id})")

                # Return original source_id so controller can use it
                return original_source_id, session_id

    # For URL inputs, generate a hash from the URL
    elif input_type == "url" and url:
        import hashlib

        file_hash = hashlib.md5(url.encode()).hexdigest()
    elif input_type == "youtube" and youtube_url:
        import hashlib

        file_hash = hashlib.md5(youtube_url.encode()).hexdigest()

    if input_type == "file":
        print(f"🆕 Processing new file: {os.path.basename(file_path)}...")
    # =======================================================================

    # Initialize variables before extraction (defensive programming)
    base = None
    images = []
    doc_id = None
    source = None

    # =======================================================================
    # ROUTE TO APPROPRIATE EXTRACTOR
    # =======================================================================

    # --- YouTube URL ---
    if input_type == "youtube":
        base, images, doc_id, source = extract_youtube(youtube_url)

    # --- Web URL ---
    elif input_type == "url":
        base, images, doc_id, source = extract_url(url)

    # --- Media File (Video/Audio) ---
    elif input_type == "media":
        base, images, doc_id, source = extract_media(file_path)

    # --- Document Files ---
    elif input_type == "file":
        if ext == ".docx":
            base, images, doc_id, source = extract_word(file_path)
        elif ext == ".pdf":
            base, images, doc_id, source = extract_pdf(file_path)
        elif ext == ".pptx":
            base, images, doc_id, source = extract_ppt(file_path)
        elif ext in [".xlsx", ".xls", ".xlsm"]:
            base, images, doc_id, source = extract_excel(file_path)
        elif ext == ".csv":
            base, images, doc_id, source = extract_csv(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]:
            base, images, doc_id, source = extract_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    else:
        raise ValueError(f"Unknown input type: {input_type}")

    # --- Save Extracted Images to Assets ---
    # !! DISABLED TO PREVENT DISK LOAD !!
    # --- Save Extracted Images to Assets ---
    # (Disabled: Images are currently processed in memory or temp)
    # ---------------------------------------
    # ---------------------------------------

    # --- Smart OCR/VLM Logic ---
    if use_ocr_vlm and images:
        from services.ocr_service import OCR_THRESHOLD, run_ocr_on_images_async

        # 1. Run OCR on all images first (async for better performance)
        ocr_results = await run_ocr_on_images_async(images)

        final_content_parts = []
        images_for_vlm = []
        ocr_success_results = []  # Store successful OCR results for MongoDB

        for res in ocr_results:
            path = res["path"]
            text = res["text"]
            conf = res["confidence"]

            # LOGIC: Determine if OCR was successful
            ocr_successful = conf >= OCR_THRESHOLD and text and len(text.strip()) >= 10

            if ocr_successful:
                # OCR succeeded - save to content and to structured results
                print(
                    f"✅ High OCR confidence ({conf:.2f}) for {os.path.basename(path)}. Skipping VLM."
                )
                final_content_parts.append(
                    f"[Image Text ({os.path.basename(path)}): {text}]"
                )

                # Store for MongoDB
                ocr_success_results.append(
                    {
                        "method": "ocr",
                        "image": os.path.basename(path),
                        "content_images": text.strip(),
                        "confidence": round(conf, 2),
                    }
                )
            else:
                # OCR failed or low confidence - queue for VLM
                print(
                    f"📉 Low OCR confidence ({conf:.2f}) for {os.path.basename(path)}. Queueing for VLM."
                )
                images_for_vlm.append(path)

        # 2. Save OCR results to JSON (for MongoDB inclusion)
        if ocr_success_results:
            ocr_analysis_path = os.path.join(base, "images", "ocr_analysis.json")
            os.makedirs(os.path.dirname(ocr_analysis_path), exist_ok=True)
            with open(ocr_analysis_path, "w", encoding="utf-8") as f:
                json.dump(ocr_success_results, f, indent=2, ensure_ascii=False)
            print(f"✅ OCR Analysis saved for {len(ocr_success_results)} images")

        # 3. Run VLM on selected low-confidence images
        if images_for_vlm:
            from services.vlm_service import analyze_extracted_images

            # Analyze (and auto-move to vlm_processed folder in service)
            vlm_results = analyze_extracted_images(base, images_for_vlm)

            # Add VLM descriptions to final content
            for v_res in vlm_results:
                desc = v_res.get("content_images", "")
                if desc:
                    final_content_parts.append(
                        f"[Image Description ({v_res['image']}): {desc}]"
                    )

        # 4. Save combined content to content.txt
        if final_content_parts:
            text_path = os.path.join(base, "text", "content.txt")
            os.makedirs(os.path.dirname(text_path), exist_ok=True)

            # Read existing text if any (e.g. from docx text)
            existing_text = ""
            if os.path.exists(text_path):
                with open(text_path, "r", encoding="utf-8") as f:
                    existing_text = f.read()

            # Append image insights
            combined_text = existing_text + "\n\n" + "\n\n".join(final_content_parts)

            with open(text_path, "w", encoding="utf-8") as f:
                f.write(combined_text)

    # ---------------------------

    # (Legacy VLM block removed - handled in Smart Loop above)

    # Auto-analyze tables for Excel and CSV files
    if source in ["excel", "csv"]:
        print("\n🔍 Analyzing tables with LLM...")
        await analyze_tables_with_llm(base)

    # Run agent AFTER table analysis (so it can include analysis.json)
    parsed_path, parsed_data = await run_agent(
        base,
        source,
        doc_id,
        file_hash,
        author=author,
        user_description=user_description,
    )

    # --- Save to MongoDB ---
    mongo_id = None
    if save_to_mongo:
        try:
            from services.db_service import save_to_mongodb

            mongo_id = save_to_mongodb(parsed_path, session_id=session_id)
        except Exception as e:
            print(f"⚠️ Failed to save to MongoDB: {e}")
    # -----------------------

    # --- RAG Indexing (with Hash Deduplication) ---
    try:
        from services.memory_service import check_hash_exists, index_chunks
        from services.rag_service import process_document_for_rag
        from utils.file_utils import calculate_file_hash

        # Calculate file hash for deduplication (only if not already set for URLs)
        if file_hash is None and file_path:
            file_hash = calculate_file_hash(file_path)

        # Check if this file was already indexed in ChromaDB
        if file_hash and check_hash_exists(file_hash):
            print(
                f"♻️ File already indexed in RAG (Hash: {file_hash[:12]}...). Skipping."
            )
        else:
            chunks = []
            metadata = []

            # Use row-based chunking for Excel/CSV files
            if source in ["excel", "csv"]:
                from services.rag_service import (
                    create_enhanced_excel_summary,
                    create_excel_chunks,
                )

                print("📊 Using row-based chunking for Excel/CSV file...")
                row_chunks, row_metadata = create_excel_chunks(base, source)

                if row_chunks:
                    # Add common metadata to each row
                    for meta in row_metadata:
                        meta.update(
                            {
                                "source": source,
                                "doc_id": doc_id,
                                "source_id": doc_id,  # Link chunks to their source file
                                "author": author,
                                "session_id": session_id or "default",
                                "file_hash": file_hash,
                                "chunk_type": "excel_row",
                            }
                        )

                    chunks = row_chunks
                    metadata = row_metadata
                    print(f"✅ Created {len(chunks)} row-based chunks from Excel/CSV")

                    # Optionally add a summary chunk for high-level context
                    summary = create_enhanced_excel_summary(base)
                    if summary:
                        chunks.append(summary)
                        metadata.append(
                            {
                                "source": source,
                                "doc_id": doc_id,
                                "source_id": doc_id,  # Link chunks to their source file
                                "author": author,
                                "session_id": session_id or "default",
                                "file_hash": file_hash,
                                "chunk_type": "excel_summary",
                            }
                        )

            # Use token-based chunking for other document types (PDF, DOCX, etc.)
            else:
                # OPTIMIZATION: Use cleaned content from LLM parsing if available
                final_text = ""
                if "parsed_data" in locals() and parsed_data.get("clean_content"):
                    print("🧹 Using cleaned content for RAG indexing...")
                    final_text = parsed_data["clean_content"]
                else:
                    # Fallback to content.txt if LLM content is not here
                    content_path = os.path.join(base, "text", "content.txt")
                    if os.path.exists(content_path):
                        with open(content_path, "r", encoding="utf-8") as f:
                            final_text = f.read()

                if final_text.strip():
                    # Use Token-based chunking by default
                    chunks = process_document_for_rag(final_text, method="token")

                    # Metadata for ChromaDB (include file_hash for deduplication)
                    metadata = [
                        {
                            "source": source,
                            "doc_id": doc_id,
                            "source_id": doc_id,  # Link chunks to their source file
                            "author": author,
                            "session_id": session_id or "default",
                            "file_hash": file_hash,
                            "chunk_type": "token",
                        }
                        for _ in chunks
                    ]

            # Index in ChromaDB
            if chunks:
                index_chunks(chunks, metadata=metadata, collection_name="global_memory")
                print(
                    f"✅ RAG indexed {len(chunks)} chunks (Hash: {file_hash[:12]}...)"
                )

    except Exception as e:
        print(f"⚠️ RAG Indexing failed: {e}")
    # -----------------------

    # Return the Mongo ID if available, otherwise the path
    result_ref = mongo_id if mongo_id else parsed_path
    return base, result_ref
