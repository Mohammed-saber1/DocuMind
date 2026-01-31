import os
import logging
from typing import List, Optional
from controllers.base_controller import BaseController
from core.config import Settings
from llama_index.core import Document
from controllers.project_controller import ProjectController
from llama_parse import LlamaParse

import sys
import os
import logging

try:
    from models.asset import Asset
except ImportError:
    logging.warning(f"⚠️ Import 'models' failed. CWD: {os.getcwd()}")
    logging.warning(f"⚠️ sys.path: {sys.path}")
    
    # Attempt to fix path by adding the src directory (parent of controllers)
    current_dir = os.path.dirname(os.path.abspath(__file__)) # src/controllers
    src_dir = os.path.dirname(current_dir) # src
    if src_dir not in sys.path:
        sys.path.append(src_dir)
        logging.warning(f"🔧 Added {src_dir} to sys.path")
    
    try:
        from models.asset import Asset
        logging.warning("✅ Import 'models' succeeded after path fix")
    except ImportError as e:
        logging.error(f"❌ Import 'models' failed AGAIN: {e}")
        # Try relative as last resort (though we know it might fail for top-level)
        try:
            from ..models.asset import Asset
        except ImportError:
            raise e


from utils.timeout import async_timeout_wrapper

class Parser(BaseController):
    
    def __init__(self, settings: Settings):
        super().__init__() # BaseController.__init__ doesn't take settings in the existing code, it grabs them itself
        
        self.logger = logging.getLogger("uvicorn.error")
        self.timeout = self.settings.TIMEOUT_PARSE_DOCUMENT
        self.project_controller = ProjectController(settings=settings)
        
        self.parser = LlamaParse(
            api_key=settings.LLAMA_CLOUD_API_KEY,
            # tier=settings.LLAMA_CLOUD_TIER_PARSING, # Unused in latest LlamaParse
            # precise_bounding_box=True, # Unused in latest LlamaParse
            # version="latest",
            # session_id=... # Optional, maybe needed later
            # version="latest", # type: ignore
            show_progress=False,
        )
        
    async def parse_document(
        self, 
        project_id: int,
        assets: List[Asset],
    ) -> Optional[List[List[Document]]]:
        project_path = self.project_controller.get_project_path(project_id=project_id)
        files_paths = [os.path.join(project_path, str(asset.asset_name)) for asset in assets]
        return await self.parse_files(files_paths, project_id=project_id)

    async def parse_files(
        self, 
        files_paths: List[str],
        project_id: int = 0
    ) -> Optional[List[List[Document]]]:
        
        self.logger.info(f"Start: parsing {len(files_paths)} files, project_id: {project_id}")
        
        async def _parse_coro():
            return await self.parser.aload_data(file_path=files_paths)
        
        timeout_seconds = self.timeout * len(files_paths)
        
        results = await async_timeout_wrapper(
            coro=_parse_coro(),
            timeout=timeout_seconds,
            operation_name=f"Parse {len(files_paths)} documents",
        )
        
        if not results:
            self.logger.error("Document parsing failed or timed out")
            return None
            
        self.logger.info(f"End: parsing the document, project_id: {project_id}")

        # Wrap in list to match original signature List[List[Document]]
        # (Assuming the caller expects a list of 'pages' or documents per asset, 
        # but here we just return one list of all chunked documents/nodes from LlamaParse)
        return [results]
