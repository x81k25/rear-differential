# app/services/batch_job_service.py
import asyncio
import logging
import uuid
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.models.api import JobStatus, BatchJobResult

logger = logging.getLogger(__name__)


@dataclass
class BatchJob:
    """Represents a batch processing job."""
    job_id: str
    status: JobStatus
    imdb_ids: List[str]
    total: int
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    last_processed: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    results: List[BatchJobResult] = field(default_factory=list)


class BatchJobService:
    """Service for managing batch processing jobs."""

    def __init__(self):
        self._jobs: Dict[str, BatchJob] = {}
        self._lock = Lock()

    def create_job(self, imdb_ids: List[str]) -> BatchJob:
        """
        Create a new batch job.

        Args:
            imdb_ids: List of IMDB IDs to process (should be pre-sorted)

        Returns:
            The created BatchJob
        """
        job_id = str(uuid.uuid4())
        job = BatchJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            imdb_ids=imdb_ids,
            total=len(imdb_ids),
            started_at=datetime.utcnow()
        )

        with self._lock:
            self._jobs[job_id] = job

        logger.info(f"Created batch job {job_id} with {len(imdb_ids)} items")
        return job

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """
        Get a job by ID.

        Args:
            job_id: The job ID

        Returns:
            The BatchJob or None if not found
        """
        with self._lock:
            return self._jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus, error: Optional[str] = None) -> None:
        """
        Update job status.

        Args:
            job_id: The job ID
            status: New status
            error: Optional error message
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                if error:
                    job.error = error
                if status == JobStatus.COMPLETED or status == JobStatus.FAILED:
                    job.completed_at = datetime.utcnow()
                logger.debug(f"Job {job_id} status updated to {status}")

    def record_result(self, job_id: str, result: BatchJobResult) -> None:
        """
        Record a processing result for a job.

        Args:
            job_id: The job ID
            result: The result to record
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.results.append(result)
                job.processed += 1
                job.last_processed = result.imdb_id
                if result.success:
                    job.succeeded += 1
                else:
                    job.failed += 1

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status as a dictionary.

        Args:
            job_id: The job ID

        Returns:
            Dictionary with job status or None if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            return {
                "job_id": job.job_id,
                "status": job.status,
                "total": job.total,
                "processed": job.processed,
                "succeeded": job.succeeded,
                "failed": job.failed,
                "last_processed": job.last_processed,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error": job.error,
                "results": job.results
            }

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove jobs older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of jobs removed
        """
        now = datetime.utcnow()
        removed = 0

        with self._lock:
            jobs_to_remove = []
            for job_id, job in self._jobs.items():
                if job.completed_at:
                    age = (now - job.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old batch jobs")

        return removed


# Global singleton instance
_batch_job_service: Optional[BatchJobService] = None


def get_batch_job_service() -> BatchJobService:
    """Get the global BatchJobService instance."""
    global _batch_job_service
    if _batch_job_service is None:
        _batch_job_service = BatchJobService()
    return _batch_job_service
