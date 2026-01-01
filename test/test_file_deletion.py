"""
E2E Integration Test for File Deletion Feature

This test works with pre-existing test data (tt9999901) in the database.
The rear_diff user only has UPDATE permission on atp.training and atp.media,
so we cannot INSERT or DELETE test records programmatically.

Test flow:
1. Reset training label via UPDATE (reset to would_watch)
2. Copy test media file to cache/library paths
3. Add torrent to Transmission (for torrent removal tests)
4. Start the API server
5. Call the /reject endpoint
6. Verify files are deleted
7. Verify torrent is removed from Transmission
8. Clean up test files (not DB records)
"""
import os
import shutil
import subprocess
import time
import signal
import requests
import psycopg2
import yaml
from pathlib import Path
from typing import Optional
import pytest
from transmission_rpc import Client as TransmissionClient
from transmission_rpc.error import TransmissionError

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "test" / "fixtures"
FIXTURE_YAML = FIXTURES_DIR / "file_deletion_test.yaml"
FIXTURE_MEDIA_DIR = FIXTURES_DIR / "media"

# Test data constants (pre-inserted in database)
TEST_IMDB_ID = "tt9999901"
TEST_HASH = "0000000000000000000000000000000099999901"
TEST_TORRENT_HASH = "55af51b9883b2e29e02fc728113747c706e480e3"
TEST_TORRENT_LINK = "https://yts.lt/torrent/download/55AF51B9883B2E29E02FC728113747C706E480E3"


def load_env():
    """Load environment variables from .env file."""
    env_file = PROJECT_ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes
                    value = value.strip("'\"")
                    env_vars[key] = value
                    os.environ[key] = value
    return env_vars


def load_fixture():
    """Load test fixture YAML."""
    with open(FIXTURE_YAML) as f:
        return yaml.safe_load(f)


class DatabaseHelper:
    """Helper class for database operations."""

    def __init__(self, env_vars: dict):
        self.conn_params = {
            "host": env_vars.get("REAR_DIFF_PGSQL_HOST", "localhost"),
            "port": env_vars.get("REAR_DIFF_PGSQL_PORT", "5432"),
            "user": env_vars.get("REAR_DIFF_PGSQL_USERNAME", "postgres"),
            "password": env_vars.get("REAR_DIFF_PGSQL_PASSWORD"),
            "dbname": env_vars.get("REAR_DIFF_PGSQL_DATABASE", "postgres"),
        }

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def reset_training_label(self, imdb_id: str) -> bool:
        """Reset training record to initial state (would_watch, not reviewed)."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE atp.training
                    SET label = 'would_watch',
                        human_labeled = false,
                        reviewed = false
                    WHERE imdb_id = %s
                    """,
                    (imdb_id,),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()

    def update_media_parent_path(self, hash: str, parent_path: str) -> bool:
        """Update the parent_path in atp.media for test setup."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE atp.media
                    SET parent_path = %s
                    WHERE hash = %s
                    """,
                    (parent_path, hash),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()

    def get_training_record(self, imdb_id: str) -> Optional[dict]:
        """Get the current training record."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT label, human_labeled, reviewed
                    FROM atp.training
                    WHERE imdb_id = %s
                    """,
                    (imdb_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "label": row[0],
                        "human_labeled": row[1],
                        "reviewed": row[2],
                    }
                return None
        finally:
            conn.close()

    def verify_test_data_exists(self, imdb_id: str, hash: str) -> tuple[bool, bool]:
        """Check if test data exists in both tables."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM atp.training WHERE imdb_id = %s", (imdb_id,)
                )
                training_exists = cur.fetchone() is not None

                cur.execute("SELECT 1 FROM atp.media WHERE hash = %s", (hash,))
                media_exists = cur.fetchone() is not None

                return training_exists, media_exists
        finally:
            conn.close()


class APIServer:
    """Helper class to manage the API server process."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.base_url = "http://localhost:8000"

    def start(self, timeout: int = 15):
        """Start the API server."""
        # Kill any existing process on port 8000
        subprocess.run(["fuser", "-k", "8000/tcp"], capture_output=True)
        time.sleep(1)

        # Start the server
        self.process = subprocess.Popen(
            ["uv", "run", "python", "-m", "app.main"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.base_url}/rear-diff/health", timeout=1)
                if resp.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)

        # If we get here, server didn't start - get error output
        if self.process:
            stdout, stderr = self.process.communicate(timeout=2)
            raise RuntimeError(
                f"API server failed to start.\nstdout: {stdout.decode()}\nstderr: {stderr.decode()}"
            )

    def stop(self):
        """Stop the API server."""
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def reject(self, imdb_id: str) -> dict:
        """Call the reject endpoint."""
        resp = requests.patch(f"{self.base_url}/rear-diff/training/{imdb_id}/reject")
        resp.raise_for_status()
        return resp.json()


class TransmissionHelper:
    """Helper class for Transmission operations in tests."""

    def __init__(self, env_vars: dict):
        self.host = env_vars.get("REAR_DIFF_TRANSMISSION_HOST", "localhost")
        self.port = int(env_vars.get("REAR_DIFF_TRANSMISSION_PORT", "9091"))
        self.username = env_vars.get("REAR_DIFF_TRANSMISSION_USERNAME", "")
        self.password = env_vars.get("REAR_DIFF_TRANSMISSION_PASSWORD", "")

    def get_client(self) -> TransmissionClient:
        """Get a Transmission RPC client."""
        return TransmissionClient(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )

    def add_torrent(self, torrent_link: str) -> bool:
        """Add a torrent to Transmission. Returns True if added or already exists."""
        try:
            client = self.get_client()
            client.add_torrent(torrent_link)
            return True
        except TransmissionError as e:
            # Duplicate torrent is OK
            if "duplicate" in str(e).lower():
                return True
            raise

    def torrent_exists(self, torrent_hash: str) -> bool:
        """Check if a torrent exists in Transmission."""
        try:
            client = self.get_client()
            client.get_torrent(torrent_hash)
            return True
        except (TransmissionError, KeyError, Exception):
            return False

    def remove_torrent(self, torrent_hash: str) -> bool:
        """Remove a torrent from Transmission. Returns True if removed or not found."""
        try:
            client = self.get_client()
            client.remove_torrent(torrent_hash, delete_data=True)
            return True
        except TransmissionError:
            return True  # Not found is OK


class TestFileDeletion:
    """E2E test for file deletion feature."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.env_vars = load_env()
        self.fixture = load_fixture()
        self.db = DatabaseHelper(self.env_vars)
        self.api = APIServer()
        self.transmission = TransmissionHelper(self.env_vars)

        # Get paths from env vars
        self.cache_path = self.env_vars.get("REAR_DIFF_MEDIA_CACHE_PATH", "").rstrip(
            "/"
        )
        self.library_movies_path = self.env_vars.get(
            "REAR_DIFF_MEDIA_LIBRARY_PATH_MOVIES", ""
        ).rstrip("/")

        # Test data from fixture
        self.test_file = self.fixture["test_file"]
        self.expected = self.fixture["expected"]
        self.target_dir = self.test_file["target_dir"]

        # Verify test data exists in database
        training_exists, media_exists = self.db.verify_test_data_exists(
            TEST_IMDB_ID, TEST_HASH
        )
        if not training_exists or not media_exists:
            pytest.skip(
                f"Test data not found in database. "
                f"training: {training_exists}, media: {media_exists}. "
                f"Please insert test data manually for imdb_id={TEST_IMDB_ID}"
            )

        # Reset training label before each test
        self.db.reset_training_label(TEST_IMDB_ID)

        yield

        # Cleanup: stop API and remove test files (NOT DB records)
        self.cleanup_files()

    def cleanup_files(self):
        """Clean up test files (not database records)."""
        # Stop API server
        self.api.stop()

        # Delete test files from all locations
        paths_to_clean = [
            os.path.join(self.cache_path, "incomplete", self.target_dir),
            os.path.join(self.cache_path, "complete", self.target_dir),
            os.path.join(self.library_movies_path, self.target_dir),
        ]

        for path in paths_to_clean:
            if path and os.path.exists(path):
                try:
                    shutil.rmtree(path)
                except PermissionError:
                    pass  # Best effort cleanup

    def copy_test_file_to_location(self, dest_base: str) -> str:
        """Copy test file to a destination directory."""
        if not dest_base:
            pytest.skip("Destination path not configured")

        dest_path = os.path.join(dest_base, self.target_dir)

        # Create destination directory
        os.makedirs(dest_path, exist_ok=True)

        # Copy files from fixture
        source_dir = FIXTURE_MEDIA_DIR
        if not source_dir.exists():
            pytest.skip(f"Fixture media directory not found: {source_dir}")

        files_copied = 0
        for file in os.listdir(source_dir):
            src = os.path.join(source_dir, file)
            dst = os.path.join(dest_path, file)
            shutil.copy2(src, dst)
            files_copied += 1

        if files_copied == 0:
            pytest.skip(f"No files found in fixture directory: {source_dir}")

        # Set permissions (best effort)
        try:
            permissions = self.test_file.get("permissions", {})
            mode = int(permissions.get("mode", "0775"), 8)
            os.chmod(dest_path, mode)
            for file in os.listdir(dest_path):
                os.chmod(os.path.join(dest_path, file), mode)
        except PermissionError:
            pass  # Continue even if we can't set permissions

        return dest_path

    def test_delete_from_library(self):
        """Test file deletion from library path."""
        if not self.library_movies_path:
            pytest.skip("REAR_DIFF_MEDIA_LIBRARY_PATH_MOVIES not configured")

        # 1. Copy test file to library
        dest_path = self.copy_test_file_to_location(self.library_movies_path)
        assert os.path.exists(dest_path), f"Failed to create test directory: {dest_path}"

        # 2. Update media parent_path to point to library
        self.db.update_media_parent_path(TEST_HASH, self.library_movies_path)

        # 3. Verify initial state
        record = self.db.get_training_record(TEST_IMDB_ID)
        assert record is not None, "Training record not found"
        assert record["label"] == "would_watch", f"Expected 'would_watch', got '{record['label']}'"

        # 4. Start API server
        self.api.start()

        # 5. Call reject endpoint
        result = self.api.reject(TEST_IMDB_ID)

        # 6. Verify response
        assert result["success"] is True, f"API returned failure: {result}"
        assert result["file_deleted"] is True, f"File was not deleted: {result}"

        # 7. Verify file is actually deleted
        assert not os.path.exists(dest_path), f"Directory still exists: {dest_path}"

        # 8. Verify database was updated
        record = self.db.get_training_record(TEST_IMDB_ID)
        assert record["label"] == self.expected["post_rejection_label"]
        assert record["human_labeled"] == self.expected["post_rejection_human_labeled"]
        assert record["reviewed"] == self.expected["post_rejection_reviewed"]

    def test_delete_from_cache_complete(self):
        """Test file deletion from cache complete path."""
        if not self.cache_path:
            pytest.skip("REAR_DIFF_MEDIA_CACHE_PATH not configured")

        complete_path = os.path.join(self.cache_path, "complete")

        # 1. Copy test file to cache/complete
        dest_path = self.copy_test_file_to_location(complete_path)
        assert os.path.exists(dest_path), f"Failed to create test directory: {dest_path}"

        # 2. Update media parent_path to point to cache/complete
        self.db.update_media_parent_path(TEST_HASH, complete_path)

        # 3. Start API server
        self.api.start()

        # 4. Call reject endpoint
        result = self.api.reject(TEST_IMDB_ID)

        # 5. Verify response
        assert result["success"] is True, f"API returned failure: {result}"
        assert result["file_deleted"] is True, f"File was not deleted: {result}"

        # 6. Verify file is actually deleted
        assert not os.path.exists(dest_path), f"Directory still exists: {dest_path}"

    def test_delete_nonexistent_file_still_updates_label(self):
        """Test rejection when file doesn't exist (should still succeed and update label)."""
        # 1. Update media parent_path to a nonexistent location
        self.db.update_media_parent_path(TEST_HASH, "/nonexistent/path")

        # 2. Start API server
        self.api.start()

        # 3. Call reject endpoint
        result = self.api.reject(TEST_IMDB_ID)

        # 4. Should succeed even without file
        assert result["success"] is True, f"API returned failure: {result}"
        # file_deleted should be False since file doesn't exist
        assert result["file_deleted"] is False, f"Expected file_deleted=False: {result}"

        # 5. Verify database was still updated
        record = self.db.get_training_record(TEST_IMDB_ID)
        assert record["label"] == self.expected["post_rejection_label"]
        assert record["human_labeled"] is True
        assert record["reviewed"] is True

    def test_reject_already_rejected(self):
        """Test calling reject on an already rejected item."""
        # 1. Start API server
        self.api.start()

        # 2. First rejection
        result1 = self.api.reject(TEST_IMDB_ID)
        assert result1["success"] is True

        # 3. Reset for second call (simulate idempotency test)
        # Note: Don't reset label, call reject again on already-rejected item

        # 4. Second rejection should still succeed
        result2 = self.api.reject(TEST_IMDB_ID)
        assert result2["success"] is True

        # 5. Label should still be would_not_watch
        record = self.db.get_training_record(TEST_IMDB_ID)
        assert record["label"] == "would_not_watch"

    def test_torrent_removal(self):
        """Test that reject endpoint removes torrent from Transmission."""
        # 1. Add torrent to Transmission
        added = self.transmission.add_torrent(TEST_TORRENT_LINK)
        assert added, "Failed to add torrent to Transmission"

        # 2. Verify torrent exists
        exists_before = self.transmission.torrent_exists(TEST_TORRENT_HASH)
        assert exists_before, "Torrent should exist in Transmission before reject"

        # 3. Start API server
        self.api.start()

        # 4. Call reject endpoint
        result = self.api.reject(TEST_IMDB_ID)

        # 5. Verify response indicates torrent was removed
        assert result["success"] is True, f"API returned failure: {result}"
        assert result["torrent_removed"] is True, f"Torrent was not removed: {result}"

        # 6. Verify torrent no longer exists in Transmission
        exists_after = self.transmission.torrent_exists(TEST_TORRENT_HASH)
        assert not exists_after, "Torrent should not exist in Transmission after reject"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
