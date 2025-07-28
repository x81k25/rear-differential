# app/routers/prediction.py
"""Prediction router for handling prediction-related endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.db_service import DatabaseService
from app.models.api import PredictionListResponse
import logging

logger = logging.getLogger("rear-differential.prediction")

def get_router():
    """Factory function to create the prediction router."""
    router = APIRouter()
    db_service = DatabaseService()

    @router.get("/", response_model=PredictionListResponse)
    async def get_predictions(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        imdb_id: Optional[str] = None,
        prediction: Optional[int] = Query(None, ge=0, le=1),
        cm_value: Optional[str] = Query(None, regex="^(tn|tp|fn|fp)$"),
        sort_by: str = Query("created_at", regex="^(imdb_id|prediction|probability|cm_value|created_at)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$")
    ):
        """
        Get prediction data from atp.prediction table.
        
        Parameters:
        - limit: Maximum number of records to return (1-1000)
        - offset: Number of records to skip
        - imdb_id: Filter by specific IMDB ID
        - prediction: Filter by prediction value (0 or 1)
        - cm_value: Filter by confusion matrix value (tn, tp, fn, fp)
        - sort_by: Field to sort by
        - sort_order: Sort direction (asc/desc)
        """
        try:
            logger.info(f"Fetching prediction data with limit={limit}, offset={offset}")
            
            # Call the database service to get prediction data
            result = db_service.get_prediction_data(
                limit=limit,
                offset=offset,
                imdb_id=imdb_id,
                prediction=prediction,
                cm_value=cm_value,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            logger.info(f"Successfully fetched {len(result['data'])} prediction records")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching prediction data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch prediction data: {str(e)}")

    return router