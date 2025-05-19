# app/routers/media.py
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional
from app.models.api import TrainingListResponse, LabelUpdateRequest, LabelUpdateResponse, MediaType, LabelType
from app.services.db_service import DatabaseService

def get_router():
    router = APIRouter()
    db_service = DatabaseService()

    @router.get("", response_model=TrainingListResponse)
    async def get_training_data(
        media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
        label: Optional[LabelType] = Query(None, description="Filter by label"),
        limit: int = Query(100, description="Maximum number of records to return"),
        offset: int = Query(0, description="Number of records to skip"),
        sort_by: str = Query("created_at", description="Field to sort results by"),
        sort_order: str = Query("desc", description="Direction of sort ('asc' or 'desc')")
    ):
        """
        Retrieve training data entries from the database with optional filtering and pagination.
        """
        try:
            result = db_service.get_training_data(
                media_type=media_type.value if media_type else None,
                label=label.value if label else None,
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

    @router.patch("/{imdb_id}/label", response_model=LabelUpdateResponse)
    async def update_label(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)"),
        request: LabelUpdateRequest = None
    ):
        """
        Update the label for a specific training data entry.
        """
        # Validate that path imdb_id matches request body imdb_id
        if request.imdb_id != imdb_id:
            return {
                "success": False,
                "error": "IMDB ID mismatch",
                "message": "Path IMDB ID and body IMDB ID do not match"
            }

        result = db_service.update_label(imdb_id, request.label.value)
        if not result.get("success", False):
            status_code = 404 if result.get("error") == "Training data not found" else 500
            return result

        return result

    return router