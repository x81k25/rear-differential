# app/services/transmission_service.py
"""Transmission RPC service for interacting with Transmission daemon."""
import logging
from typing import Dict, Any, Optional
from transmission_rpc import Client as TransmissionClient
from transmission_rpc.error import TransmissionError
from app.core.config import settings

logger = logging.getLogger(__name__)


class TransmissionService:
    """Service for Transmission RPC operations."""

    def __init__(self):
        """Initialize the Transmission service."""
        self.host = settings.REAR_DIFF_TRANSMISSION_HOST
        self.port = settings.REAR_DIFF_TRANSMISSION_PORT
        self.username = settings.REAR_DIFF_TRANSMISSION_USERNAME
        self.password = settings.REAR_DIFF_TRANSMISSION_PASSWORD

    def get_client(self) -> TransmissionClient:
        """Get a Transmission RPC client."""
        try:
            return TransmissionClient(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )
        except Exception as e:
            logger.error(f"Error connecting to Transmission: {e}")
            raise

    def torrent_exists(self, hash: str) -> bool:
        """
        Check if a torrent exists in Transmission by hash.

        Args:
            hash: The torrent hash (infohash)

        Returns:
            True if torrent exists, False otherwise
        """
        try:
            client = self.get_client()
            client.get_torrent(hash)
            return True
        except TransmissionError:
            return False
        except Exception as e:
            logger.error(f"Error checking torrent existence: {e}")
            return False

    def remove_torrent(self, hash: str, delete_data: bool = True) -> Dict[str, Any]:
        """
        Remove a torrent from Transmission by hash.

        Args:
            hash: The torrent hash (infohash)
            delete_data: Whether to delete downloaded data (default: True)

        Returns:
            Dictionary with success status and message
        """
        try:
            client = self.get_client()

            # Check if torrent exists first
            try:
                torrent = client.get_torrent(hash)
                torrent_name = torrent.name
            except TransmissionError:
                return {
                    "success": True,
                    "found": False,
                    "message": f"Torrent not found in Transmission: {hash}"
                }

            # Remove the torrent
            client.remove_torrent(hash, delete_data=delete_data)
            logger.info(f"Removed torrent from Transmission: {torrent_name} (hash: {hash})")

            return {
                "success": True,
                "found": True,
                "message": f"Torrent removed from Transmission: {torrent_name}",
                "torrent_name": torrent_name
            }

        except TransmissionError as e:
            logger.error(f"Transmission error removing torrent {hash}: {e}")
            return {
                "success": False,
                "found": False,
                "error": "Transmission error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Error removing torrent {hash}: {e}")
            return {
                "success": False,
                "found": False,
                "error": "Connection error",
                "message": str(e)
            }

    def add_torrent(self, torrent_link: str, hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a torrent to Transmission by magnet link or torrent URL.

        Args:
            torrent_link: The magnet link or torrent file URL
            hash: Optional hash to check if torrent already exists

        Returns:
            Dictionary with success status, already_exists flag, and message
        """
        try:
            client = self.get_client()

            # If hash provided, check if torrent already exists
            if hash:
                try:
                    existing = client.get_torrent(hash)
                    logger.info(f"Torrent already exists in Transmission: {existing.name}")
                    return {
                        "success": True,
                        "already_exists": True,
                        "message": f"Torrent already exists: {existing.name}",
                        "torrent_name": existing.name
                    }
                except TransmissionError:
                    # Torrent doesn't exist, proceed to add it
                    pass

            # Add the torrent
            torrent = client.add_torrent(torrent_link)
            logger.info(f"Added torrent to Transmission: {torrent.name}")

            return {
                "success": True,
                "already_exists": False,
                "message": f"Torrent added successfully: {torrent.name}",
                "torrent_name": torrent.name
            }

        except TransmissionError as e:
            error_msg = str(e).lower()
            # Check if the error is because torrent already exists (duplicate)
            if "duplicate" in error_msg or "already" in error_msg:
                logger.info(f"Torrent already exists in Transmission (duplicate): {hash}")
                return {
                    "success": True,
                    "already_exists": True,
                    "message": "Torrent already exists in Transmission"
                }
            logger.error(f"Transmission error adding torrent: {e}")
            return {
                "success": False,
                "already_exists": False,
                "error": "Transmission error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Error adding torrent: {e}")
            return {
                "success": False,
                "already_exists": False,
                "error": "Connection error",
                "message": str(e)
            }
