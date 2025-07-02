# app/services/db_service.py
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
            'host': settings.REAR_DIFF_PGSQL_HOST,
            'port': settings.REAR_DIFF_PGSQL_PORT,
            'user': settings.REAR_DIFF_PGSQL_USERNAME,
            'password': settings.REAR_DIFF_PGSQL_PASSWORD,
            'dbname': settings.REAR_DIFF_PGSQL_DATABASE
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

    def get_training_data(self,
                 media_type: Optional[str] = None,
                 label: Optional[str] = None,
                 reviewed: Optional[bool] = None,
                 human_labeled: Optional[bool] = None,
                 anomalous: Optional[bool] = None,
                 limit: int = 100,
                 offset: int = 0,
                 sort_by: str = "created_at",
                 sort_order: str = "desc") -> Dict[str, Any]:
        """
        Get training data entries from the database with optional filtering.

        Args:
            media_type: Optional filter by media type
            label: Optional filter by label
            reviewed: Optional filter by reviewed status
            human_labeled: Optional filter by human labeled status
            anomalous: Optional filter by anomalous status
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

                if label:
                    where_clauses.append("label = %s")
                    params.append(label)

                if reviewed is not None:
                    where_clauses.append("reviewed = %s")
                    params.append(reviewed)

                if human_labeled is not None:
                    where_clauses.append("human_labeled = %s")
                    params.append(human_labeled)

                if anomalous is not None:
                    where_clauses.append("anomalous = %s")
                    params.append(anomalous)

                where_clause = " AND ".join(where_clauses)
                if where_clause:
                    where_clause = "WHERE " + where_clause

                # Validate sort_by to prevent SQL injection
                valid_sort_fields = [
                    "created_at", "updated_at", "media_title", "release_year",
                    "media_type", "label", "imdb_id", "tmdb_id", "budget",
                    "revenue", "runtime", "original_language", "tmdb_rating",
                    "tmdb_votes", "rt_score", "metascore", "imdb_rating",
                    "imdb_votes", "human_labeled", "anomalous", "reviewed"
                ]
                if sort_by not in valid_sort_fields:
                    sort_by = "created_at"

                # Validate sort_order
                sort_order = sort_order.lower()
                if sort_order not in ["asc", "desc"]:
                    sort_order = "desc"

                # Count total matching records
                count_query = f"""
                    SELECT COUNT(*) FROM atp.training {where_clause}
                """
                cursor.execute(count_query, params)
                total = cursor.fetchone()["count"]

                # Get the requested page of data
                query = f"""
                    SELECT * FROM atp.training
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
                    "next": f"/rear-diff/training?offset={next_offset}&limit={limit}" if next_offset is not None else None,
                    "previous": f"/rear-diff/training?offset={previous_offset}&limit={limit}" if previous_offset is not None else None
                }

                return {
                    "data": data,
                    "pagination": pagination
                }

        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_label(self, imdb_id: str, label: str) -> Dict[str, Any]:
        """
        Update the label for a training data entry and set human_labeled to True.

        Args:
            imdb_id: The IMDB ID of the media item
            label: The new label value

        Returns:
            Dictionary with success status and message
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Check if the training data entry exists
                cursor.execute("SELECT 1 FROM atp.training WHERE imdb_id = %s", (imdb_id,))
                if cursor.fetchone() is None:
                    return {
                        "success": False,
                        "error": "Training data not found",
                        "message": f"No training data found with IMDB ID: {imdb_id}"
                    }

                # Update the label and set human_labeled and reviewed to True
                query = """
                    UPDATE atp.training
                    SET label = %s, human_labeled = TRUE, reviewed = TRUE, updated_at = NOW()
                    WHERE imdb_id = %s
                """
                cursor.execute(query, (label, imdb_id))
                conn.commit()

                return {
                    "success": True,
                    "message": "Label updated successfully"
                }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating label: {e}")
            return {
                "success": False,
                "error": "Database error",
                "message": str(e)
            }
        finally:
            if conn:
                conn.close()

    def update_reviewed(self, imdb_id: str) -> Dict[str, Any]:
        """
        Update the reviewed status for a training data entry to True.

        Args:
            imdb_id: The IMDB ID of the media item

        Returns:
            Dictionary with success status and message
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Check if the training data entry exists
                cursor.execute("SELECT 1 FROM atp.training WHERE imdb_id = %s", (imdb_id,))
                if cursor.fetchone() is None:
                    return {
                        "success": False,
                        "error": "Training data not found",
                        "message": f"No training data found with IMDB ID: {imdb_id}"
                    }

                # Update the reviewed status to True
                query = """
                    UPDATE atp.training
                    SET reviewed = TRUE, updated_at = NOW()
                    WHERE imdb_id = %s
                """
                cursor.execute(query, (imdb_id,))
                conn.commit()

                return {
                    "success": True,
                    "message": "Reviewed status updated successfully"
                }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating reviewed status: {e}")
            return {
                "success": False,
                "error": "Database error",
                "message": str(e)
            }
        finally:
            if conn:
                conn.close()