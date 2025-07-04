# app/routers/media.py
"""Media router for handling media-related endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from app.services.db_service import DatabaseService
from app.models.api import MediaListResponse, MediaType, PipelineStatus, RejectionStatus, FlywayHistoryResponse
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
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            logger.info(f"Successfully fetched {len(result['data'])} media records")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching media data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch media data: {str(e)}")

    @router.get("/flyway", response_model=FlywayHistoryResponse)
    async def get_flyway_history():
        """
        Get all records from flyway_schema_history table.
        
        Returns:
            All flyway schema history records
        """
        try:
            logger.info("Fetching flyway schema history")
            
            # Call the database service to get flyway data
            result = db_service.get_flyway_schema_history()
            
            logger.info(f"Successfully fetched {len(result)} flyway history records")
            return {"data": result}
            
        except Exception as e:
            logger.error(f"Error fetching flyway history: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch flyway history: {str(e)}")

    @router.get("/public-tables")
    async def get_public_tables():
        """
        Get all tables in public schema for debugging.
        
        Returns:
            List of all tables in public schema
        """
        try:
            logger.info("Fetching public schema tables")
            
            # Call the database service to get public tables
            result = db_service.get_public_tables()
            
            logger.info(f"Successfully fetched {len(result)} public tables")
            return {"data": result}
            
        except Exception as e:
            logger.error(f"Error fetching public tables: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch public tables: {str(e)}")

    return router