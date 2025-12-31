# app/services/file_service.py
"""File service for library file operations."""
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Service for file system operations on the media library."""

    def __init__(self):
        """Initialize the file service."""
        self.file_deletion_enabled = settings.REAR_DIFF_FILE_DELETION_ENABLED
        self.db_path_prefix = settings.REAR_DIFF_DB_PATH_PREFIX
        self.library_mount_path = settings.REAR_DIFF_LIBRARY_MOUNT_PATH

    def convert_db_path_to_library_path(self, db_parent_path: str, db_target_path: str) -> Optional[str]:
        """
        Convert database paths to library mount path.

        Database paths are like: /d/media-cache/dev/transfer/movies/movie-slug-2025
        Library paths are like:  /library/movies/movie-slug-2025

        Args:
            db_parent_path: The parent_path from atp.media table
            db_target_path: The target_path from atp.media table

        Returns:
            The converted library path, or None if conversion fails
        """
        try:
            # Combine parent_path and target_path
            full_db_path = os.path.join(db_parent_path, db_target_path)

            # Check if path starts with the expected prefix
            if not full_db_path.startswith(self.db_path_prefix):
                logger.warning(f"DB path does not start with expected prefix: {full_db_path}")
                return None

            # Extract the relative path after the prefix
            # e.g., /d/media-cache/dev/transfer/movies/slug -> movies/slug
            relative_path = full_db_path[len(self.db_path_prefix):].lstrip('/')

            # Construct the library path
            library_path = os.path.join(self.library_mount_path, relative_path)

            return library_path

        except Exception as e:
            logger.error(f"Error converting path: {e}")
            return None

    def delete_directory(self, db_parent_path: str, db_target_path: str) -> Dict[str, Any]:
        """
        Delete a media directory from the library.

        Args:
            db_parent_path: The parent_path from atp.media table
            db_target_path: The target_path from atp.media table

        Returns:
            Dictionary with success status and message/warning
        """
        # Check if file deletion is enabled
        if not self.file_deletion_enabled:
            logger.info("File deletion is disabled, skipping deletion")
            return {
                "success": True,
                "deleted": False,
                "message": "File deletion is disabled"
            }

        # Convert path
        library_path = self.convert_db_path_to_library_path(db_parent_path, db_target_path)

        if library_path is None:
            return {
                "success": False,
                "deleted": False,
                "warning": f"Could not convert path: {db_parent_path}/{db_target_path}"
            }

        # Check if path exists
        if not os.path.exists(library_path):
            logger.info(f"Path does not exist, nothing to delete: {library_path}")
            return {
                "success": True,
                "deleted": False,
                "message": f"Path does not exist: {library_path}"
            }

        # Attempt deletion
        try:
            path_obj = Path(library_path)

            if path_obj.is_file():
                path_obj.unlink()
                logger.info(f"Deleted file: {library_path}")
            elif path_obj.is_dir():
                shutil.rmtree(library_path)
                logger.info(f"Deleted directory: {library_path}")
            else:
                return {
                    "success": False,
                    "deleted": False,
                    "warning": f"Path is neither file nor directory: {library_path}"
                }

            return {
                "success": True,
                "deleted": True,
                "message": f"Successfully deleted: {library_path}",
                "path": library_path
            }

        except PermissionError as e:
            logger.warning(f"Permission denied deleting {library_path}: {e}")
            return {
                "success": False,
                "deleted": False,
                "warning": f"Permission denied: {library_path}"
            }
        except Exception as e:
            logger.warning(f"Error deleting {library_path}: {e}")
            return {
                "success": False,
                "deleted": False,
                "warning": f"Deletion failed: {str(e)}"
            }
