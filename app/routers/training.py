# app/routers/training.py
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from app.models.api import TrainingListResponse, TrainingUpdateRequest, TrainingUpdateResponse, MediaType, LabelType
from app.services.db_service import DatabaseService

def get_router():
    router = APIRouter()
    db_service = DatabaseService()

    @router.get("", response_model=TrainingListResponse)
    async def get_training_data(
        media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
        label: Optional[LabelType] = Query(None, description="Filter by label"),
        reviewed: Optional[bool] = Query(None, description="Filter by reviewed status"),
        human_labeled: Optional[bool] = Query(None, description="Filter by human labeled status"),
        anomalous: Optional[bool] = Query(None, description="Filter by anomalous status"),
        imdb_id: Optional[str] = Query(None, description="Filter by specific IMDB ID(s). Single ID or comma-separated list (e.g., 'tt1234567' or 'tt1234567,tt7654321')"),
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

    return router