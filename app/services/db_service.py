# app/services/db_service.py (updated)
import logging
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for database operations."""

    def __init__(self):
        """Initialize the database service."""
        self.connection_params = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD,
            'dbname': settings.DB_NAME
        }

    def get_connection(self):
        """Get a database connection."""
        try:
            conn = psycopg2.connect(**self.connection_params)
            # Set the schema search path
            with conn.cursor() as cursor:
                cursor.execute("SET search_path TO atp")
            return conn
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def get_media(self,
                 media_type: Optional[str] = None,
                 pipeline_status: Optional[str] = None,
                 limit: int = 100,
                 offset: int = 0,
                 sort_by: str = "created_at",
                 sort_order: str = "desc") -> Dict[str, Any]:
        """
        Get all media entries from the database with optional filtering.

        Args:
            media_type: Optional filter by media type
            pipeline_status: Optional filter by pipeline status
            limit: Maximum number of records to return
            offset: Number of records to skip
            sort_by: Field to sort by
            sort_order: Direction of sort ('asc' or 'desc')

        Returns:
            Dictionary with data and pagination information
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Build the WHERE clause for filtering
                where_clauses = []
                params = []

                if media_type:
                    where_clauses.append("media_type = %s")
                    params.append(media_type)

                if pipeline_status:
                    where_clauses.append("pipeline_status = %s")
                    params.append(pipeline_status)

                where_clause = " AND ".join(where_clauses)
                if where_clause:
                    where_clause = "WHERE " + where_clause

                # Validate sort_by to prevent SQL injection
                valid_sort_fields = [
                    "created_at", "updated_at", "media_title", "release_year",
                    "media_type", "pipeline_status"
                ]
                if sort_by not in valid_sort_fields:
                    sort_by = "created_at"

                # Validate sort_order
                sort_order = sort_order.lower()
                if sort_order not in ["asc", "desc"]:
                    sort_order = "desc"

                # Count total matching records
                count_query = f"""
                    SELECT COUNT(*) FROM atp.media {where_clause}
                """
                cursor.execute(count_query, params)
                total = cursor.fetchone()["count"]

                # Get the requested page of data
                query = f"""
                    SELECT * FROM atp.media
                    {where_clause}
                    ORDER BY {sort_by} {sort_order}
                    LIMIT %s OFFSET %s
                """

                # Add limit and offset to params
                cursor.execute(query, params + [limit, offset])
                data = cursor.fetchall()

                # Prepare pagination info
                next_offset = offset + limit if offset + limit < total else None
                previous_offset = offset - limit if offset > 0 else None

                pagination = {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "next": f"/rear-diff/media?offset={next_offset}&limit={limit}" if next_offset is not None else None,
                    "previous": f"/rear-diff/media?offset={previous_offset}&limit={limit}" if previous_offset is not None else None
                }

                return {
                    "data": data,
                    "pagination": pagination
                }

        except Exception as e:
            logger.error(f"Error getting media: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_rejection_status(self, hash: str, rejection_status: str) -> Dict[str, Any]:
        """
        Update the rejection status for a media item.

        Args:
            hash: The 40-character SHA-1 hash of the media item
            rejection_status: The new rejection status

        Returns:
            Dictionary with success status and message
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Check if the media item exists
                cursor.execute("SELECT 1 FROM atp.media WHERE hash = %s", (hash,))
                if cursor.fetchone() is None:
                    return {
                        "success": False,
                        "error": "Media not found",
                        "message": f"No media found with hash: {hash}"
                    }

                # Update the rejection status
                query = """
                    UPDATE atp.media
                    SET rejection_status = %s, updated_at = NOW()
                    WHERE hash = %s
                """
                cursor.execute(query, (rejection_status, hash))
                conn.commit()

                return {
                    "success": True,
                    "message": "Rejection status updated successfully"
                }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating rejection status: {e}")
            return {
                "success": False,
                "error": "Database error",
                "message": str(e)
            }
        finally:
            if conn:
                conn.close()