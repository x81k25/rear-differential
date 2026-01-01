# app/services/file_service.py
"""File service for library file operations."""
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Service for file system operations on the media library."""

    def __init__(self):
        """Initialize the file service."""
        self.file_deletion_enabled = settings.REAR_DIFF_FILE_DELETION_ENABLED
        self.cache_path = settings.REAR_DIFF_MEDIA_CACHE_PATH.rstrip('/')
        self.library_path_movies = settings.REAR_DIFF_MEDIA_LIBRARY_PATH_MOVIES.rstrip('/')
        self.library_path_tv = settings.REAR_DIFF_MEDIA_LIBRARY_PATH_TV.rstrip('/')

    def _delete_path(self, path: str) -> Dict[str, Any]:
        """
        Delete a file or directory at the given path.

        Args:
            path: The filesystem path to delete

        Returns:
            Dictionary with deletion result
        """
        if not os.path.exists(path):
            logger.debug(f"Path does not exist: {path}")
            return {"exists": False, "deleted": False}

        try:
            path_obj = Path(path)

            if path_obj.is_file():
                path_obj.unlink()
                logger.debug(f"Deleted file: {path}")
            elif path_obj.is_dir():
                shutil.rmtree(path)
                logger.debug(f"Deleted directory: {path}")
            else:
                logger.debug(f"Path is neither file nor directory: {path}")
                return {"exists": True, "deleted": False, "error": "Not a file or directory"}

            return {"exists": True, "deleted": True, "path": path}

        except PermissionError as e:
            logger.debug(f"Permission denied deleting {path}: {e}")
            return {"exists": True, "deleted": False, "error": f"Permission denied: {path}"}
        except Exception as e:
            logger.debug(f"Error deleting {path}: {e}")
            return {"exists": True, "deleted": False, "error": str(e)}

    def delete_media(self, db_parent_path: str, db_target_path: str, media_type: str) -> Dict[str, Any]:
        """
        Delete media from all possible locations (cache/incomplete, cache/complete, library).

        Args:
            db_parent_path: The parent_path from atp.media table
            db_target_path: The target_path from atp.media table
            media_type: 'movie' or 'tv'

        Returns:
            Dictionary with success status and message/warning
        """
        if not self.file_deletion_enabled:
            logger.info("File deletion is disabled, skipping deletion")
            return {
                "success": True,
                "deleted": False,
                "message": "File deletion is disabled"
            }

        # Determine library path based on media type
        library_base = self.library_path_movies if media_type == 'movie' else self.library_path_tv

        # Build all paths to try
        paths_to_try: List[str] = []

        # 1. Cache incomplete path (no movies/tv subdirs in cache)
        if self.cache_path:
            incomplete_path = os.path.join(self.cache_path, 'incomplete', db_target_path)
            paths_to_try.append(incomplete_path)

        # 2. Cache complete path (no movies/tv subdirs in cache)
        if self.cache_path:
            complete_path = os.path.join(self.cache_path, 'complete', db_target_path)
            paths_to_try.append(complete_path)

        # 3. Library path (already includes movies/ or tv/ in the path)
        if library_base:
            library_path = os.path.join(library_base, db_target_path)
            paths_to_try.append(library_path)

        # Also try the original DB path directly
        full_db_path = os.path.join(db_parent_path, db_target_path)
        if full_db_path not in paths_to_try:
            paths_to_try.append(full_db_path)

        # Try all paths
        deleted_paths: List[str] = []
        for path in paths_to_try:
            result = self._delete_path(path)
            if result.get("deleted"):
                deleted_paths.append(path)
                logger.info(f"Successfully deleted: {path}")

        # Build response
        if deleted_paths:
            return {
                "success": True,
                "deleted": True,
                "message": f"Deleted {len(deleted_paths)} path(s)",
                "paths": deleted_paths
            }
        else:
            logger.debug(f"No files found to delete for {db_target_path}")
            return {
                "success": True,
                "deleted": False,
                "message": f"No files found in any location for: {db_target_path}"
            }

    # Keep old method name for backwards compatibility
    def delete_directory(self, db_parent_path: str, db_target_path: str) -> Dict[str, Any]:
        """
        Delete a media directory. Tries to detect media type from path.

        For new code, prefer delete_media() with explicit media_type.
        """
        # Detect media type from path
        media_type = 'movie' if '/movies' in db_parent_path else 'tv'
        return self.delete_media(db_parent_path, db_target_path, media_type)
