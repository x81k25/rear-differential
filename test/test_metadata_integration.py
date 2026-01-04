# test/test_metadata_integration.py
"""
Integration tests for MetadataService - uses real API calls.

NOT part of automated testing suite (CI/CD).
Run manually with: uv run pytest test/test_metadata_integration.py -v

These tests verify the metadata service works with real TMDB/OMDB APIs
using actual IMDB IDs from the database.
"""
import pytest

# Mark all tests in this file as integration tests (excluded from CI/CD)
pytestmark = [pytest.mark.integration, pytest.mark.live]
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.services.metadata_service import MetadataService
from app.services.db_service import DatabaseService


# Sample IMDB IDs from the database for testing
# These are real entries that should have valid TMDB/OMDB data
TEST_IMDB_IDS = [
    {"imdb_id": "tt0469494", "tmdb_id": 7345, "media_type": "movie", "title": "There Will Be Blood"},
    {"imdb_id": "tt7535792", "tmdb_id": 477274, "media_type": "movie", "title": "My Travel Buddy"},
]


class TestMetadataServiceLive:
    """Live integration tests for MetadataService."""

    @pytest.fixture
    def metadata_service(self):
        """Create a real MetadataService instance."""
        return MetadataService()

    @pytest.fixture
    def db_service(self):
        """Create a real DatabaseService instance."""
        return DatabaseService()

    def test_collect_tmdb_details_live(self, metadata_service):
        """Test TMDB metadata collection with real API."""
        test_data = TEST_IMDB_IDS[0]  # There Will Be Blood

        result = metadata_service.collect_tmdb_details(
            tmdb_id=test_data["tmdb_id"],
            media_type=test_data["media_type"]
        )

        print(f"\n--- TMDB Result for {test_data['title']} ---")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Data: {result['data']}")
        else:
            print(f"Error: {result['error']}")

        assert result["success"] is True, f"TMDB API failed: {result.get('error')}"
        assert "media_title" in result["data"] or "original_media_title" in result["data"]
        assert "tmdb_rating" in result["data"]

    def test_collect_omdb_ratings_live(self, metadata_service):
        """Test OMDB ratings collection with real API."""
        test_data = TEST_IMDB_IDS[0]  # There Will Be Blood

        result = metadata_service.collect_omdb_ratings(
            imdb_id=test_data["imdb_id"],
            media_type=test_data["media_type"]
        )

        print(f"\n--- OMDB Result for {test_data['title']} ---")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Data: {result['data']}")
        else:
            print(f"Error: {result['error']}")

        assert result["success"] is True, f"OMDB API failed: {result.get('error')}"
        assert "imdb_rating" in result["data"]

    def test_collect_all_metadata_live(self, metadata_service):
        """Test combined metadata collection with real APIs."""
        test_data = TEST_IMDB_IDS[0]  # There Will Be Blood

        result = metadata_service.collect_all_metadata(
            imdb_id=test_data["imdb_id"],
            tmdb_id=test_data["tmdb_id"],
            media_type=test_data["media_type"]
        )

        print(f"\n--- Combined Result for {test_data['title']} ---")
        print(f"Success: {result['success']}")
        print(f"TMDB Success: {result['tmdb_success']}")
        print(f"OMDB Success: {result['omdb_success']}")
        print(f"Errors: {result['errors']}")
        print(f"Data keys: {list(result['data'].keys())}")
        print(f"Data: {result['data']}")

        assert result["success"] is True, f"Combined collection failed"
        assert result["tmdb_success"] is True
        assert result["omdb_success"] is True

    def test_collect_all_metadata_multiple_movies(self, metadata_service):
        """Test metadata collection for multiple movies."""
        print("\n--- Testing multiple movies ---")

        for test_data in TEST_IMDB_IDS:
            result = metadata_service.collect_all_metadata(
                imdb_id=test_data["imdb_id"],
                tmdb_id=test_data["tmdb_id"],
                media_type=test_data["media_type"]
            )

            print(f"\n{test_data['title']} ({test_data['imdb_id']}):")
            print(f"  Success: {result['success']}")
            print(f"  TMDB: {result['tmdb_success']}, OMDB: {result['omdb_success']}")
            print(f"  Fields collected: {len(result['data'])}")

            assert result["success"] is True, f"Failed for {test_data['title']}"


class TestRerunMetadataEndpointLive:
    """Live integration tests for the rerun_metadata endpoint."""

    @pytest.fixture
    def db_service(self):
        """Create a real DatabaseService instance."""
        return DatabaseService()

    @pytest.fixture
    def metadata_service(self):
        """Create a real MetadataService instance."""
        return MetadataService()

    def test_get_training_by_imdb_id(self, db_service):
        """Test fetching training data by IMDB ID."""
        test_data = TEST_IMDB_IDS[0]

        result = db_service.get_training_by_imdb_id(test_data["imdb_id"])

        print(f"\n--- Training Data for {test_data['imdb_id']} ---")
        print(f"Success: {result['success']}")
        if result['success']:
            data = result['data']
            print(f"IMDB ID: {data.get('imdb_id')}")
            print(f"TMDB ID: {data.get('tmdb_id')}")
            print(f"Title: {data.get('media_title')}")
            print(f"Media Type: {data.get('media_type')}")

        assert result["success"] is True

    def test_full_rerun_metadata_flow(self, db_service, metadata_service):
        """Test the full metadata rerun flow (without actually updating DB)."""
        test_data = TEST_IMDB_IDS[0]

        # Step 1: Get training record
        training_result = db_service.get_training_by_imdb_id(test_data["imdb_id"])
        assert training_result["success"] is True

        training_data = training_result["data"]
        tmdb_id = training_data.get("tmdb_id")
        media_type = training_data.get("media_type")

        print(f"\n--- Full Rerun Flow for {test_data['title']} ---")
        print(f"Training record found: {training_data.get('media_title')}")
        print(f"TMDB ID: {tmdb_id}, Media Type: {media_type}")

        # Step 2: Collect metadata
        metadata_result = metadata_service.collect_all_metadata(
            imdb_id=test_data["imdb_id"],
            tmdb_id=tmdb_id,
            media_type=media_type
        )

        assert metadata_result["success"] is True

        print(f"\nMetadata collected successfully:")
        print(f"  Fields: {list(metadata_result['data'].keys())}")

        # Step 3: Simulate what would be updated (don't actually update)
        collected_metadata = metadata_result.get("data", {})
        updateable_fields = [
            "media_title", "release_year", "budget", "revenue", "runtime",
            "origin_country", "production_companies", "production_countries",
            "production_status", "original_language", "spoken_languages",
            "genre", "original_media_title", "tagline", "overview",
            "tmdb_rating", "tmdb_votes", "rt_score", "metascore",
            "imdb_rating", "imdb_votes"
        ]

        fields_to_update = {k: v for k, v in collected_metadata.items()
                          if k in updateable_fields and v is not None}

        print(f"\nFields that would be updated ({len(fields_to_update)}):")
        for field, value in fields_to_update.items():
            # Truncate long values for display
            display_value = str(value)[:50] + "..." if len(str(value)) > 50 else value
            print(f"  {field}: {display_value}")


class TestRerunMetadataEndpointHTTP:
    """HTTP-level integration tests for rerun_metadata endpoint."""

    @pytest.fixture
    def api_url(self):
        """Base URL for the running API (assumes API is running locally)."""
        return "http://127.0.0.1:8000/rear-diff"

    def test_rerun_metadata_endpoint_http(self, api_url):
        """Test the actual HTTP endpoint (requires API to be running)."""
        import requests

        test_data = TEST_IMDB_IDS[0]

        try:
            response = requests.patch(
                f"{api_url}/training/{test_data['imdb_id']}/rerun_metadata",
                timeout=30
            )

            print(f"\n--- HTTP Endpoint Test ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["imdb_id"] == test_data["imdb_id"]

        except requests.exceptions.ConnectionError:
            pytest.skip("API not running locally - start with 'uv run python -m app.main'")

    def test_rerun_metadata_endpoint_not_found(self, api_url):
        """Test endpoint returns 404 for non-existent IMDB ID."""
        import requests

        try:
            response = requests.patch(
                f"{api_url}/training/tt9999999/rerun_metadata",
                timeout=30
            )

            print(f"\n--- 404 Test ---")
            print(f"Status Code: {response.status_code}")

            assert response.status_code == 404

        except requests.exceptions.ConnectionError:
            pytest.skip("API not running locally - start with 'uv run python -m app.main'")
