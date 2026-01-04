# app/routers/training.py
import logging
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from app.models.api import TrainingListResponse, TrainingUpdateRequest, TrainingUpdateResponse, MetadataRerunResponse, MediaType, LabelType
from app.services.db_service import DatabaseService
from app.services.file_service import FileService
from app.services.transmission_service import TransmissionService
from app.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)

def get_router():
    router = APIRouter()
    db_service = DatabaseService()
    file_service = FileService()
    transmission_service = TransmissionService()
    metadata_service = MetadataService()

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

    @router.patch("/{imdb_id}/would_not_watch", response_model=TrainingUpdateResponse)
    async def would_not_watch_training(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)")
    ):
        """
        Mark a media item as would_not_watch and delete associated files.

        This endpoint:
        1. Sets label to 'would_not_watch'
        2. Sets human_labeled and reviewed to True
        3. Attempts to delete media files from the library (if enabled)
        4. Attempts to remove torrent from Transmission
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
                torrent_hash = original_link.rstrip('/').split('/')[-1].lower()
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

    @router.patch("/{imdb_id}/would_watch", response_model=TrainingUpdateResponse)
    async def would_watch_training(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)")
    ):
        """
        Mark a media item as would_watch.

        This endpoint:
        1. Sets label to 'would_watch'
        2. Sets human_labeled and reviewed to True
        """
        result = db_service.update_training_fields(
            imdb_id=imdb_id,
            label="would_watch"
        )

        if not result.get("success", False):
            if result.get("error") == "Training data not found":
                raise HTTPException(status_code=404, detail=result)
            return result

        return result

    @router.patch("/{imdb_id}/rerun_metadata", response_model=MetadataRerunResponse)
    async def rerun_metadata(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)")
    ):
        """
        Re-collect metadata from TMDB and OMDB APIs for an existing training record.

        This endpoint:
        1. Looks up the training record by IMDB ID
        2. Fetches fresh metadata from TMDB (using tmdb_id if available)
        3. Fetches fresh ratings from OMDB (using imdb_id)
        4. Updates the training record with new metadata
        """
        # Get existing training record
        training_result = db_service.get_training_by_imdb_id(imdb_id)

        if not training_result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": training_result.get("message", "Training data not found"),
                    "imdb_id": imdb_id,
                    "error": training_result.get("error")
                }
            )

        training_data = training_result["data"]
        tmdb_id = training_data.get("tmdb_id")
        media_type = training_data.get("media_type", "movie")

        # Collect metadata from APIs
        metadata_result = metadata_service.collect_all_metadata(
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
            media_type=media_type
        )

        if not metadata_result.get("success", False):
            return {
                "success": False,
                "message": "Failed to collect metadata from external APIs",
                "imdb_id": imdb_id,
                "error": "API collection failed",
                "tmdb_success": metadata_result.get("tmdb_success", False),
                "omdb_success": metadata_result.get("omdb_success", False),
                "errors": metadata_result.get("errors", [])
            }

        # Update training record with new metadata
        collected_metadata = metadata_result.get("data", {})

        if not collected_metadata:
            return {
                "success": False,
                "message": "No metadata collected from APIs",
                "imdb_id": imdb_id,
                "error": "Empty metadata response",
                "tmdb_success": metadata_result.get("tmdb_success", False),
                "omdb_success": metadata_result.get("omdb_success", False),
                "errors": metadata_result.get("errors", [])
            }

        # Update the training record
        update_result = db_service.update_training_metadata(imdb_id, collected_metadata)

        if not update_result.get("success", False):
            return {
                "success": False,
                "message": "Failed to update training record",
                "imdb_id": imdb_id,
                "error": update_result.get("error"),
                "tmdb_success": metadata_result.get("tmdb_success", False),
                "omdb_success": metadata_result.get("omdb_success", False),
                "errors": metadata_result.get("errors", [])
            }

        return {
            "success": True,
            "message": "Metadata successfully re-collected and updated",
            "imdb_id": imdb_id,
            "tmdb_success": metadata_result.get("tmdb_success", False),
            "omdb_success": metadata_result.get("omdb_success", False),
            "errors": metadata_result.get("errors", []) if metadata_result.get("errors") else None,
            "updated_fields": update_result.get("updated_fields"),
            "fields_updated_count": update_result.get("fields_updated_count")
        }

    return router