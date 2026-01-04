# app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="Host to bind the API server")
    API_PORT: int = Field(default=8000, description="Port to run the API server")

   # Database Configuration
    REAR_DIFF_PGSQL_HOST: str = Field(default="localhost", description="Database host")
    REAR_DIFF_PGSQL_PORT: str = Field(default="5432", description="Database port")
    REAR_DIFF_PGSQL_USERNAME: str = Field(default="postgres", description="Database user")
    REAR_DIFF_PGSQL_PASSWORD: str = Field(description="Database password")
    REAR_DIFF_PGSQL_DATABASE: str = Field(default="postgres", description="Database name")

    # Transmission RPC Configuration
    REAR_DIFF_TRANSMISSION_HOST: str = Field(default="localhost", description="Transmission RPC host")
    REAR_DIFF_TRANSMISSION_PORT: int = Field(default=9091, description="Transmission RPC port")
    REAR_DIFF_TRANSMISSION_USERNAME: str = Field(default="", description="Transmission RPC username")
    REAR_DIFF_TRANSMISSION_PASSWORD: str = Field(default="", description="Transmission RPC password")

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # File Deletion Configuration
    REAR_DIFF_FILE_DELETION_ENABLED: bool = Field(default=False, description="Enable file deletion on would_not_watch label")
    REAR_DIFF_MEDIA_CACHE_PATH: str = Field(default="", description="Media cache base path with incomplete/ and complete/ subdirs")
    REAR_DIFF_MEDIA_LIBRARY_PATH_MOVIES: str = Field(default="", description="Media library path for movies")
    REAR_DIFF_MEDIA_LIBRARY_PATH_TV: str = Field(default="", description="Media library path for TV shows")

    # TMDB API Configuration (Movie)
    REAR_DIFF_MOVIE_SEARCH_API_BASE_URL: str = Field(default="https://api.themoviedb.org/3/search/movie", description="TMDB movie search API URL")
    REAR_DIFF_MOVIE_DETAILS_API_BASE_URL: str = Field(default="https://api.themoviedb.org/3/movie", description="TMDB movie details API URL")
    REAR_DIFF_MOVIE_SEARCH_API_KEY: str = Field(default="", description="TMDB movie search API key")
    REAR_DIFF_MOVIE_DETAILS_API_KEY: str = Field(default="", description="TMDB movie details API key")

    # TMDB API Configuration (TV)
    REAR_DIFF_TV_SEARCH_API_BASE_URL: str = Field(default="https://api.themoviedb.org/3/search/tv", description="TMDB TV search API URL")
    REAR_DIFF_TV_DETAILS_API_BASE_URL: str = Field(default="https://api.themoviedb.org/3/tv", description="TMDB TV details API URL")
    REAR_DIFF_TV_SEARCH_API_KEY: str = Field(default="", description="TMDB TV search API key")
    REAR_DIFF_TV_DETAILS_API_KEY: str = Field(default="", description="TMDB TV details API key")

    # OMDB API Configuration (Ratings)
    REAR_DIFF_MOVIE_RATINGS_API_BASE_URL: str = Field(default="http://www.omdbapi.com/", description="OMDB movie ratings API URL")
    REAR_DIFF_MOVIE_RATINGS_API_KEY: str = Field(default="", description="OMDB movie ratings API key")
    REAR_DIFF_TV_RATINGS_API_BASE_URL: str = Field(default="http://www.omdbapi.com/", description="OMDB TV ratings API URL")
    REAR_DIFF_TV_RATINGS_API_KEY: str = Field(default="", description="OMDB TV ratings API key")

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()