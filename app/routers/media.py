# app/routers/media.py
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from app.models.api import MediaListResponse, RejectionStatusUpdateRequest, RejectionStatusUpdateResponse
from app.services.db_service import DatabaseService

def get_router():
    router = APIRouter()
    db_service = DatabaseService()

    @router.get("", response_model=MediaListResponse)
    async def get_media(
        media_type: Optional[str] = Query(None, description="Filter by media type"),
        pipeline_status: Optional[str] = Query(None, description="Filter by pipeline status"),
        limit: int = Query(100, description="Maximum number of records to return"),
        offset: int = Query(0, description="Number of records to skip"),
        sort_by: str = Query("created_at", description="Field to sort results by"),
        sort_order: str = Query("desc", description="Direction of sort ('asc' or 'desc')")
    ):
        """
        Retrieve media entries from the database with optional filtering and pagination.
        """
        try:
            result = db_service.get_media(
                media_type=media_type,
                pipeline_status=pipeline_status,
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

    @router.patch("/{hash}/rejection-status", response_model=RejectionStatusUpdateResponse)
    async def update_rejection_status(
        hash: str = Path(..., description="The 40-character SHA-1 hash of the media item"),
        request: RejectionStatusUpdateRequest = None
    ):
        """
        Update the rejection status for a specific media item.
        """
        # Validate that path hash matches request body hash
        if request.hash != hash:
            return {
                "success": False,
                "error": "Hash mismatch",
                "message": "Path hash and body hash do not match"
            }

        result = db_service.update_rejection_status(hash, request.rejection_status)
        if not result.get("success", False):
            status_code = 404 if result.get("error") == "Media not found" else 500
            return result

        return result

    return router