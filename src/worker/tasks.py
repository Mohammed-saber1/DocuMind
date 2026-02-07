import os
import asyncio
import httpx
import logging
from worker.celery_app import celery_app
from controllers.extraction_controller import ExtractionController
from core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


# --- 1. Helper to Mock UploadFile in Celery ---
class CeleryUploadFile:
    """
    Mimics FastAPI's UploadFile for the Controller,
    but reads from a local disk path.
    """

    def __init__(
        self,
        file_path: str,
        filename: str,
        content_type: str = "application/octet-stream",
    ):
        self.file_path = file_path
        self.filename = filename
        self.content_type = content_type
        self.file = open(file_path, "rb")  # Open the actual file

    async def read(self, size: int = -1):
        return self.file.read(size)

    async def seek(self, offset: int):
        self.file.seek(offset)

    async def close(self):
        self.file.close()


# --- 2. The Celery Task ---
@celery_app.task(bind=True, queue="extraction_queue")
def extraction_task(self, task_payload: dict):
    """
    Handles document extraction asynchronously.
    Payload expects: {
        "file_paths": [{"path": str, "name": str, "type": str}],
        "url": str (optional),
        "youtube_url": str (optional),
        "author": str,
        "use_ocr_vlm": bool,
        "session_id": str,
        "user_description": str,
        "callback_url": str
    }
    """
    session_id = task_payload.get("session_id")
    callback_url = (
        task_payload.get("callback_url") or settings.worker.backend_callback_url
    )

    # 🔧 Validate and Fix Callback URL early
    if not callback_url:
        logger.warning(
            "⚠️ No callback_url provided and no default setting found. Callback will be skipped."
        )
    else:
        logger.info(f"Using callback_url: {callback_url}")
        if not callback_url.startswith("http"):
            callback_url = "https://" + callback_url
            logger.info(
                f"🔧 meaningful callback_url updated with protocol: {callback_url}"
            )

    file_paths = task_payload.get("file_paths", [])
    links = task_payload.get("links", [])

    logger.info(
        f"🚀 Extraction Task started | Session: {session_id} | Files: {len(file_paths)} | Links: {len(links)}"
    )

    # Reconstruct "UploadFile" objects from disk paths
    mock_files = []
    for f in file_paths:
        mock_files.append(CeleryUploadFile(f["path"], f["name"], f["type"]))

    try:
        # Initialize Controller
        controller = ExtractionController()

        # Run the async process
        # We wrap it in asyncio.run because Celery is synchronous by default
        result = asyncio.run(
            controller.process_documents(
                files=mock_files if mock_files else None,
                links=links,
                author=task_payload.get("author"),
                use_ocr_vlm=task_payload.get("use_ocr_vlm"),
                session_id=session_id,
                user_description=task_payload.get("user_description"),
            )
        )

        logger.info(f"📊 Extraction complete | Session: {session_id}")

        # Send Success Callback
        if callback_url:
            response = httpx.post(
                callback_url,
                json=(
                    result.dict() if hasattr(result, "dict") else result
                ),  # Ensure it's JSON serializable
                headers={"Authorization": "Bearer ai_worker_token"},
                timeout=120,
            )
            logger.info(f"✅ Callback sent | Status: {response.status_code}")

    except Exception as e:
        logger.error(f"❌ Extraction failed | Session: {session_id} | Error: {e}")
        # Send Failure Callback
        try:
            httpx.post(
                callback_url,
                json={"session_id": session_id, "status": "failed", "error": str(e)},
                timeout=30,
            )
        except Exception as cb_err:
            logger.error(f"❌ Callback also failed: {cb_err}")

        raise e  # Re-raise to mark task as failed in Celery

    finally:
        # --- CRITICAL: CLEANUP ---
        # Close file handles and delete temp files to save disk space
        for mf in mock_files:
            try:
                mf.file.close()  # Close file handle directly
                if os.path.exists(mf.file_path):
                    os.remove(mf.file_path)
                    logger.info(f"🧹 Deleted temp file: {mf.file_path}")
            except Exception as cleanup_err:
                logger.warning(f"⚠️ Cleanup failed for {mf.file_path}: {cleanup_err}")

    return {"status": "done", "session_id": session_id}
