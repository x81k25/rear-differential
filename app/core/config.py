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
    REAR_DIFF_DB_PATH_PREFIX: str = Field(default="/d/media-cache/dev/transfer", description="Database path prefix to replace")
    REAR_DIFF_LIBRARY_MOUNT_PATH: str = Field(default="/library", description="Container mount path for library")

    # Directory paths (optional, used for reference)
    REAR_DIFF_DOWNLOAD_DIR: str = Field(default="", description="Download directory path")
    REAR_DIFF_MOVIE_DIR: str = Field(default="", description="Movie directory path")
    REAR_DIFF_TV_SHOW_DIR: str = Field(default="", description="TV show directory path")

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()