"""
Extraction Controller 🎮
========================

This module implements the `ExtractionController` class, which serves as the bridge
between the API (FastAPI routes) and the business logic (Document Pipeline).

Responsibilities:
-----------------
- **Input Validation**: Ensures at least one input (files, URL, or YouTube) is provided.
- **Session Management**: Generates or validates `session_id` to group related documents.
- **Orchestration**: Iterates over uploaded files and URLs, sending them to the pipeline.
- **Batch Processing**: Aggregates results from multiple inputs into a single MongoDB batch document.
- **Error Handling**: Catches exceptions per input so that one failure doesn't stop the whole batch.

Supported Inputs:
- Files: Documents (PDF, DOCX, etc.), Media files (MP4, MP3, etc.)
- URLs: Web pages to scrape
- YouTube: Videos to transcribe

"""
import os
import shutil
import uuid
from typing import List, Optional
from fastapi import UploadFile

from controllers.base_controller import BaseController
from pipeline.document_pipeline import pipeline
from services.db_service import save_batch_to_mongodb


class ExtractionController(BaseController):
    """
    Controller for handling document extraction API requests.
    Inherits from BaseController for shared utilities (temp dir management, etc.).
    """
    
    async def process_documents(
        self,
        files: Optional[List[UploadFile]] = None,
        links: Optional[List[str]] = None,
        author: str = "Default Author",
        use_ocr_vlm: bool = True,
        session_id: str = None,
        user_description: str = None
    ) -> dict:
        """
        Process a batch of uploaded documents and links (Web/YouTube) asynchronously.
        
        Args:
            files: List of uploaded files (optional)
            links: List of URLs (Web pages of YouTube videos)
            author: Document author metadata
            use_ocr_vlm: Whether to use OCR/VLM processing
            session_id: Session identifier for grouping
            user_description: User-provided description
            
        Returns:
            Dict with session_id, batch_mongo_id, processed_count, and documents status
        """
        import asyncio
        
        # Generate session ID if not provided
        if not session_id:
            session_id = self.generate_session_id()
        
        tasks = []
        file_maps = []
        temp_paths_to_clean = []
        
        temp_paths_to_clean = []
        
        # --- Process Files ---
        if files:
            for file in files:
                if not hasattr(file, 'filename') or not file.filename:
                    continue
                    
                # Create unique filename to avoid collisions
                unique_id = uuid.uuid4().hex[:8]
                filename = f"{unique_id}_{file.filename}"
                temp_path = os.path.join(self.temp_dir, filename)
                
                # Save uploaded file temporarily
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                print(f"🚀 Queueing file: {file.filename} (Session: {session_id})")
                
                # Add to task list (pipeline is now async)
                tasks.append(pipeline(
                    file_path=temp_path,
                    author=author,
                    use_ocr_vlm=use_ocr_vlm,
                    save_to_mongo=False,  # We save batch at the end
                    session_id=session_id,
                    user_description=user_description
                ))
                file_maps.append({"name": file.filename, "type": "file"})
                temp_paths_to_clean.append(temp_path)
        
        # --- Process Links (Web & YouTube) ---
        if links:
            import json
            expanded_links = []
            
            # First pass: Handle potential JSON stringified lists (e.g. '["url1", "url2"]')
            for link_item in links:
                if not link_item:
                    continue
                s_link = link_item.strip()
                # Check if it looks like a JSON list
                if s_link.startswith("[") and s_link.endswith("]"):
                    try:
                        parsed = json.loads(s_link)
                        if isinstance(parsed, list):
                            expanded_links.extend([str(l) for l in parsed])
                        else:
                            expanded_links.append(s_link)
                    except Exception:
                        expanded_links.append(s_link) # Fallback if parse fails
                else:
                    expanded_links.append(s_link)
            
            # Second pass: Process individual valid links
            for link in expanded_links:
                link = link.strip().strip('"').strip("'")
                if not link:
                    continue
                    
                # Auto-detect YouTube URL
                is_youtube = "youtube.com" in link.lower() or "youtu.be" in link.lower()
                
                if is_youtube:
                    print(f"📺 Queueing YouTube: {link} (Session: {session_id})")
                    tasks.append(pipeline(
                        youtube_url=link,
                        author=author,
                        use_ocr_vlm=use_ocr_vlm,
                        save_to_mongo=False,
                        session_id=session_id,
                        user_description=user_description
                    ))
                    file_maps.append({"name": link, "type": "youtube"})
                else:
                    print(f"🌐 Queueing URL: {link} (Session: {session_id})")
                    tasks.append(pipeline(
                        url=link,
                        author=author,
                        use_ocr_vlm=use_ocr_vlm,
                        save_to_mongo=False,
                        session_id=session_id,
                        user_description=user_description
                    ))
                    file_maps.append({"name": link, "type": "url"})
        
        # Validate we have at least one task
        if not tasks:
            return {
                "session_id": session_id,
                "batch_mongo_id": None,
                "processed_count": 0,
                "documents": [],
                "error": "No valid inputs provided"
            }

        # Run all extractions in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        documents_status = []
        json_paths = []
        
        for idx, result in enumerate(results):
            input_info = file_maps[idx]
            input_name = input_info["name"]
            input_type = input_info["type"]
            
            if isinstance(result, Exception):
                print(f"❌ Error processing {input_name}: {result}")
                documents_status.append({
                    "filename": input_name,
                    "input_type": input_type,
                    "status": "error",
                    "error": str(result)
                })
            else:
                base_dir, parsed_path = result
                
                # Handle Fast-Track case: base_dir will be original source_id (uuid_filename format)
                # Normal case: base_dir is a directory path
                if os.path.isdir(str(base_dir)) if base_dir else False:
                    source_id_result = os.path.basename(base_dir)
                    json_paths.append(parsed_path)
                    is_fast_tracked = False
                    # Add base_dir to cleanup list to delete all temp artifacts
                    temp_paths_to_clean.append(base_dir)
                else:
                    # Fast-tracked: base_dir is already the source_id
                    source_id_result = base_dir
                    is_fast_tracked = True
                    
                documents_status.append({
                    "filename": input_name,
                    "input_type": input_type,
                    "source_id": source_id_result,
                    "status": "success",
                    "fast_tracked": is_fast_tracked
                })

        # Save aggregated batch to MongoDB (only for newly processed files)
        batch_mongo_id = None
        if json_paths:
            try:
                batch_mongo_id = save_batch_to_mongodb(
                    json_paths, 
                    session_id, 
                    author
                )
            except Exception as e:
                print(f"⚠️ Batch MongoDB Save failed: {e}")
        
        # For fast-tracked files, the batch_mongo_id was already created by pipeline
        # So we use session_id as the reference
        if not batch_mongo_id and any(d.get("fast_tracked") for d in documents_status):
            batch_mongo_id = session_id
        
        # Clean up temporary files AND directories
        for temp_path in temp_paths_to_clean:
            if os.path.exists(temp_path):
                if os.path.isdir(temp_path):
                    shutil.rmtree(temp_path)
                else:
                    os.remove(temp_path)

        # Count all successful documents (including fast-tracked)
        success_count = len([d for d in documents_status if d["status"] == "success"])

        return {
            "session_id": session_id,
            "batch_mongo_id": batch_mongo_id,
            "processed_count": success_count,
            "documents": documents_status
        }

