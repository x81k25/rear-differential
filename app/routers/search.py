# app/routers/search.py
"""Search router for torrent search endpoints."""
from fastapi import APIRouter, HTTPException, Query
from app.services.search_service import SearchService
from app.models.api import SearchListResponse, SearchMediaType
import logging

logger = logging.getLogger("rear-differential.search")


def get_router():
    """Factory function to create the search router."""
    router = APIRouter()
    search_service = SearchService()

    @router.get("/", response_model=SearchListResponse)
    async def search_torrents(
        q: str = Query(..., min_length=1, description="Search text"),
        media_type: SearchMediaType = Query(..., description="Media type: movie or tv"),
    ):
        """
        Search public torrent APIs for matching content.

        - **movie**: searches YTS and The Pirate Bay
        - **tv**: searches EZTV and The Pirate Bay

        Returns parsed results with title, year, season, episode,
        resolution, and video codec.
        """
        try:
            logger.info(f"Searching for q={q!r}, media_type={media_type.value}")
            results = await search_service.search(q, media_type.value)
            logger.info(f"Search returned {len(results)} results")
            return {"count": len(results), "results": results}
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    return router
