# app/routers/media.py
"""Media router for handling media-related endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from app.services.db_service import DatabaseService
from app.models.api import MediaListResponse, MediaType, PipelineStatus, RejectionStatus, MediaPipelineUpdateRequest, MediaPipelineUpdateResponse, MediaDeleteResponse
import logging

logger = logging.getLogger("rear-differential.media")

def get_router():
    """Factory function to create the media router."""
    router = APIRouter()
    db_service = DatabaseService()

    @router.get("/", response_model=MediaListResponse)
    async def get_media(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        media_type: Optional[MediaType] = None,
        pipeline_status: Optional[PipelineStatus] = None,
        rejection_status: Optional[RejectionStatus] = None,
        error_status: Optional[bool] = None,
        imdb_id: Optional[str] = None,
        media_title: Optional[str] = None,
        hash: Optional[str] = None,
        sort_by: str = Query("created_at", regex="^(created_at|updated_at|release_year|media_title|imdb_rating)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$")
    ):
        """
        Get media data from atp.media table.
        
        Parameters:
        - limit: Maximum number of records to return (1-1000)
        - offset: Number of records to skip
        - media_type: Filter by media type
        - pipeline_status: Filter by pipeline status
        - rejection_status: Filter by rejection status
        - error_status: Filter by error status
        - imdb_id: Filter by specific IMDB ID
        - media_title: Search by media title (case-insensitive partial match)
        - hash: Filter by specific hash
        - sort_by: Field to sort by
        - sort_order: Sort direction (asc/desc)
        """
        try:
            logger.info(f"Fetching media data with limit={limit}, offset={offset}")
            
            # Call the database service to get media data
            result = db_service.get_media_data(
                limit=limit,
                offset=offset,
                media_type=media_type,
                pipeline_status=pipeline_status,
                rejection_status=rejection_status,
                error_status=error_status,
                imdb_id=imdb_id,
                media_title=media_title,
                hash=hash,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            logger.info(f"Successfully fetched {len(result['data'])} media records")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching media data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch media data: {str(e)}")

    @router.patch("/{hash}/pipeline", response_model=MediaPipelineUpdateResponse)
    async def update_media_pipeline(
        hash: str,
        request: MediaPipelineUpdateRequest
    ):
        """
        Update pipeline status, error status, and rejection status for a media entry.
        
        Parameters:
        - hash: The hash of the media entry to update
        - request: The update request containing the new status values
        """
        try:
            logger.info(f"Updating media pipeline status for hash={hash}")
            
            # Validate that the hash in the URL matches the hash in the request body
            if request.hash != hash:
                raise HTTPException(
                    status_code=400, 
                    detail="Hash in URL path must match hash in request body"
                )
            
            # Call the database service to update the media pipeline status
            result = db_service.update_media_pipeline(
                hash=hash,
                pipeline_status=request.pipeline_status,
                error_status=request.error_status,
                rejection_status=request.rejection_status
            )
            
            if result["success"]:
                logger.info(f"Successfully updated media pipeline status for hash={hash}")
                return MediaPipelineUpdateResponse(
                    success=True,
                    message=result["message"]
                )
            else:
                logger.warning(f"Failed to update media pipeline status for hash={hash}: {result['message']}")
                raise HTTPException(
                    status_code=404 if result["error"] == "Media not found" else 400,
                    detail=result["message"]
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating media pipeline status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update media pipeline status: {str(e)}")

    @router.delete("/{hash}", response_model=MediaDeleteResponse)
    async def delete_media(hash: str):
        """
        Delete a media entry by hash.

        Parameters:
        - hash: The hash of the media entry to delete (40 hex characters)
        """
        try:
            logger.info(f"Deleting media entry with hash={hash}")

            # Call the database service to delete the media entry
            result = db_service.delete_media(hash=hash)

            if result["success"]:
                logger.info(f"Successfully deleted media entry with hash={hash}")
                return MediaDeleteResponse(
                    success=True,
                    message=result["message"],
                    hash=hash
                )
            else:
                logger.warning(f"Failed to delete media entry with hash={hash}: {result['message']}")
                raise HTTPException(
                    status_code=404 if result["error"] == "Media not found" else 400,
                    detail=result["message"]
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting media entry: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete media entry: {str(e)}")

    return router