# app/services/metadata_service.py
import logging
import re
import requests
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MetadataService:
    """Service for fetching metadata from TMDB and OMDB APIs."""

    def __init__(self):
        # TMDB config
        self.tmdb_movie_details_url = settings.REAR_DIFF_MOVIE_DETAILS_API_BASE_URL
        self.tmdb_movie_details_key = settings.REAR_DIFF_MOVIE_DETAILS_API_KEY
        self.tmdb_tv_details_url = settings.REAR_DIFF_TV_DETAILS_API_BASE_URL
        self.tmdb_tv_details_key = settings.REAR_DIFF_TV_DETAILS_API_KEY
        # OMDB config
        self.omdb_movie_url = settings.REAR_DIFF_MOVIE_RATINGS_API_BASE_URL
        self.omdb_movie_key = settings.REAR_DIFF_MOVIE_RATINGS_API_KEY
        self.omdb_tv_url = settings.REAR_DIFF_TV_RATINGS_API_BASE_URL
        self.omdb_tv_key = settings.REAR_DIFF_TV_RATINGS_API_KEY

    def collect_tmdb_details(self, tmdb_id: int, media_type: str) -> Dict[str, Any]:
        """
        Fetch detailed metadata from TMDB API.

        :param tmdb_id: TMDB ID of the media item
        :param media_type: 'movie' or 'tv_show'/'tv_season'/'tv_episode_pack'
        :return: Dict with metadata fields
        """
        result = {"success": False, "data": {}, "error": None}

        # Determine URL and key based on media type
        if media_type == "movie":
            url = f"{self.tmdb_movie_details_url}/{tmdb_id}"
            api_key = self.tmdb_movie_details_key
        else:
            url = f"{self.tmdb_tv_details_url}/{tmdb_id}"
            api_key = self.tmdb_tv_details_key

        if not api_key:
            result["error"] = "TMDB API key not configured"
            return result

        params = {"api_key": api_key}

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                result["error"] = f"TMDB API returned status {response.status_code}"
                logger.error(f"TMDB API error for tmdb_id={tmdb_id}: {response.status_code}")
                return result

            data = response.json()
            metadata = {}

            # Extract IMDB ID
            if "imdb_id" in data:
                metadata["imdb_id"] = data["imdb_id"]

            # Extract release year
            year_pattern = r"(19|20)\d{2}"
            if media_type == "movie":
                if "release_date" in data and data["release_date"]:
                    match = re.search(year_pattern, data["release_date"])
                    if match:
                        metadata["release_year"] = int(match.group(0))
            else:
                if "first_air_date" in data and data["first_air_date"]:
                    match = re.search(year_pattern, data["first_air_date"])
                    if match:
                        metadata["release_year"] = int(match.group(0))

            # Quantitative fields
            if "budget" in data:
                metadata["budget"] = data["budget"]
            if "revenue" in data:
                metadata["revenue"] = data["revenue"]
            if "runtime" in data:
                metadata["runtime"] = data["runtime"]

            # Country and production info
            if "origin_country" in data:
                metadata["origin_country"] = data["origin_country"]

            if "production_companies" in data:
                metadata["production_companies"] = [
                    c["name"] for c in data["production_companies"]
                ]

            if "production_countries" in data:
                metadata["production_countries"] = [
                    c["iso_3166_1"] for c in data["production_countries"]
                ]

            if "status" in data:
                metadata["production_status"] = data["status"]

            # Language info
            if "original_language" in data:
                metadata["original_language"] = data["original_language"]

            if "spoken_languages" in data:
                metadata["spoken_languages"] = [
                    lang["iso_639_1"] for lang in data["spoken_languages"]
                ]

            # Genre
            if "genres" in data:
                metadata["genre"] = [g["name"] for g in data["genres"]]

            # Title fields
            if "original_title" in data:
                metadata["original_media_title"] = data["original_title"]
            elif "original_name" in data:
                metadata["original_media_title"] = data["original_name"]

            if "title" in data:
                metadata["media_title"] = data["title"]
            elif "name" in data:
                metadata["media_title"] = data["name"]

            # Long text fields
            if "overview" in data:
                metadata["overview"] = data["overview"]
            if "tagline" in data:
                metadata["tagline"] = data["tagline"]

            # TMDB ratings
            if "vote_average" in data:
                metadata["tmdb_rating"] = data["vote_average"]
            if "vote_count" in data:
                metadata["tmdb_votes"] = data["vote_count"]

            result["success"] = True
            result["data"] = metadata
            logger.debug(f"Collected TMDB metadata for tmdb_id={tmdb_id}")

        except requests.RequestException as e:
            result["error"] = f"TMDB API request failed: {str(e)}"
            logger.error(f"TMDB API request error for tmdb_id={tmdb_id}: {e}")

        return result

    def collect_omdb_ratings(self, imdb_id: str, media_type: str) -> Dict[str, Any]:
        """
        Fetch ratings metadata from OMDB API.

        :param imdb_id: IMDB ID of the media item
        :param media_type: 'movie' or 'tv_show'/'tv_season'/'tv_episode_pack'
        :return: Dict with ratings fields
        """
        result = {"success": False, "data": {}, "error": None}

        # Determine URL and key based on media type
        if media_type == "movie":
            url = self.omdb_movie_url
            api_key = self.omdb_movie_key
        else:
            url = self.omdb_tv_url
            api_key = self.omdb_tv_key

        if not api_key:
            result["error"] = "OMDB API key not configured"
            return result

        params = {"i": imdb_id, "apikey": api_key}

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                result["error"] = f"OMDB API returned status {response.status_code}"
                logger.error(f"OMDB API error for imdb_id={imdb_id}: {response.status_code}")
                return result

            data = response.json()

            if data.get("Response") != "True":
                result["error"] = data.get("Error", "OMDB returned no results")
                return result

            metadata = {}

            # Metascore
            if data.get("Metascore") and data["Metascore"] != "N/A":
                try:
                    metadata["metascore"] = int(data["Metascore"])
                except ValueError:
                    pass

            # IMDB rating and votes
            if data.get("imdbRating") and data["imdbRating"] != "N/A":
                try:
                    metadata["imdb_rating"] = float(data["imdbRating"])
                except ValueError:
                    pass

            if data.get("imdbVotes") and data["imdbVotes"] != "N/A":
                try:
                    metadata["imdb_votes"] = int(re.sub(r"\D", "", data["imdbVotes"]))
                except ValueError:
                    pass

            # Rotten Tomatoes score (movies only)
            if media_type == "movie" and "Ratings" in data:
                for rating in data["Ratings"]:
                    if rating["Source"] == "Rotten Tomatoes":
                        try:
                            metadata["rt_score"] = int(rating["Value"].rstrip("%"))
                        except ValueError:
                            pass

            result["success"] = True
            result["data"] = metadata
            logger.debug(f"Collected OMDB ratings for imdb_id={imdb_id}")

        except requests.RequestException as e:
            result["error"] = f"OMDB API request failed: {str(e)}"
            logger.error(f"OMDB API request error for imdb_id={imdb_id}: {e}")

        return result

    def collect_all_metadata(
        self, imdb_id: str, tmdb_id: Optional[int], media_type: str
    ) -> Dict[str, Any]:
        """
        Collect metadata from both TMDB and OMDB APIs.

        :param imdb_id: IMDB ID of the media item
        :param tmdb_id: TMDB ID of the media item (optional)
        :param media_type: 'movie' or 'tv_show'/'tv_season'/'tv_episode_pack'
        :return: Combined metadata dict with success status
        """
        result = {
            "success": False,
            "data": {},
            "tmdb_success": False,
            "omdb_success": False,
            "errors": [],
        }

        combined_metadata = {}

        # Collect TMDB details if tmdb_id is available
        if tmdb_id:
            tmdb_result = self.collect_tmdb_details(tmdb_id, media_type)
            result["tmdb_success"] = tmdb_result["success"]
            if tmdb_result["success"]:
                combined_metadata.update(tmdb_result["data"])
            elif tmdb_result["error"]:
                result["errors"].append(f"TMDB: {tmdb_result['error']}")

        # Collect OMDB ratings
        omdb_result = self.collect_omdb_ratings(imdb_id, media_type)
        result["omdb_success"] = omdb_result["success"]
        if omdb_result["success"]:
            combined_metadata.update(omdb_result["data"])
        elif omdb_result["error"]:
            result["errors"].append(f"OMDB: {omdb_result['error']}")

        # Success if at least one API call succeeded
        result["success"] = result["tmdb_success"] or result["omdb_success"]
        result["data"] = combined_metadata

        return result
