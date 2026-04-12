# app/routers/transmission.py
"""Transmission router for adding torrents to Transmission."""
from fastapi import APIRouter, HTTPException
from app.services.transmission_service import TransmissionService
from app.models.api import TransmissionAddRequest, TransmissionAddResponse
import logging

logger = logging.getLogger("rear-differential.transmission")


def get_router():
    """Factory function to create the transmission router."""
    router = APIRouter()
    transmission_service = TransmissionService()

    @router.post("/", response_model=TransmissionAddResponse)
    async def add_torrent(request: TransmissionAddRequest):
        """
        Add a torrent to Transmission via magnet link.

        Forwards the magnet link to the environment's Transmission instance.
        """
        try:
            logger.info("Adding torrent to Transmission")
            result = transmission_service.add_torrent(request.magnet_link)

            if not result["success"]:
                raise HTTPException(status_code=502, detail=result["message"])

            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to add torrent: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to add torrent: {e}")

    return router
