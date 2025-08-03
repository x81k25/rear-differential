# app/routers/movies.py
"""Movies router for handling movie-related endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from app.services.db_service import DatabaseService
from app.models.api import MovieListResponse, MediaType, LabelType
import logging

logger = logging.getLogger("rear-differential.movies")

def get_router():
    """Factory function to create the movies router."""
    router = APIRouter()
    db_service = DatabaseService()

    @router.get("/", response_model=MovieListResponse)
    async def get_movies(
        # Training filters
        media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
        label: Optional[LabelType] = Query(None, description="Filter by label"),
        reviewed: Optional[bool] = Query(None, description="Filter by reviewed status"),
        human_labeled: Optional[bool] = Query(None, description="Filter by human labeled status"),
        anomalous: Optional[bool] = Query(None, description="Filter by anomalous status"),
        
        # Prediction filters
        prediction: Optional[int] = Query(None, ge=0, le=1, description="Filter by prediction value (0 or 1)"),
        cm_value: Optional[str] = Query(None, regex="^(tn|tp|fn|fp)$", description="Filter by confusion matrix value (tn, tp, fn, fp)"),
        
        # Media content filters
        imdb_id: Optional[str] = Query(None, description="Filter by specific IMDB ID(s). Single ID or comma-separated list (e.g., 'tt1234567' or 'tt1234567,tt7654321')"),
        media_title: Optional[str] = Query(None, description="Search by media title (case-insensitive partial match)"),
        release_year: Optional[int] = Query(None, ge=1850, le=2100, description="Filter by release year"),
        
        # Pagination
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return (1-1000)"),
        offset: int = Query(0, ge=0, description="Number of records to skip"),
        
        # Sorting
        sort_by: str = Query(
            "training_created_at", 
            regex="^(imdb_id|tmdb_id|label|media_type|media_title|season|episode|release_year|budget|revenue|runtime|origin_country|production_companies|production_countries|production_status|original_language|spoken_languages|genre|original_media_title|tagline|overview|tmdb_rating|tmdb_votes|rt_score|metascore|imdb_rating|imdb_votes|human_labeled|anomalous|reviewed|prediction|probability|cm_value|training_created_at|training_updated_at|prediction_created_at)$",
            description="Field to sort by"
        ),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction (asc/desc)")
    ):
        """
        Get movie data from atp.movies view.
        
        This endpoint combines training and prediction data for movies, providing comprehensive
        filtering options from both tables including:
        
        **Training Filters:**
        - media_type: Filter by media type
        - label: Filter by label (would_watch/would_not_watch)
        - reviewed: Filter by reviewed status
        - human_labeled: Filter by human labeled status
        - anomalous: Filter by anomalous status
        
        **Prediction Filters:**
        - prediction: Filter by prediction value (0 or 1)
        - cm_value: Filter by confusion matrix value (tn, tp, fn, fp)
        
        **Content Filters:**
        - imdb_id: Filter by specific IMDB ID(s)
        - media_title: Search by media title (partial match)
        - release_year: Filter by release year
        
        **Pagination & Sorting:**
        - limit: Maximum records to return
        - offset: Records to skip
        - sort_by: Field to sort by
        - sort_order: Sort direction
        """
        try:
            logger.info(f"Fetching movie data with limit={limit}, offset={offset}")
            
            # Parse imdb_id parameter - handle single ID or comma-separated list
            imdb_ids = None
            if imdb_id:
                # Split by comma and strip whitespace, filter out empty strings
                imdb_ids = [id.strip() for id in imdb_id.split(',') if id.strip()]
            
            # Call the database service to get movie data
            result = db_service.get_movie_data(
                media_type=media_type.value if media_type else None,
                label=label.value if label else None,
                reviewed=reviewed,
                human_labeled=human_labeled,
                anomalous=anomalous,
                imdb_ids=imdb_ids,
                prediction=prediction,
                cm_value=cm_value,
                media_title=media_title,
                release_year=release_year,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            logger.info(f"Successfully fetched {len(result['data'])} movie records")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching movie data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch movie data: {str(e)}")

    return router