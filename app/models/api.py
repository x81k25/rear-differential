# app/models/api.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal
import re
from enum import Enum

class MediaType(str, Enum):
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    TV_SEASON = "tv_season"

class LabelType(str, Enum):
    WOULD_WATCH = "would_watch"
    WOULD_NOT_WATCH = "would_not_watch"

class TrainingResponseModel(BaseModel):
    """Model for training data response."""
    # Identifier columns
    imdb_id: str
    tmdb_id: Optional[int] = None

    # Label columns
    label: LabelType

    # Media identifying information
    media_type: MediaType
    media_title: str
    season: Optional[int] = None
    episode: Optional[int] = None
    release_year: int

    # Metadata pertaining to the media item
    # - quantitative details
    budget: Optional[int] = None
    revenue: Optional[int] = None
    runtime: Optional[int] = None

    # - country and production information
    origin_country: Optional[List[str]] = None
    production_companies: Optional[List[str]] = None
    production_countries: Optional[List[str]] = None
    production_status: Optional[str] = None

    # - language information
    original_language: Optional[str] = None
    spoken_languages: Optional[List[str]] = None

    # - other string fields
    genre: Optional[List[str]] = None
    original_media_title: Optional[str] = None

    # - long string fields
    tagline: Optional[str] = None
    overview: Optional[str] = None

    # - ratings info
    tmdb_rating: Optional[Decimal] = None
    tmdb_votes: Optional[int] = None
    rt_score: Optional[int] = None
    metascore: Optional[int] = None
    imdb_rating: Optional[Decimal] = None
    imdb_votes: Optional[int] = None

    # Flag columns
    human_labeled: Optional[bool] = None
    anomalous: Optional[bool] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    @validator('imdb_id')
    def validate_imdb_id(cls, v):
        if not re.match(r'^tt[0-9]{7,8}$', v):
            raise ValueError('IMDB ID must match format tt followed by 7-8 digits')
        return v

    @validator('tmdb_id')
    def validate_tmdb_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('TMDB ID must be greater than 0')
        return v

    @validator('release_year')
    def validate_release_year(cls, v):
        if v < 1850 or v > 2100:
            raise ValueError('Release year must be between 1850 and 2100')
        return v

    @validator('budget')
    def validate_budget(cls, v):
        if v is not None and v < 0:
            raise ValueError('Budget must be greater than or equal to 0')
        return v

    @validator('revenue')
    def validate_revenue(cls, v):
        if v is not None and v < 0:
            raise ValueError('Revenue must be greater than or equal to 0')
        return v

    @validator('runtime')
    def validate_runtime(cls, v):
        if v is not None and v < 0:
            raise ValueError('Runtime must be greater than or equal to 0')
        return v

    @validator('origin_country', 'production_countries')
    def validate_country_codes(cls, v):
        if v is not None:
            for code in v:
                if len(code) != 2:
                    raise ValueError('Country codes must be exactly 2 characters')
        return v

    @validator('original_language')
    def validate_original_language(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError('Original language must be exactly 2 characters')
        return v

    @validator('spoken_languages')
    def validate_spoken_languages(cls, v):
        if v is not None:
            for lang in v:
                if len(lang) != 2:
                    raise ValueError('Spoken language codes must be exactly 2 characters')
        return v

    @validator('tmdb_rating')
    def validate_tmdb_rating(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('TMDB rating must be between 0 and 10')
        return v

    @validator('tmdb_votes')
    def validate_tmdb_votes(cls, v):
        if v is not None and v < 0:
            raise ValueError('TMDB votes must be greater than or equal to 0')
        return v

    @validator('rt_score')
    def validate_rt_score(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('RT score must be between 0 and 100')
        return v

    @validator('metascore')
    def validate_metascore(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Metascore must be between 0 and 100')
        return v

    @validator('imdb_rating')
    def validate_imdb_rating(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('IMDB rating must be between 0 and 100')
        return v

    @validator('imdb_votes')
    def validate_imdb_votes(cls, v):
        if v is not None and v < 0:
            raise ValueError('IMDB votes must be greater than or equal to 0')
        return v

class TrainingListResponse(BaseModel):
    """Response model for the training data listing endpoint."""
    data: List[TrainingResponseModel]
    pagination: Dict[str, Any]

class LabelUpdateRequest(BaseModel):
    """Request model for updating label."""
    imdb_id: str
    label: LabelType

    @validator('imdb_id')
    def validate_imdb_id(cls, v):
        if not re.match(r'^tt[0-9]{7,8}$', v):
            raise ValueError('IMDB ID must match format tt followed by 7-8 digits')
        return v

class LabelUpdateResponse(BaseModel):
    """Response model for updating label."""
    success: bool
    message: str
    error: Optional[str] = None