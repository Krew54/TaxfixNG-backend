"""
Local file storage utilities for document management.
Replaces S3 storage with local file system storage.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status


class LocalStorageManager:
    """Manages local file storage for document uploads"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize storage manager
        
        Args:
            storage_path: Base path for stored files. Defaults to /app/storage
        """
        self.storage_path = Path(storage_path or os.environ.get("STORAGE_PATH", "/app/storage"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def get_user_storage_path(self, user_email: str) -> Path:
        """Get the storage path for a specific user"""
        user_path = self.storage_path / user_email
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path
    
    def save_file(self, file_content: bytes, user_email: str, filename: str) -> str:
        """
        Save a file to local storage
        
        Args:
            file_content: Binary content of the file
            user_email: Email of the user uploading the file
            filename: Original filename
            
        Returns:
            Relative path to the stored file
        """
        try:
            user_path = self.get_user_storage_path(user_email)
            file_path = user_path / filename
            
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Return relative path for storage in database
            return str(file_path.relative_to(self.storage_path))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    def get_file_path(self, relative_path: str) -> Optional[Path]:
        """
        Get the full file path from a relative path stored in database
        
        Args:
            relative_path: Relative path stored in database
            
        Returns:
            Full path to the file if it exists, None otherwise
        """
        full_path = self.storage_path / relative_path
        
        # Security check: ensure the path is within storage directory
        try:
            full_path.resolve().relative_to(self.storage_path.resolve())
        except ValueError:
            return None
        
        if full_path.exists():
            return full_path
        return None
    
    def get_public_url(self, relative_path: str) -> str:
        """
        Generate a public URL for accessing the file
        
        Args:
            relative_path: Relative path stored in database
            
        Returns:
            Public URL for the file
        """
        # Format: /api/documents/files/{relative_path}
        # This assumes an endpoint is created to serve files
        return f"/api/documents/files/{relative_path}"
    
    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            relative_path: Relative path stored in database
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            file_path = self.get_file_path(relative_path)
            if file_path:
                file_path.unlink()
                
                # Try to remove empty user directory
                user_dir = file_path.parent
                try:
                    if user_dir.exists() and not any(user_dir.iterdir()):
                        user_dir.rmdir()
                except OSError:
                    pass
                
                return True
            return False
        except Exception:
            return False
    
    def cleanup_user_storage(self, user_email: str) -> bool:
        """
        Clean up all files for a user (e.g., on account deletion)
        
        Args:
            user_email: Email of the user
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            user_path = self.storage_path / user_email
            if user_path.exists():
                shutil.rmtree(user_path)
            return True
        except Exception:
            return False
