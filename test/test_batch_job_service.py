# test/test_batch_job_service.py
"""Unit tests for BatchJobService."""
import pytest
from datetime import datetime
from unittest.mock import patch

from app.services.batch_job_service import BatchJobService, get_batch_job_service, BatchJob
from app.models.api import JobStatus, BatchJobResult


class TestBatchJobService:
    """Test BatchJobService functionality."""

    @pytest.fixture
    def service(self):
        """Create a fresh BatchJobService instance for each test."""
        return BatchJobService()

    def test_create_job(self, service):
        """Test creating a new batch job."""
        imdb_ids = ["tt0000001", "tt0000002", "tt0000003"]
        job = service.create_job(imdb_ids)

        assert job.job_id is not None
        assert len(job.job_id) == 36  # UUID length with hyphens
        assert job.status == JobStatus.PENDING
        assert job.total == 3
        assert job.processed == 0
        assert job.succeeded == 0
        assert job.failed == 0
        assert job.imdb_ids == imdb_ids
        assert job.started_at is not None
        assert job.completed_at is None
        assert job.last_processed is None

    def test_get_job_exists(self, service):
        """Test getting an existing job."""
        imdb_ids = ["tt0000001"]
        created_job = service.create_job(imdb_ids)

        retrieved_job = service.get_job(created_job.job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == created_job.job_id
        assert retrieved_job.total == 1

    def test_get_job_not_exists(self, service):
        """Test getting a non-existent job returns None."""
        retrieved_job = service.get_job("non-existent-id")
        assert retrieved_job is None

    def test_update_job_status_processing(self, service):
        """Test updating job status to processing."""
        job = service.create_job(["tt0000001"])

        service.update_job_status(job.job_id, JobStatus.PROCESSING)

        updated_job = service.get_job(job.job_id)
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.completed_at is None

    def test_update_job_status_completed(self, service):
        """Test updating job status to completed sets completed_at."""
        job = service.create_job(["tt0000001"])

        service.update_job_status(job.job_id, JobStatus.COMPLETED)

        updated_job = service.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.completed_at is not None

    def test_update_job_status_failed_with_error(self, service):
        """Test updating job status to failed with error message."""
        job = service.create_job(["tt0000001"])

        service.update_job_status(job.job_id, JobStatus.FAILED, error="Test error")

        updated_job = service.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert updated_job.error == "Test error"
        assert updated_job.completed_at is not None

    def test_record_result_success(self, service):
        """Test recording a successful result."""
        job = service.create_job(["tt0000001", "tt0000002"])

        result = BatchJobResult(
            imdb_id="tt0000001",
            success=True,
            tmdb_success=True,
            omdb_success=True
        )
        service.record_result(job.job_id, result)

        updated_job = service.get_job(job.job_id)
        assert updated_job.processed == 1
        assert updated_job.succeeded == 1
        assert updated_job.failed == 0
        assert updated_job.last_processed == "tt0000001"
        assert len(updated_job.results) == 1
        assert updated_job.results[0].imdb_id == "tt0000001"

    def test_record_result_failure(self, service):
        """Test recording a failed result."""
        job = service.create_job(["tt0000001", "tt0000002"])

        result = BatchJobResult(
            imdb_id="tt0000001",
            success=False,
            error="API error",
            tmdb_success=False,
            omdb_success=True
        )
        service.record_result(job.job_id, result)

        updated_job = service.get_job(job.job_id)
        assert updated_job.processed == 1
        assert updated_job.succeeded == 0
        assert updated_job.failed == 1
        assert updated_job.last_processed == "tt0000001"

    def test_record_multiple_results(self, service):
        """Test recording multiple results."""
        job = service.create_job(["tt0000001", "tt0000002", "tt0000003"])

        # Record mixed results
        service.record_result(job.job_id, BatchJobResult(imdb_id="tt0000001", success=True))
        service.record_result(job.job_id, BatchJobResult(imdb_id="tt0000002", success=False, error="Error"))
        service.record_result(job.job_id, BatchJobResult(imdb_id="tt0000003", success=True))

        updated_job = service.get_job(job.job_id)
        assert updated_job.processed == 3
        assert updated_job.succeeded == 2
        assert updated_job.failed == 1
        assert updated_job.last_processed == "tt0000003"
        assert len(updated_job.results) == 3

    def test_get_job_status_as_dict(self, service):
        """Test getting job status as dictionary."""
        job = service.create_job(["tt0000001"])
        service.update_job_status(job.job_id, JobStatus.PROCESSING)
        service.record_result(job.job_id, BatchJobResult(imdb_id="tt0000001", success=True))

        status = service.get_job_status(job.job_id)

        assert status is not None
        assert status["job_id"] == job.job_id
        assert status["status"] == JobStatus.PROCESSING
        assert status["total"] == 1
        assert status["processed"] == 1
        assert status["succeeded"] == 1
        assert status["failed"] == 0
        assert status["last_processed"] == "tt0000001"
        assert status["started_at"] is not None
        assert len(status["results"]) == 1

    def test_get_job_status_not_found(self, service):
        """Test getting status for non-existent job."""
        status = service.get_job_status("non-existent-id")
        assert status is None

    def test_cleanup_old_jobs(self, service):
        """Test cleanup of old completed jobs."""
        # Create and complete a job
        job = service.create_job(["tt0000001"])
        service.update_job_status(job.job_id, JobStatus.COMPLETED)

        # Manually set completed_at to old time
        old_job = service.get_job(job.job_id)
        old_job.completed_at = datetime(2020, 1, 1)

        # Cleanup jobs older than 1 hour
        removed = service.cleanup_old_jobs(max_age_hours=1)

        assert removed == 1
        assert service.get_job(job.job_id) is None

    def test_cleanup_keeps_recent_jobs(self, service):
        """Test cleanup keeps recent completed jobs."""
        job = service.create_job(["tt0000001"])
        service.update_job_status(job.job_id, JobStatus.COMPLETED)

        # Cleanup - job was just completed so should not be removed
        removed = service.cleanup_old_jobs(max_age_hours=24)

        assert removed == 0
        assert service.get_job(job.job_id) is not None

    def test_cleanup_keeps_pending_jobs(self, service):
        """Test cleanup doesn't remove pending jobs."""
        job = service.create_job(["tt0000001"])
        # Job is PENDING, not completed

        removed = service.cleanup_old_jobs(max_age_hours=0)  # 0 hours = immediate

        assert removed == 0
        assert service.get_job(job.job_id) is not None


class TestGetBatchJobService:
    """Test singleton pattern for BatchJobService."""

    def test_singleton_returns_same_instance(self):
        """Test that get_batch_job_service returns the same instance."""
        # Reset the global singleton for testing
        import app.services.batch_job_service as module
        module._batch_job_service = None

        service1 = get_batch_job_service()
        service2 = get_batch_job_service()

        assert service1 is service2

    def test_singleton_persists_jobs(self):
        """Test that jobs persist across get_batch_job_service calls."""
        import app.services.batch_job_service as module
        module._batch_job_service = None

        service1 = get_batch_job_service()
        job = service1.create_job(["tt0000001"])

        service2 = get_batch_job_service()
        retrieved_job = service2.get_job(job.job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id


class TestBatchJobModel:
    """Test BatchJob dataclass."""

    def test_batch_job_defaults(self):
        """Test BatchJob default values."""
        job = BatchJob(
            job_id="test-id",
            status=JobStatus.PENDING,
            imdb_ids=["tt0000001"],
            total=1
        )

        assert job.processed == 0
        assert job.succeeded == 0
        assert job.failed == 0
        assert job.last_processed is None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.error is None
        assert job.results == []

    def test_batch_job_with_all_fields(self):
        """Test BatchJob with all fields populated."""
        now = datetime.utcnow()
        results = [BatchJobResult(imdb_id="tt0000001", success=True)]

        job = BatchJob(
            job_id="test-id",
            status=JobStatus.COMPLETED,
            imdb_ids=["tt0000001"],
            total=1,
            processed=1,
            succeeded=1,
            failed=0,
            last_processed="tt0000001",
            started_at=now,
            completed_at=now,
            error=None,
            results=results
        )

        assert job.processed == 1
        assert job.succeeded == 1
        assert job.last_processed == "tt0000001"
        assert len(job.results) == 1
