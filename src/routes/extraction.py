"""Document extraction API routes."""

import uuid
import os
import pathlib
import shutil

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from controllers.extraction_controller import ExtractionController
from schemas.extraction import ExtractionResponse
from worker.tasks import extraction_task

extraction_router = APIRouter(
    prefix="/api/v1/extract",
    tags=["extraction"],
)

SRC_DIR = pathlib.Path(__file__).parent.parent.resolve()

UPLOAD_DIR = SRC_DIR / "temp" / "uploads"


class AsyncExtractionResponse(BaseModel):
    """Response model for asynchronous extraction requests."""

    status: str
    task_id: str
    session_id: str
    message: str


@extraction_router.post("/", response_model=AsyncExtractionResponse)
async def extract_documents_async(
    files: Optional[List[UploadFile]] = File(None),
    links: Optional[List[str]] = Form(None),
    author: str = Form("Default Author"),
    use_ocr_vlm: bool = Form(True),
    session_id: str = Form(...),
    user_description: Optional[str] = Form(None),
    callback_url: Optional[str] = Form(None),
):
    """
    Async extraction: Uploads files or links (Web/YouTube) -> Saves to disk -> Queues Celery Task.
    Returns 202 Accepted immediately.

    Accepts:
    - files: Document files (PDF, DOCX, XLSX, etc.), media files (MP4, MP3, etc.)
    - links: List of URLs (Web pages or YouTube videos)

    At least one of files or links must be provided.
    """
    # Validate that at least one input is provided
    has_files = files and len(files) > 0 and files[0].filename
    has_links = links and len(links) > 0

    if not has_files and not has_links:
        raise HTTPException(
            status_code=400, detail="At least one input required: files or links"
        )

    saved_file_info = []

    try:
        # 1. Save files to disk so Celery can reach them (if provided)
        if has_files:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            for file in files:
                if not file.filename:
                    continue
                # Generate a unique safe filename
                safe_filename = f"{session_id}_{uuid.uuid4()}_{file.filename}"
                file_path = os.path.join(UPLOAD_DIR, safe_filename)

                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                saved_file_info.append(
                    {
                        "path": file_path,
                        "name": file.filename,
                        "type": file.content_type,
                    }
                )

        # 2. Prepare Payload with Links support
        task_payload = {
            "file_paths": saved_file_info,
            "links": links if has_links else [],
            "author": author,
            "use_ocr_vlm": use_ocr_vlm,
            "session_id": session_id,
            "user_description": user_description,
            "callback_url": callback_url,
        }

        # 3. Trigger Celery Task
        task = extraction_task.delay(task_payload)

        # Build response message
        input_types = []
        if has_files:
            input_types.append(f"{len(saved_file_info)} file(s)")
        if has_links:
            input_types.append(f"{len(links)} link(s)")

        return {
            "status": "queued",
            "task_id": task.id,
            "session_id": session_id,
            "message": f"Extraction queued for {', '.join(input_types)}.",
        }

    except Exception as e:
        # Cleanup if something fails *before* queueing
        for info in saved_file_info:
            if os.path.exists(info["path"]):
                os.remove(info["path"])
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")
