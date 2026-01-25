"""
Base controller with shared functionality.

All controllers should inherit from this class to access
common utilities and configuration.
"""
import os
import random
import string
from core.config import get_settings, Settings


class BaseController:
    """Base class for all controllers."""
    
    def __init__(self):
        """Initialize controller with settings and directories."""
        self.settings: Settings = get_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.files_dir = os.path.join(self.base_dir, "assets", "files")
        self.temp_dir = os.path.join(self.base_dir, "temp", "uploads")
        
        # Ensure directories exist
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def generate_random_string(self, length: int = 12) -> str:
        """
        Generate a random alphanumeric string.
        
        Args:
            length: Length of the string to generate
            
        Returns:
            Random string of specified length
        """
        return ''.join(random.choices(
            string.ascii_lowercase + string.digits, 
            k=length
        ))
    
    def generate_session_id(self) -> str:
        """
        Generate a unique session ID.
        
        Returns:
            Session ID in format 'sess_xxxxxxxx'
        """
        return f"sess_{self.generate_random_string(8)}"
