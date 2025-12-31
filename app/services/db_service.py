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
                 imdb_ids: Optional[List[str]] = None,
                 media_title: Optional[str] = None,
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
            imdb_ids: Optional filter by list of specific IMDB IDs
            media_title: Optional filter by media title (partial match, case-insensitive)
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

                if imdb_ids:
                    # Handle multiple IMDB IDs using IN clause
                    placeholders = ','.join(['%s'] * len(imdb_ids))
                    where_clauses.append(f"imdb_id IN ({placeholders})")
                    params.extend(imdb_ids)

                if media_title:
                    # Case-insensitive partial match for media title
                    where_clauses.append("LOWER(media_title) LIKE LOWER(%s)")
                    params.append(f"%{media_title}%")

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
                    ORDER BY {sort_by} {sort_order}, imdb_id ASC
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

    def get_media_data(self,
                      media_type: Optional[str] = None,
                      pipeline_status: Optional[str] = None,
                      rejection_status: Optional[str] = None,
                      error_status: Optional[bool] = None,
                      imdb_id: Optional[str] = None,
                      media_title: Optional[str] = None,
                      hash: Optional[str] = None,
                      limit: int = 100,
                      offset: int = 0,
                      sort_by: str = "created_at",
                      sort_order: str = "desc") -> Dict[str, Any]:
        """
        Get media data from atp.media table with optional filtering.

        Args:
            media_type: Optional filter by media type
            pipeline_status: Optional filter by pipeline status
            rejection_status: Optional filter by rejection status
            error_status: Optional filter by error status
            imdb_id: Optional filter by specific IMDB ID
            media_title: Optional search by media title (case-insensitive partial match)
            hash: Optional filter by specific hash
            limit: Maximum number of results to return
            offset: Number of results to skip
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Dictionary containing media data and pagination info
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Build the WHERE clause
                where_conditions = []
                params = []
                
                if media_type:
                    where_conditions.append("media_type = %s")
                    params.append(media_type)
                
                if pipeline_status:
                    where_conditions.append("pipeline_status = %s")
                    params.append(pipeline_status)
                
                if rejection_status:
                    where_conditions.append("rejection_status = %s")
                    params.append(rejection_status)
                
                if error_status is not None:
                    where_conditions.append("error_status = %s")
                    params.append(error_status)
                
                if imdb_id:
                    where_conditions.append("imdb_id = %s")
                    params.append(imdb_id)
                
                if media_title:
                    where_conditions.append("media_title ILIKE %s")
                    params.append(f"%{media_title}%")
                
                if hash:
                    where_conditions.append("hash = %s")
                    params.append(hash)
                
                # Always exclude soft-deleted records
                where_conditions.append("deleted_at IS NULL")

                where_clause = " AND ".join(where_conditions)

                # Count total records
                count_query = f"SELECT COUNT(*) FROM atp.media WHERE {where_clause}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()['count']
                
                # Build the main query
                query = f"""
                    SELECT 
                        hash, media_type, media_title, season, episode, release_year,
                        pipeline_status, error_status, error_condition, rejection_status, rejection_reason,
                        parent_path, target_path, original_title, original_path, original_link,
                        rss_source, uploader, imdb_id, tmdb_id,
                        budget, revenue, runtime,
                        origin_country, production_companies, production_countries, production_status,
                        original_language, spoken_languages,
                        genre, original_media_title, tagline, overview,
                        tmdb_rating, tmdb_votes, rt_score, metascore, imdb_rating, imdb_votes,
                        resolution, video_codec, upload_type, audio_codec,
                        created_at, updated_at
                    FROM atp.media
                    WHERE {where_clause}
                    ORDER BY {sort_by} {sort_order}, hash ASC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([limit, offset])
                cursor.execute(query, params)
                
                # Fetch all results
                media_data = cursor.fetchall()
                
                # Convert to list of dicts and handle any necessary data conversions
                result_data = []
                for row in media_data:
                    # Convert row to dict (already done by RealDictCursor)
                    row_dict = dict(row)
                    
                    # Ensure datetime objects are properly serialized
                    if row_dict.get('created_at'):
                        row_dict['created_at'] = row_dict['created_at'].isoformat()
                    if row_dict.get('updated_at'):
                        row_dict['updated_at'] = row_dict['updated_at'].isoformat()
                    
                    result_data.append(row_dict)
                
                # Prepare pagination info
                pagination = {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_count
                }
                
                return {
                    "data": result_data,
                    "pagination": pagination
                }
                
        except Exception as e:
            logger.error(f"Error fetching media data: {e}")
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

    def update_training_fields(self, imdb_id: str, label: Optional[str] = None, 
                             human_labeled: Optional[bool] = None, 
                             anomalous: Optional[bool] = None,
                             reviewed: Optional[bool] = None) -> Dict[str, Any]:
        """
        Update multiple fields for a training data entry.

        Args:
            imdb_id: The IMDB ID of the media item
            label: The new label value (optional)
            human_labeled: The new human_labeled value (optional)
            anomalous: The new anomalous value (optional)
            reviewed: The new reviewed value (optional)

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

                # Build dynamic update query
                update_fields = []
                params = []
                updated_fields = {}
                
                if label is not None:
                    update_fields.append("label = %s")
                    params.append(label)
                    updated_fields['label'] = label
                    # When label is updated, also set human_labeled and reviewed to True
                    update_fields.append("human_labeled = TRUE")
                    updated_fields['human_labeled'] = True
                    update_fields.append("reviewed = TRUE")
                    updated_fields['reviewed'] = True
                
                if human_labeled is not None and label is None:
                    update_fields.append("human_labeled = %s")
                    params.append(human_labeled)
                    updated_fields['human_labeled'] = human_labeled
                
                if anomalous is not None:
                    update_fields.append("anomalous = %s")
                    params.append(anomalous)
                    updated_fields['anomalous'] = anomalous
                
                if reviewed is not None and label is None:
                    update_fields.append("reviewed = %s")
                    params.append(reviewed)
                    updated_fields['reviewed'] = reviewed

                if not update_fields:
                    return {
                        "success": False,
                        "error": "No fields to update",
                        "message": "At least one field must be provided for update"
                    }

                # Add updated_at timestamp
                update_fields.append("updated_at = NOW()")
                
                # Add imdb_id to params
                params.append(imdb_id)

                # Execute update
                query = f"""
                    UPDATE atp.training
                    SET {', '.join(update_fields)}
                    WHERE imdb_id = %s
                """
                cursor.execute(query, params)
                conn.commit()

                return {
                    "success": True,
                    "message": "Training data updated successfully",
                    "updated_fields": updated_fields
                }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating training fields: {e}")
            return {
                "success": False,
                "error": "Database error",
                "message": str(e)
            }
        finally:
            if conn:
                conn.close()

    def get_public_tables(self) -> List[Dict[str, Any]]:
        """
        Get all tables in public schema.

        Returns:
            List of table names in public schema
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                return cursor.fetchall()

        except Exception as e:
            logger.error(f"Error fetching public tables: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_flyway_schema_history(self, sort_by: str = "installed_rank", sort_order: str = "asc") -> List[Dict[str, Any]]:
        """
        Get all records from flyway_schema_history table.

        Args:
            sort_by: Field to sort by (installed_rank, installed_on, version)
            sort_order: Sort direction (asc/desc)

        Returns:
            List of flyway schema history records
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Check if flyway_schema_history exists in any schema
                cursor.execute("""
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'flyway_schema_history'
                """)
                flyway_tables = cursor.fetchall()
                
                if flyway_tables:
                    # Use the first schema where the table exists
                    schema_name = flyway_tables[0]['table_schema']
                    
                    # Validate sort_by to prevent SQL injection
                    valid_sort_fields = ["installed_rank", "installed_on", "version"]
                    if sort_by not in valid_sort_fields:
                        sort_by = "installed_rank"
                    
                    # Validate sort_order
                    sort_order = sort_order.lower()
                    if sort_order not in ["asc", "desc"]:
                        sort_order = "asc"
                    
                    # Handle numeric sorting for installed_rank
                    order_clause = f"{sort_by} {sort_order}"
                    if sort_by == "installed_rank":
                        order_clause = f"CAST({sort_by} AS INTEGER) {sort_order}"
                    
                    query = f"""
                        SELECT 
                            installed_rank,
                            version,
                            description,
                            type,
                            script,
                            checksum,
                            installed_by,
                            installed_on,
                            execution_time,
                            success
                        FROM {schema_name}.flyway_schema_history
                        ORDER BY {order_clause}
                    """
                    cursor.execute(query)
                    return cursor.fetchall()
                else:
                    # Table doesn't exist anywhere, return empty list
                    logger.warning("flyway_schema_history table not found in any schema")
                    return []

        except Exception as e:
            logger.error(f"Error fetching flyway schema history: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_media_pipeline(self, hash: str, pipeline_status: Optional[str] = None,
                             error_status: Optional[bool] = None,
                             rejection_status: Optional[str] = None,
                             clear_error_condition: bool = False) -> Dict[str, Any]:
        """
        Update the pipeline status, error status, and rejection status for a media entry.

        Args:
            hash: The hash of the media item
            pipeline_status: Optional new pipeline status
            error_status: Optional new error status
            rejection_status: Optional new rejection status
            clear_error_condition: If True, sets error_condition to NULL

        Returns:
            Dictionary with success status and message
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Check if the media entry exists
                cursor.execute("SELECT 1 FROM atp.media WHERE hash = %s", (hash,))
                if cursor.fetchone() is None:
                    return {
                        "success": False,
                        "error": "Media not found",
                        "message": f"No media found with hash: {hash}"
                    }

                # Build the update query dynamically based on provided fields
                update_fields = []
                params = []

                if pipeline_status is not None:
                    update_fields.append("pipeline_status = %s")
                    params.append(pipeline_status)

                if error_status is not None:
                    update_fields.append("error_status = %s")
                    params.append(error_status)

                if rejection_status is not None:
                    update_fields.append("rejection_status = %s")
                    params.append(rejection_status)

                if clear_error_condition:
                    update_fields.append("error_condition = NULL")

                if not update_fields:
                    return {
                        "success": False,
                        "error": "No fields to update",
                        "message": "At least one field must be provided for update"
                    }

                # Always update the updated_at timestamp
                update_fields.append("updated_at = NOW()")
                params.append(hash)

                query = f"""
                    UPDATE atp.media
                    SET {', '.join(update_fields)}
                    WHERE hash = %s
                """
                cursor.execute(query, params)
                conn.commit()

                return {
                    "success": True,
                    "message": "Media pipeline status updated successfully"
                }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error updating media pipeline status: {e}")
            return {
                "success": False,
                "error": "Database error",
                "message": str(e)
            }
        finally:
            if conn:
                conn.close()

    def get_prediction_data(self,
                          imdb_id: Optional[str] = None,
                          prediction: Optional[int] = None,
                          cm_value: Optional[str] = None,
                          limit: int = 100,
                          offset: int = 0,
                          sort_by: str = "created_at",
                          sort_order: str = "desc") -> Dict[str, Any]:
        """
        Get prediction data from atp.prediction table with optional filtering.

        Args:
            imdb_id: Optional filter by specific IMDB ID
            prediction: Optional filter by prediction value (0 or 1)
            cm_value: Optional filter by confusion matrix value (tn, tp, fn, fp)
            limit: Maximum number of results to return
            offset: Number of results to skip
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Dictionary containing prediction data and pagination info
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Build the WHERE clause
                where_conditions = []
                params = []
                
                if imdb_id:
                    where_conditions.append("imdb_id = %s")
                    params.append(imdb_id)
                
                if prediction is not None:
                    where_conditions.append("prediction = %s")
                    params.append(prediction)
                
                if cm_value:
                    where_conditions.append("cm_value = %s")
                    params.append(cm_value)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # Count total records
                count_query = f"SELECT COUNT(*) FROM atp.prediction WHERE {where_clause}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()['count']
                
                # Validate sort_by to prevent SQL injection
                valid_sort_fields = ["imdb_id", "prediction", "probability", "cm_value", "created_at"]
                if sort_by not in valid_sort_fields:
                    sort_by = "created_at"
                
                # Validate sort_order
                sort_order = sort_order.lower()
                if sort_order not in ["asc", "desc"]:
                    sort_order = "desc"
                
                # Build the main query
                query = f"""
                    SELECT 
                        imdb_id, prediction, probability, cm_value, created_at
                    FROM atp.prediction
                    WHERE {where_clause}
                    ORDER BY {sort_by} {sort_order}, imdb_id ASC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([limit, offset])
                cursor.execute(query, params)
                
                # Fetch all results
                prediction_data = cursor.fetchall()
                
                # Convert to list of dicts and handle any necessary data conversions
                result_data = []
                for row in prediction_data:
                    # Convert row to dict (already done by RealDictCursor)
                    row_dict = dict(row)
                    
                    # Ensure datetime objects are properly serialized
                    if row_dict.get('created_at'):
                        row_dict['created_at'] = row_dict['created_at'].isoformat()
                    
                    result_data.append(row_dict)
                
                # Prepare pagination info
                pagination = {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_count
                }
                
                return {
                    "data": result_data,
                    "pagination": pagination
                }
                
        except Exception as e:
            logger.error(f"Error fetching prediction data: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def soft_delete_media(self, hash: str) -> Dict[str, Any]:
        """
        Soft delete a media entry by setting deleted_at timestamp.

        Args:
            hash: The hash of the media item to soft delete

        Returns:
            Dictionary with success status and message
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Check if the media entry exists and is not already deleted
                cursor.execute(
                    "SELECT deleted_at FROM atp.media WHERE hash = %s",
                    (hash,)
                )
                result = cursor.fetchone()
                if result is None:
                    return {
                        "success": False,
                        "error": "Media not found",
                        "message": f"No media found with hash: {hash}"
                    }

                if result[0] is not None:
                    return {
                        "success": False,
                        "error": "Already deleted",
                        "message": f"Media already deleted at: {result[0]}"
                    }

                # Soft delete by setting deleted_at timestamp (UTC)
                cursor.execute(
                    "UPDATE atp.media SET deleted_at = (NOW() AT TIME ZONE 'UTC'), updated_at = (NOW() AT TIME ZONE 'UTC') WHERE hash = %s",
                    (hash,)
                )
                conn.commit()

                return {
                    "success": True,
                    "message": "Media soft deleted successfully",
                    "hash": hash
                }

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error soft deleting media: {e}")
            return {
                "success": False,
                "error": "Database error",
                "message": str(e)
            }
        finally:
            if conn:
                conn.close()

    def get_media_by_hash(self, hash: str) -> Dict[str, Any]:
        """
        Get a single media entry by hash.

        Args:
            hash: The hash of the media item

        Returns:
            Dictionary with success status and media data or error message
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT hash, original_link, media_title, pipeline_status,
                           rejection_status, error_status, deleted_at
                    FROM atp.media
                    WHERE hash = %s
                    """,
                    (hash,)
                )
                result = cursor.fetchone()

                if result is None:
                    return {
                        "success": False,
                        "error": "Media not found",
                        "message": f"No media found with hash: {hash}"
                    }

                if result.get('deleted_at') is not None:
                    return {
                        "success": False,
                        "error": "Media deleted",
                        "message": f"Media has been deleted: {hash}"
                    }

                return {
                    "success": True,
                    "data": dict(result)
                }

        except Exception as e:
            logger.error(f"Error getting media by hash: {e}")
            return {
                "success": False,
                "error": "Database error",
                "message": str(e)
            }
        finally:
            if conn:
                conn.close()

    def get_movie_data(self,
                      media_type: Optional[str] = None,
                      label: Optional[str] = None,
                      reviewed: Optional[bool] = None,
                      human_labeled: Optional[bool] = None,
                      anomalous: Optional[bool] = None,
                      imdb_ids: Optional[List[str]] = None,
                      prediction: Optional[int] = None,
                      cm_value: Optional[str] = None,
                      media_title: Optional[str] = None,
                      release_year: Optional[int] = None,
                      limit: int = 100,
                      offset: int = 0,
                      sort_by: str = "training_created_at",
                      sort_order: str = "desc") -> Dict[str, Any]:
        """
        Get movie data from atp.movies view with optional filtering.

        Args:
            media_type: Optional filter by media type
            label: Optional filter by label
            reviewed: Optional filter by reviewed status
            human_labeled: Optional filter by human labeled status
            anomalous: Optional filter by anomalous status
            imdb_ids: Optional filter by list of specific IMDB IDs
            prediction: Optional filter by prediction value (0 or 1)
            cm_value: Optional filter by confusion matrix value (tn, tp, fn, fp)
            media_title: Optional search by media title (case-insensitive partial match)
            release_year: Optional filter by release year
            limit: Maximum number of results to return
            offset: Number of results to skip
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Dictionary containing movie data and pagination info
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Build the WHERE clause
                where_conditions = []
                params = []
                
                if media_type:
                    where_conditions.append("media_type = %s")
                    params.append(media_type)
                
                if label:
                    where_conditions.append("label = %s")
                    params.append(label)
                
                if reviewed is not None:
                    where_conditions.append("reviewed = %s")
                    params.append(reviewed)
                
                if human_labeled is not None:
                    where_conditions.append("human_labeled = %s")
                    params.append(human_labeled)
                
                if anomalous is not None:
                    where_conditions.append("anomalous = %s")
                    params.append(anomalous)
                
                if imdb_ids:
                    # Handle multiple IMDB IDs using IN clause
                    placeholders = ','.join(['%s'] * len(imdb_ids))
                    where_conditions.append(f"imdb_id IN ({placeholders})")
                    params.extend(imdb_ids)
                
                if prediction is not None:
                    where_conditions.append("prediction = %s")
                    params.append(prediction)
                
                if cm_value:
                    where_conditions.append("cm_value = %s")
                    params.append(cm_value)
                
                if media_title:
                    where_conditions.append("media_title ILIKE %s")
                    params.append(f"%{media_title}%")
                
                if release_year is not None:
                    where_conditions.append("release_year = %s")
                    params.append(release_year)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # Count total records
                count_query = f"SELECT COUNT(*) FROM atp.movies WHERE {where_clause}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()['count']
                
                # Validate sort_by to prevent SQL injection
                valid_sort_fields = [
                    "imdb_id", "tmdb_id", "label", "media_type", "media_title", 
                    "season", "episode", "release_year", "budget", "revenue", "runtime",
                    "origin_country", "production_companies", "production_countries", 
                    "production_status", "original_language", "spoken_languages",
                    "genre", "original_media_title", "tagline", "overview",
                    "tmdb_rating", "tmdb_votes", "rt_score", "metascore", 
                    "imdb_rating", "imdb_votes", "human_labeled", "anomalous", 
                    "reviewed", "prediction", "probability", "cm_value",
                    "training_created_at", "training_updated_at", "prediction_created_at"
                ]
                if sort_by not in valid_sort_fields:
                    sort_by = "training_created_at"
                
                # Validate sort_order
                sort_order = sort_order.lower()
                if sort_order not in ["asc", "desc"]:
                    sort_order = "desc"
                
                # Build the main query
                query = f"""
                    SELECT 
                        imdb_id, tmdb_id, label, media_type, media_title, 
                        season, episode, release_year, budget, revenue, runtime,
                        origin_country, production_companies, production_countries, 
                        production_status, original_language, spoken_languages,
                        genre, original_media_title, tagline, overview,
                        tmdb_rating, tmdb_votes, rt_score, metascore, 
                        imdb_rating, imdb_votes, human_labeled, anomalous, 
                        reviewed, prediction, probability, cm_value,
                        training_created_at, training_updated_at, prediction_created_at
                    FROM atp.movies
                    WHERE {where_clause}
                    ORDER BY {sort_by} {sort_order}, imdb_id ASC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([limit, offset])
                cursor.execute(query, params)
                
                # Fetch all results
                movie_data = cursor.fetchall()
                
                # Convert to list of dicts and handle any necessary data conversions
                result_data = []
                for row in movie_data:
                    # Convert row to dict (already done by RealDictCursor)
                    row_dict = dict(row)
                    
                    # Ensure datetime objects are properly serialized
                    if row_dict.get('training_created_at'):
                        row_dict['training_created_at'] = row_dict['training_created_at'].isoformat()
                    if row_dict.get('training_updated_at'):
                        row_dict['training_updated_at'] = row_dict['training_updated_at'].isoformat()
                    if row_dict.get('prediction_created_at'):
                        row_dict['prediction_created_at'] = row_dict['prediction_created_at'].isoformat()
                    
                    result_data.append(row_dict)
                
                # Prepare pagination info
                pagination = {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_count
                }
                
                return {
                    "data": result_data,
                    "pagination": pagination
                }
                
        except Exception as e:
            logger.error(f"Error fetching movie data: {e}")
            raise
        finally:
            if conn:
                conn.close()