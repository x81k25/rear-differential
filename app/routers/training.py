# app/routers/training.py
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks, Response
from typing import Optional, List
from app.models.api import (
    TrainingListResponse, TrainingUpdateRequest, TrainingUpdateResponse,
    MetadataRerunResponse, MediaType, LabelType,
    BatchMetadataRequest, BatchJobCreateResponse, BatchJobStatusResponse,
    JobStatus, BatchJobResult
)
from app.services.db_service import DatabaseService
from app.services.file_service import FileService
from app.services.transmission_service import TransmissionService
from app.services.metadata_service import MetadataService
from app.services.batch_job_service import get_batch_job_service

logger = logging.getLogger(__name__)

# Backoff delays in seconds for rate limiting
BACKOFF_DELAYS = [1, 5, 10, 30, 60]

def get_router():
    router = APIRouter()
    db_service = DatabaseService()
    file_service = FileService()
    transmission_service = TransmissionService()
    metadata_service = MetadataService()

    @router.get("", response_model=TrainingListResponse)
    async def get_training_data(
        media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
        label: Optional[LabelType] = Query(None, description="Filter by label"),
        reviewed: Optional[bool] = Query(None, description="Filter by reviewed status"),
        human_labeled: Optional[bool] = Query(None, description="Filter by human labeled status"),
        anomalous: Optional[bool] = Query(None, description="Filter by anomalous status"),
        imdb_id: Optional[str] = Query(None, description="Filter by specific IMDB ID(s). Single ID or comma-separated list (e.g., 'tt1234567' or 'tt1234567,tt7654321')"),
        media_title: Optional[str] = Query(None, description="Filter by media title (partial match, case-insensitive)"),
        limit: int = Query(100, description="Maximum number of records to return"),
        offset: int = Query(0, description="Number of records to skip"),
        sort_by: str = Query("created_at", description="Field to sort results by"),
        sort_order: str = Query("desc", description="Direction of sort ('asc' or 'desc')")
    ):
        """
        Retrieve training data entries from the database with optional filtering and pagination.
        """
        try:
            # Parse imdb_id parameter - handle single ID or comma-separated list
            imdb_ids = None
            if imdb_id:
                # Split by comma and strip whitespace, filter out empty strings
                imdb_ids = [id.strip() for id in imdb_id.split(',') if id.strip()]
            
            result = db_service.get_training_data(
                media_type=media_type.value if media_type else None,
                label=label.value if label else None,
                reviewed=reviewed,
                human_labeled=human_labeled,
                anomalous=anomalous,
                imdb_ids=imdb_ids,
                media_title=media_title,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            )
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"error": "Database error occurred", "details": str(e)}
            )

    @router.patch("/{imdb_id}", response_model=TrainingUpdateResponse)
    async def update_training(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)"),
        request: TrainingUpdateRequest = None
    ):
        """
        Update training data fields for a specific entry.
        Can update label, human_labeled, anomalous, and reviewed fields.
        When label is updated, human_labeled and reviewed are automatically set to True.
        """
        # Validate that path imdb_id matches request body imdb_id
        if request.imdb_id != imdb_id:
            return {
                "success": False,
                "error": "IMDB ID mismatch",
                "message": "Path IMDB ID and body IMDB ID do not match"
            }

        # Call the new update method with all possible fields
        result = db_service.update_training_fields(
            imdb_id=imdb_id,
            label=request.label.value if request.label else None,
            human_labeled=request.human_labeled,
            anomalous=request.anomalous,
            reviewed=request.reviewed
        )

        if not result.get("success", False):
            status_code = 404 if result.get("error") == "Training data not found" else 500
            return result

        return result

    @router.patch("/{imdb_id}/would_not_watch", response_model=TrainingUpdateResponse)
    async def would_not_watch_training(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)")
    ):
        """
        Mark a media item as would_not_watch and delete associated files.

        This endpoint:
        1. Sets label to 'would_not_watch'
        2. Sets human_labeled and reviewed to True
        3. Attempts to delete media files from the library (if enabled)
        4. Attempts to remove torrent from Transmission
        """
        # Update label to would_not_watch
        result = db_service.update_training_fields(
            imdb_id=imdb_id,
            label="would_not_watch"
        )

        if not result.get("success", False):
            if result.get("error") == "Training data not found":
                raise HTTPException(status_code=404, detail=result)
            return result

        # Attempt file deletion
        path_result = db_service.get_media_path_by_imdb_id(imdb_id)
        original_link = None

        if path_result.get("success"):
            path_data = path_result["data"]
            parent_path = path_data.get("parent_path")
            target_path = path_data.get("target_path")
            original_link = path_data.get("original_link")

            if parent_path and target_path:
                deletion_result = file_service.delete_directory(parent_path, target_path)

                if deletion_result.get("deleted"):
                    result["file_deleted"] = True
                    logger.info(f"Deleted files for {imdb_id}: {deletion_result.get('path')}")
                elif deletion_result.get("warning"):
                    result["file_deleted"] = False
                    result["file_deletion_warning"] = deletion_result["warning"]
                    logger.warning(f"File deletion warning for {imdb_id}: {deletion_result['warning']}")
                else:
                    # Deletion disabled or path doesn't exist
                    result["file_deleted"] = False
                    if deletion_result.get("message"):
                        result["file_deletion_warning"] = deletion_result["message"]
            else:
                result["file_deleted"] = False
                result["file_deletion_warning"] = "No path information available in media table"
        else:
            result["file_deleted"] = False
            result["file_deletion_warning"] = path_result.get("message", "Could not retrieve media path")

        # Attempt torrent removal from Transmission
        result["torrent_removed"] = False
        if original_link:
            # Extract hash from original_link (last segment of URL path)
            try:
                torrent_hash = original_link.rstrip('/').split('/')[-1].lower()
                if torrent_hash:
                    torrent_result = transmission_service.remove_torrent(torrent_hash, delete_data=False)
                    result["torrent_removed"] = torrent_result.get("found", False)
                    if torrent_result.get("found"):
                        logger.debug(f"Removed torrent for {imdb_id}: {torrent_hash}")
                    else:
                        logger.debug(f"Torrent not found in Transmission for {imdb_id}: {torrent_hash}")
            except Exception as e:
                logger.debug(f"Error removing torrent for {imdb_id}: {e}")
        else:
            logger.debug(f"No original_link found for {imdb_id}, skipping torrent removal")

        return result

    @router.patch("/{imdb_id}/would_watch", response_model=TrainingUpdateResponse)
    async def would_watch_training(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)")
    ):
        """
        Mark a media item as would_watch.

        This endpoint:
        1. Sets label to 'would_watch'
        2. Sets human_labeled and reviewed to True
        """
        result = db_service.update_training_fields(
            imdb_id=imdb_id,
            label="would_watch"
        )

        if not result.get("success", False):
            if result.get("error") == "Training data not found":
                raise HTTPException(status_code=404, detail=result)
            return result

        return result

    @router.patch("/{imdb_id}/rerun_metadata", response_model=MetadataRerunResponse)
    async def rerun_metadata(
        imdb_id: str = Path(..., description="The IMDB ID of the media item (format: tt followed by 7-8 digits)")
    ):
        """
        Re-collect metadata from TMDB and OMDB APIs for an existing training record.

        This endpoint:
        1. Looks up the training record by IMDB ID
        2. Fetches fresh metadata from TMDB (using tmdb_id if available)
        3. Fetches fresh ratings from OMDB (using imdb_id)
        4. Updates the training record with new metadata
        """
        # Get existing training record
        training_result = db_service.get_training_by_imdb_id(imdb_id)

        if not training_result.get("success", False):
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": training_result.get("message", "Training data not found"),
                    "imdb_id": imdb_id,
                    "error": training_result.get("error")
                }
            )

        training_data = training_result["data"]
        tmdb_id = training_data.get("tmdb_id")
        media_type = training_data.get("media_type", "movie")

        # Collect metadata from APIs
        metadata_result = metadata_service.collect_all_metadata(
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
            media_type=media_type
        )

        if not metadata_result.get("success", False):
            return {
                "success": False,
                "message": "Failed to collect metadata from external APIs",
                "imdb_id": imdb_id,
                "error": "API collection failed",
                "tmdb_success": metadata_result.get("tmdb_success", False),
                "omdb_success": metadata_result.get("omdb_success", False),
                "errors": metadata_result.get("errors", [])
            }

        # Update training record with new metadata
        collected_metadata = metadata_result.get("data", {})

        if not collected_metadata:
            return {
                "success": False,
                "message": "No metadata collected from APIs",
                "imdb_id": imdb_id,
                "error": "Empty metadata response",
                "tmdb_success": metadata_result.get("tmdb_success", False),
                "omdb_success": metadata_result.get("omdb_success", False),
                "errors": metadata_result.get("errors", [])
            }

        # Update the training record
        update_result = db_service.update_training_metadata(imdb_id, collected_metadata)

        if not update_result.get("success", False):
            return {
                "success": False,
                "message": "Failed to update training record",
                "imdb_id": imdb_id,
                "error": update_result.get("error"),
                "tmdb_success": metadata_result.get("tmdb_success", False),
                "omdb_success": metadata_result.get("omdb_success", False),
                "errors": metadata_result.get("errors", [])
            }

        return {
            "success": True,
            "message": "Metadata successfully re-collected and updated",
            "imdb_id": imdb_id,
            "tmdb_success": metadata_result.get("tmdb_success", False),
            "omdb_success": metadata_result.get("omdb_success", False),
            "errors": metadata_result.get("errors", []) if metadata_result.get("errors") else None,
            "updated_fields": update_result.get("updated_fields"),
            "fields_updated_count": update_result.get("fields_updated_count")
        }

    async def process_batch_metadata(job_id: str, imdb_ids: List[str]) -> None:
        """
        Background task to process batch metadata rerun.

        Processes each IMDB ID with rate limiting (1 record per second),
        parallel TMDB+OMDB calls, and exponential backoff on errors.
        """
        batch_service = get_batch_job_service()
        batch_service.update_job_status(job_id, JobStatus.PROCESSING)

        # Track last call time per API for rate limiting
        last_tmdb_call = 0.0
        last_omdb_call = 0.0
        min_interval = 1.0  # 1 second between calls to same API

        for imdb_id in imdb_ids:
            try:
                # Get training record
                training_result = db_service.get_training_by_imdb_id(imdb_id)

                if not training_result.get("success", False):
                    batch_service.record_result(job_id, BatchJobResult(
                        imdb_id=imdb_id,
                        success=False,
                        error="Training data not found"
                    ))
                    continue

                training_data = training_result["data"]
                tmdb_id = training_data.get("tmdb_id")
                media_type = training_data.get("media_type", "movie")

                # Collect metadata with rate limiting and backoff
                metadata_result = await collect_metadata_with_backoff(
                    imdb_id, tmdb_id, media_type,
                    last_tmdb_call, last_omdb_call, min_interval
                )

                # Update last call times
                import time
                current_time = time.time()
                if metadata_result.get("tmdb_called"):
                    last_tmdb_call = current_time
                if metadata_result.get("omdb_called"):
                    last_omdb_call = current_time

                if not metadata_result.get("success", False):
                    batch_service.record_result(job_id, BatchJobResult(
                        imdb_id=imdb_id,
                        success=False,
                        error=metadata_result.get("error", "API collection failed"),
                        tmdb_success=metadata_result.get("tmdb_success", False),
                        omdb_success=metadata_result.get("omdb_success", False)
                    ))
                    continue

                # Update training record
                collected_metadata = metadata_result.get("data", {})
                if collected_metadata:
                    update_result = db_service.update_training_metadata(imdb_id, collected_metadata)

                    if not update_result.get("success", False):
                        batch_service.record_result(job_id, BatchJobResult(
                            imdb_id=imdb_id,
                            success=False,
                            error=f"DB update failed: {update_result.get('error', 'Unknown')}",
                            tmdb_success=metadata_result.get("tmdb_success", False),
                            omdb_success=metadata_result.get("omdb_success", False)
                        ))
                        continue

                batch_service.record_result(job_id, BatchJobResult(
                    imdb_id=imdb_id,
                    success=True,
                    tmdb_success=metadata_result.get("tmdb_success", False),
                    omdb_success=metadata_result.get("omdb_success", False)
                ))

            except Exception as e:
                logger.error(f"Error processing {imdb_id} in batch: {e}")
                batch_service.record_result(job_id, BatchJobResult(
                    imdb_id=imdb_id,
                    success=False,
                    error=str(e)
                ))

        # Mark job as complete
        batch_service.update_job_status(job_id, JobStatus.COMPLETED)
        job = batch_service.get_job(job_id)
        if job:
            logger.info(
                f"Batch job {job_id} completed: {job.succeeded}/{job.total} succeeded, "
                f"{job.failed} failed"
            )

    async def collect_metadata_with_backoff(
        imdb_id: str,
        tmdb_id: Optional[int],
        media_type: str,
        last_tmdb_call: float,
        last_omdb_call: float,
        min_interval: float
    ) -> dict:
        """
        Collect metadata from TMDB and OMDB with rate limiting and exponential backoff.

        Calls both APIs in parallel but respects rate limits for each.
        Uses exponential backoff on errors: 1s, 5s, 10s, 30s, 60s.
        """
        import time

        result = {
            "success": False,
            "data": {},
            "tmdb_success": False,
            "omdb_success": False,
            "tmdb_called": False,
            "omdb_called": False,
            "errors": []
        }

        combined_metadata = {}

        # Calculate wait times to respect rate limits
        current_time = time.time()
        tmdb_wait = max(0, min_interval - (current_time - last_tmdb_call))
        omdb_wait = max(0, min_interval - (current_time - last_omdb_call))

        # Collect TMDB details with backoff
        if tmdb_id:
            await asyncio.sleep(tmdb_wait)
            result["tmdb_called"] = True

            tmdb_result = None
            for attempt, delay in enumerate(BACKOFF_DELAYS):
                tmdb_result = metadata_service.collect_tmdb_details(tmdb_id, media_type)

                if tmdb_result["success"]:
                    result["tmdb_success"] = True
                    combined_metadata.update(tmdb_result["data"])
                    break
                elif "429" in str(tmdb_result.get("error", "")) or "rate" in str(tmdb_result.get("error", "")).lower():
                    # Rate limited, apply backoff
                    logger.warning(f"TMDB rate limited for {imdb_id}, waiting {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                elif "404" in str(tmdb_result.get("error", "")):
                    # Not found, skip
                    result["errors"].append(f"TMDB: {tmdb_result['error']}")
                    break
                elif "500" in str(tmdb_result.get("error", "")) or "502" in str(tmdb_result.get("error", "")) or "503" in str(tmdb_result.get("error", "")):
                    # Server error, retry once then skip
                    if attempt == 0:
                        logger.warning(f"TMDB server error for {imdb_id}, retrying once")
                        await asyncio.sleep(delay)
                    else:
                        result["errors"].append(f"TMDB: {tmdb_result['error']}")
                        break
                else:
                    # Other error, record and continue
                    result["errors"].append(f"TMDB: {tmdb_result['error']}")
                    break

        # Collect OMDB ratings with backoff
        # Recalculate wait time in case TMDB took a while
        current_time = time.time()
        omdb_wait = max(0, min_interval - (current_time - last_omdb_call))
        await asyncio.sleep(omdb_wait)
        result["omdb_called"] = True

        omdb_result = None
        for attempt, delay in enumerate(BACKOFF_DELAYS):
            omdb_result = metadata_service.collect_omdb_ratings(imdb_id, media_type)

            if omdb_result["success"]:
                result["omdb_success"] = True
                combined_metadata.update(omdb_result["data"])
                break
            elif "429" in str(omdb_result.get("error", "")) or "rate" in str(omdb_result.get("error", "")).lower():
                # Rate limited, apply backoff
                logger.warning(f"OMDB rate limited for {imdb_id}, waiting {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
            elif "404" in str(omdb_result.get("error", "")) or "not found" in str(omdb_result.get("error", "")).lower():
                # Not found, skip
                result["errors"].append(f"OMDB: {omdb_result['error']}")
                break
            elif "500" in str(omdb_result.get("error", "")) or "502" in str(omdb_result.get("error", "")) or "503" in str(omdb_result.get("error", "")):
                # Server error, retry once then skip
                if attempt == 0:
                    logger.warning(f"OMDB server error for {imdb_id}, retrying once")
                    await asyncio.sleep(delay)
                else:
                    result["errors"].append(f"OMDB: {omdb_result['error']}")
                    break
            else:
                # Other error, record and continue
                result["errors"].append(f"OMDB: {omdb_result['error']}")
                break

        # Success if at least one API succeeded
        result["success"] = result["tmdb_success"] or result["omdb_success"]
        result["data"] = combined_metadata

        return result

    @router.post("/rerun_metadata_batch", response_model=BatchJobCreateResponse, status_code=202)
    async def create_batch_metadata_rerun(
        request: BatchMetadataRequest,
        background_tasks: BackgroundTasks
    ):
        """
        Create a batch job to re-collect metadata for multiple training records.

        This endpoint:
        1. Validates all IMDB IDs exist in the database
        2. Sorts IDs alphabetically for deterministic processing order
        3. Returns immediately with a job ID (202 Accepted)
        4. Processes records in background (1 record/sec, parallel TMDB+OMDB calls)

        Use GET /training/rerun_metadata_batch/{job_id} to check progress.
        """
        batch_service = get_batch_job_service()

        # Sort IMDB IDs alphabetically for deterministic ordering
        sorted_imdb_ids = sorted(set(request.imdb_ids))  # Also deduplicate

        # Validate all IMDB IDs exist in database (fail fast)
        missing_ids = []
        for imdb_id in sorted_imdb_ids:
            result = db_service.get_training_by_imdb_id(imdb_id)
            if not result.get("success", False):
                missing_ids.append(imdb_id)

        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Validation failed",
                    "message": f"The following IMDB IDs do not exist in the database: {missing_ids[:10]}{'...' if len(missing_ids) > 10 else ''}",
                    "missing_count": len(missing_ids),
                    "missing_ids": missing_ids[:50]  # Limit to first 50 for response size
                }
            )

        # Create the job
        job = batch_service.create_job(sorted_imdb_ids)

        # Start background processing
        background_tasks.add_task(process_batch_metadata, job.job_id, sorted_imdb_ids)

        return BatchJobCreateResponse(
            job_id=job.job_id,
            status=job.status,
            total=job.total,
            message=f"Batch job created. Processing {job.total} records. Use GET /training/rerun_metadata_batch/{job.job_id} to check status."
        )

    @router.get("/rerun_metadata_batch/{job_id}", response_model=BatchJobStatusResponse)
    async def get_batch_metadata_status(
        job_id: str = Path(..., description="The batch job ID"),
        include_results: bool = Query(False, description="Include detailed results for each processed item")
    ):
        """
        Get the status of a batch metadata rerun job.

        Returns progress information including:
        - Current status (pending, validating, processing, completed, failed)
        - Total items to process
        - Items processed so far
        - Success/failure counts
        - Last processed IMDB ID (for clear cutoff point)
        - Optionally, detailed results for each item
        """
        batch_service = get_batch_job_service()
        job_status = batch_service.get_job_status(job_id)

        if not job_status:
            raise HTTPException(
                status_code=404,
                detail={"error": "Job not found", "message": f"No batch job found with ID: {job_id}"}
            )

        # Optionally exclude detailed results to reduce response size
        if not include_results:
            job_status["results"] = None

        return BatchJobStatusResponse(**job_status)

    return router