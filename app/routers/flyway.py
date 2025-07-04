# app/routers/flyway.py
"""Flyway router for handling flyway schema history endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.db_service import DatabaseService
from app.models.api import FlywayHistoryResponse
import logging

logger = logging.getLogger("rear-differential.flyway")

def get_router():
    """Factory function to create the flyway router."""
    router = APIRouter()
    db_service = DatabaseService()

    @router.get("/flyway", response_model=FlywayHistoryResponse)
    async def get_flyway_history(
        sort_by: str = Query("installed_rank", regex="^(installed_rank|installed_on|version)$"),
        sort_order: str = Query("asc", regex="^(asc|desc)$")
    ):
        """
        Get all records from flyway_schema_history table.
        
        Parameters:
        - sort_by: Field to sort by (installed_rank, installed_on, version)
        - sort_order: Sort direction (asc/desc)
        
        Returns:
            All flyway schema history records
        """
        try:
            logger.info(f"Fetching flyway schema history with sort_by={sort_by}, sort_order={sort_order}")
            
            # Call the database service to get flyway data
            result = db_service.get_flyway_schema_history(sort_by=sort_by, sort_order=sort_order)
            
            logger.info(f"Successfully fetched {len(result)} flyway history records")
            return {"data": result}
            
        except Exception as e:
            logger.error(f"Error fetching flyway history: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch flyway history: {str(e)}")

    return router