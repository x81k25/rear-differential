# app/routers/training.py
import logging
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from app.models.api import TrainingListResponse, TrainingUpdateRequest, TrainingUpdateResponse, MediaType, LabelType
from app.services.db_service import DatabaseService
from app.services.file_service import FileService
from app.services.transmission_service import TransmissionService

logger = logging.getLogger(__name__)

def get_router():
    router = APIRouter()
    db_service = DatabaseService()
    file_service = FileService()
    transmission_service = TransmissionService()

    @router.get("", response_model=TrainingListResponse)
    async def get_training_data(
        media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
        label: Optional[LabelType] = Query(None, description="Filter by label"),
        reviewed: Optional[bool] = Query(None, description="Filter by reviewed status"),
        human_labeled: Optional[bool] = Query(None, description="Filter by human labeled status"),
        anomalous: Optional[bool] = Query(None, description="Filter by anomalous status"),
        imdb_id: Optional[str] = Query(None, description="Filter by specific IMDB ID(s). Single ID or comma-separated list (e.g., 'tt1234567' or 'tt1234567,tt7654321')"),
        media_title: Optional[str] = Query(None, description="Filter by media title (partial match, case-insensitive)"),
        limit: int = Query(100, description="Maximum number of records to return"),
        offset: int = Query(0, description="Number of records to skip"),
        sort_by: str = Query("created_at", description="Field to sort results by"),
        sort_order: str = Query("desc", description="Direction of sort ('asc' or 'desc')")
    ):
        """
        Retrieve training data entries from the database with optional filtering and pagination.
        """
        try:
            # Parse imdb_id parameter - handle single ID or comma-separated list
            imdb_ids = None
            if imdb_id:
                # Split by comma and strip whitespace, filter out empty strings
                imdb_ids = [id.strip() for id in imdb_id.split(',') if id.strip()]
            
            result = db_service.get_training_data(
                media_type=media_type.value if media_type else None,
                label=label.value if label else None,
                reviewed=reviewed,
                human_labeled=human_labeled,
                anomalous=anomalous,
                imdb_ids=imdb_ids,
                media_title=media_title,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            )
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"error": "Database error occurred", "details": str(e)}
            )

    @router.patch("/{imdb_id}", response_model=TrainingUpdateResponse)
    async def update_training(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)"),
        request: TrainingUpdateRequest = None
    ):
        """
        Update training data fields for a specific entry.
        Can update label, human_labeled, anomalous, and reviewed fields.
        When label is updated, human_labeled and reviewed are automatically set to True.
        """
        # Validate that path imdb_id matches request body imdb_id
        if request.imdb_id != imdb_id:
            return {
                "success": False,
                "error": "IMDB ID mismatch",
                "message": "Path IMDB ID and body IMDB ID do not match"
            }

        # Call the new update method with all possible fields
        result = db_service.update_training_fields(
            imdb_id=imdb_id,
            label=request.label.value if request.label else None,
            human_labeled=request.human_labeled,
            anomalous=request.anomalous,
            reviewed=request.reviewed
        )

        if not result.get("success", False):
            status_code = 404 if result.get("error") == "Training data not found" else 500
            return result

        return result

    @router.patch("/{imdb_id}/reject", response_model=TrainingUpdateResponse)
    async def reject_training(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)")
    ):
        """
        Reject a media item by setting label to would_not_watch and deleting associated files.

        This endpoint:
        1. Sets label to 'would_not_watch'
        2. Sets human_labeled and reviewed to True
        3. Attempts to delete media files from the library (if enabled)
        """
        # Update label to would_not_watch
        result = db_service.update_training_fields(
            imdb_id=imdb_id,
            label="would_not_watch"
        )

        if not result.get("success", False):
            if result.get("error") == "Training data not found":
                raise HTTPException(status_code=404, detail=result)
            return result

        # Attempt file deletion
        path_result = db_service.get_media_path_by_imdb_id(imdb_id)
        original_link = None

        if path_result.get("success"):
            path_data = path_result["data"]
            parent_path = path_data.get("parent_path")
            target_path = path_data.get("target_path")
            original_link = path_data.get("original_link")

            if parent_path and target_path:
                deletion_result = file_service.delete_directory(parent_path, target_path)

                if deletion_result.get("deleted"):
                    result["file_deleted"] = True
                    logger.info(f"Deleted files for {imdb_id}: {deletion_result.get('path')}")
                elif deletion_result.get("warning"):
                    result["file_deleted"] = False
                    result["file_deletion_warning"] = deletion_result["warning"]
                    logger.warning(f"File deletion warning for {imdb_id}: {deletion_result['warning']}")
                else:
                    # Deletion disabled or path doesn't exist
                    result["file_deleted"] = False
                    if deletion_result.get("message"):
                        result["file_deletion_warning"] = deletion_result["message"]
            else:
                result["file_deleted"] = False
                result["file_deletion_warning"] = "No path information available in media table"
        else:
            result["file_deleted"] = False
            result["file_deletion_warning"] = path_result.get("message", "Could not retrieve media path")

        # Attempt torrent removal from Transmission
        result["torrent_removed"] = False
        if original_link:
            # Extract hash from original_link (last segment of URL path)
            try:
                torrent_hash = original_link.rstrip('/').split('/')[-1]
                if torrent_hash:
                    torrent_result = transmission_service.remove_torrent(torrent_hash, delete_data=False)
                    result["torrent_removed"] = torrent_result.get("found", False)
                    if torrent_result.get("found"):
                        logger.debug(f"Removed torrent for {imdb_id}: {torrent_hash}")
                    else:
                        logger.debug(f"Torrent not found in Transmission for {imdb_id}: {torrent_hash}")
            except Exception as e:
                logger.debug(f"Error removing torrent for {imdb_id}: {e}")
        else:
            logger.debug(f"No original_link found for {imdb_id}, skipping torrent removal")

        return result

    return router