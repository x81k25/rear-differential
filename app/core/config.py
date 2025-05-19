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
    PGSQL_HOST: str = Field(default="localhost", description="Database host")
    PGSQL_PORT: int = Field(default=5432, description="Database port")
    PGSQL_USER: str = Field(default="postgres", description="Database user")
    PGSQL_PASSWORD: str = Field(description="Database password")
    PGSQL_NAME: str = Field(default="postgres", description="Database name")

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()