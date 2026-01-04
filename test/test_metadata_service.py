# test/test_metadata_service.py
"""Unit tests for MetadataService - mocked API calls for CI/CD."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.metadata_service import MetadataService


class TestMetadataServiceTMDB:
    """Test TMDB metadata collection with mocked responses."""

    @pytest.fixture
    def metadata_service(self):
        """Create a MetadataService instance with mocked config."""
        with patch('app.services.metadata_service.settings') as mock_settings:
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/movie"
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_TV_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/tv"
            mock_settings.REAR_DIFF_TV_DETAILS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_TV_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_TV_RATINGS_API_KEY = "test_key"
            yield MetadataService()

    @patch('app.services.metadata_service.requests.get')
    def test_collect_tmdb_details_movie_success(self, mock_get, metadata_service):
        """Test successful TMDB movie details collection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 550,
            "imdb_id": "tt0137523",
            "title": "Fight Club",
            "original_title": "Fight Club",
            "release_date": "1999-10-15",
            "budget": 63000000,
            "revenue": 100853753,
            "runtime": 139,
            "origin_country": ["US"],
            "production_companies": [{"name": "Fox 2000 Pictures"}],
            "production_countries": [{"iso_3166_1": "US"}],
            "status": "Released",
            "original_language": "en",
            "spoken_languages": [{"iso_639_1": "en"}],
            "genres": [{"name": "Drama"}, {"name": "Thriller"}],
            "overview": "A ticking-Loss of control movie.",
            "tagline": "Mischief. Mayhem. Soap.",
            "vote_average": 8.4,
            "vote_count": 25000
        }
        mock_get.return_value = mock_response

        result = metadata_service.collect_tmdb_details(550, "movie")

        assert result["success"] is True
        assert result["data"]["imdb_id"] == "tt0137523"
        assert result["data"]["media_title"] == "Fight Club"
        assert result["data"]["release_year"] == 1999
        assert result["data"]["budget"] == 63000000
        assert result["data"]["runtime"] == 139
        assert result["data"]["genre"] == ["Drama", "Thriller"]
        assert result["data"]["tmdb_rating"] == 8.4

    @patch('app.services.metadata_service.requests.get')
    def test_collect_tmdb_details_tv_success(self, mock_get, metadata_service):
        """Test successful TMDB TV details collection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1399,
            "name": "Game of Thrones",
            "original_name": "Game of Thrones",
            "first_air_date": "2011-04-17",
            "origin_country": ["US"],
            "production_companies": [{"name": "HBO"}],
            "production_countries": [{"iso_3166_1": "US"}],
            "status": "Ended",
            "original_language": "en",
            "spoken_languages": [{"iso_639_1": "en"}],
            "genres": [{"name": "Drama"}, {"name": "Fantasy"}],
            "overview": "Seven noble families fight for control.",
            "tagline": "Winter Is Coming",
            "vote_average": 8.3,
            "vote_count": 18000
        }
        mock_get.return_value = mock_response

        result = metadata_service.collect_tmdb_details(1399, "tv_show")

        assert result["success"] is True
        assert result["data"]["media_title"] == "Game of Thrones"
        assert result["data"]["release_year"] == 2011
        assert result["data"]["genre"] == ["Drama", "Fantasy"]

    @patch('app.services.metadata_service.requests.get')
    def test_collect_tmdb_details_api_error(self, mock_get, metadata_service):
        """Test TMDB API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = metadata_service.collect_tmdb_details(99999999, "movie")

        assert result["success"] is False
        assert "404" in result["error"]

    @patch('app.services.metadata_service.requests.get')
    def test_collect_tmdb_details_request_exception(self, mock_get, metadata_service):
        """Test TMDB request exception handling."""
        import requests as req
        mock_get.side_effect = req.RequestException("Connection timeout")

        result = metadata_service.collect_tmdb_details(550, "movie")

        assert result["success"] is False
        assert "Connection timeout" in result["error"]

    def test_collect_tmdb_details_no_api_key(self):
        """Test TMDB collection without API key."""
        with patch('app.services.metadata_service.settings') as mock_settings:
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/movie"
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_KEY = ""  # Empty key
            mock_settings.REAR_DIFF_TV_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/tv"
            mock_settings.REAR_DIFF_TV_DETAILS_API_KEY = ""
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_KEY = ""
            mock_settings.REAR_DIFF_TV_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_TV_RATINGS_API_KEY = ""
            service = MetadataService()

        result = service.collect_tmdb_details(550, "movie")

        assert result["success"] is False
        assert "not configured" in result["error"]


class TestMetadataServiceOMDB:
    """Test OMDB ratings collection with mocked responses."""

    @pytest.fixture
    def metadata_service(self):
        """Create a MetadataService instance with mocked config."""
        with patch('app.services.metadata_service.settings') as mock_settings:
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/movie"
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_TV_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/tv"
            mock_settings.REAR_DIFF_TV_DETAILS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_TV_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_TV_RATINGS_API_KEY = "test_key"
            yield MetadataService()

    @patch('app.services.metadata_service.requests.get')
    def test_collect_omdb_ratings_movie_success(self, mock_get, metadata_service):
        """Test successful OMDB movie ratings collection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "True",
            "imdbRating": "8.8",
            "imdbVotes": "2,000,000",
            "Metascore": "66",
            "Ratings": [
                {"Source": "Rotten Tomatoes", "Value": "79%"}
            ]
        }
        mock_get.return_value = mock_response

        result = metadata_service.collect_omdb_ratings("tt0137523", "movie")

        assert result["success"] is True
        assert result["data"]["imdb_rating"] == 8.8
        assert result["data"]["imdb_votes"] == 2000000
        assert result["data"]["metascore"] == 66
        assert result["data"]["rt_score"] == 79

    @patch('app.services.metadata_service.requests.get')
    def test_collect_omdb_ratings_tv_success(self, mock_get, metadata_service):
        """Test successful OMDB TV ratings collection (no RT score)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "True",
            "imdbRating": "9.3",
            "imdbVotes": "1,500,000",
            "Metascore": "N/A"
        }
        mock_get.return_value = mock_response

        result = metadata_service.collect_omdb_ratings("tt0903747", "tv_show")

        assert result["success"] is True
        assert result["data"]["imdb_rating"] == 9.3
        assert result["data"]["imdb_votes"] == 1500000
        assert "metascore" not in result["data"]  # N/A values excluded
        assert "rt_score" not in result["data"]  # TV shows don't get RT

    @patch('app.services.metadata_service.requests.get')
    def test_collect_omdb_ratings_not_found(self, mock_get, metadata_service):
        """Test OMDB not found response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Response": "False",
            "Error": "Movie not found!"
        }
        mock_get.return_value = mock_response

        result = metadata_service.collect_omdb_ratings("tt9999999", "movie")

        assert result["success"] is False
        assert "Movie not found" in result["error"]

    @patch('app.services.metadata_service.requests.get')
    def test_collect_omdb_ratings_api_error(self, mock_get, metadata_service):
        """Test OMDB API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = metadata_service.collect_omdb_ratings("tt0137523", "movie")

        assert result["success"] is False
        assert "500" in result["error"]


class TestMetadataServiceCombined:
    """Test combined metadata collection."""

    @pytest.fixture
    def metadata_service(self):
        """Create a MetadataService instance with mocked config."""
        with patch('app.services.metadata_service.settings') as mock_settings:
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/movie"
            mock_settings.REAR_DIFF_MOVIE_DETAILS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_TV_DETAILS_API_BASE_URL = "https://api.themoviedb.org/3/tv"
            mock_settings.REAR_DIFF_TV_DETAILS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_MOVIE_RATINGS_API_KEY = "test_key"
            mock_settings.REAR_DIFF_TV_RATINGS_API_BASE_URL = "http://www.omdbapi.com/"
            mock_settings.REAR_DIFF_TV_RATINGS_API_KEY = "test_key"
            yield MetadataService()

    @patch('app.services.metadata_service.requests.get')
    def test_collect_all_metadata_both_success(self, mock_get, metadata_service):
        """Test collecting from both APIs successfully."""
        def mock_response(url, *args, **kwargs):
            response = MagicMock()
            response.status_code = 200
            if "themoviedb" in url:
                response.json.return_value = {
                    "id": 550,
                    "title": "Fight Club",
                    "release_date": "1999-10-15",
                    "budget": 63000000,
                    "genres": [{"name": "Drama"}],
                    "vote_average": 8.4
                }
            else:
                response.json.return_value = {
                    "Response": "True",
                    "imdbRating": "8.8",
                    "imdbVotes": "2,000,000"
                }
            return response

        mock_get.side_effect = mock_response

        result = metadata_service.collect_all_metadata("tt0137523", 550, "movie")

        assert result["success"] is True
        assert result["tmdb_success"] is True
        assert result["omdb_success"] is True
        assert result["data"]["media_title"] == "Fight Club"
        assert result["data"]["imdb_rating"] == 8.8

    @patch('app.services.metadata_service.requests.get')
    def test_collect_all_metadata_tmdb_only(self, mock_get, metadata_service):
        """Test collecting when only TMDB succeeds."""
        def mock_response(url, *args, **kwargs):
            response = MagicMock()
            if "themoviedb" in url:
                response.status_code = 200
                response.json.return_value = {
                    "id": 550,
                    "title": "Fight Club",
                    "release_date": "1999-10-15"
                }
            else:
                response.status_code = 500
            return response

        mock_get.side_effect = mock_response

        result = metadata_service.collect_all_metadata("tt0137523", 550, "movie")

        assert result["success"] is True  # At least one succeeded
        assert result["tmdb_success"] is True
        assert result["omdb_success"] is False

    @patch('app.services.metadata_service.requests.get')
    def test_collect_all_metadata_omdb_only(self, mock_get, metadata_service):
        """Test collecting when only OMDB succeeds (no tmdb_id)."""
        def mock_response(url, *args, **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "Response": "True",
                "imdbRating": "8.8",
                "imdbVotes": "2,000,000"
            }
            return response

        mock_get.side_effect = mock_response

        result = metadata_service.collect_all_metadata("tt0137523", None, "movie")

        assert result["success"] is True
        assert result["tmdb_success"] is False  # No tmdb_id provided
        assert result["omdb_success"] is True

    @patch('app.services.metadata_service.requests.get')
    def test_collect_all_metadata_both_fail(self, mock_get, metadata_service):
        """Test when both APIs fail."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = metadata_service.collect_all_metadata("tt0137523", 550, "movie")

        assert result["success"] is False
        assert result["tmdb_success"] is False
        assert result["omdb_success"] is False
        assert len(result["errors"]) == 2
