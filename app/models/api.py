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
    UNKNOWN = "unknown"

class LabelType(str, Enum):
    WOULD_WATCH = "would_watch"
    WOULD_NOT_WATCH = "would_not_watch"

class PipelineStatus(str, Enum):
    INGESTED = "ingested"
    PAUSED = "paused"
    PARSED = "parsed"
    REJECTED = "rejected"
    FILE_ACCEPTED = "file_accepted"
    METADATA_COLLECTED = "metadata_collected"
    MEDIA_ACCEPTED = "media_accepted"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    TRANSFERRED = "transferred"
    COMPLETE = "complete"

class RejectionStatus(str, Enum):
    UNFILTERED = "unfiltered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    OVERRIDE = "override"

class RssSource(str, Enum):
    YTS_MX = "yts.mx"
    EPISODEFEED_COM = "episodefeed.com"

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
    reviewed: Optional[bool] = None

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

class ReviewedUpdateRequest(BaseModel):
    """Request model for updating reviewed status."""
    imdb_id: str

    @validator('imdb_id')
    def validate_imdb_id(cls, v):
        if not re.match(r'^tt[0-9]{7,8}$', v):
            raise ValueError('IMDB ID must match format tt followed by 7-8 digits')
        return v

class ReviewedUpdateResponse(BaseModel):
    """Response model for updating reviewed status."""
    success: bool
    message: str
    error: Optional[str] = None

class MediaResponseModel(BaseModel):
    """Model for media data response."""
    # Primary key
    hash: str
    
    # Media identifying information
    media_type: MediaType
    media_title: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    release_year: Optional[int] = None
    
    # Status fields
    pipeline_status: PipelineStatus
    error_status: bool
    error_condition: Optional[str] = None
    rejection_status: RejectionStatus
    rejection_reason: Optional[str] = None
    
    # Path information
    parent_path: Optional[str] = None
    target_path: Optional[str] = None
    original_title: str
    original_path: Optional[str] = None
    original_link: Optional[str] = None
    
    # Source information
    rss_source: Optional[RssSource] = None
    uploader: Optional[str] = None
    
    # External IDs
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    
    # Financial data
    budget: Optional[int] = None
    revenue: Optional[int] = None
    runtime: Optional[int] = None
    
    # Country and production information
    origin_country: Optional[List[str]] = None
    production_companies: Optional[List[str]] = None
    production_countries: Optional[List[str]] = None
    production_status: Optional[str] = None
    
    # Language information
    original_language: Optional[str] = None
    spoken_languages: Optional[List[str]] = None
    
    # Content information
    genre: Optional[List[str]] = None
    original_media_title: Optional[str] = None
    tagline: Optional[str] = None
    overview: Optional[str] = None
    
    # Ratings
    tmdb_rating: Optional[Decimal] = None
    tmdb_votes: Optional[int] = None
    rt_score: Optional[int] = None
    metascore: Optional[int] = None
    imdb_rating: Optional[Decimal] = None
    imdb_votes: Optional[int] = None
    
    # Technical information
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    upload_type: Optional[str] = None
    audio_codec: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    @validator('hash')
    def validate_hash(cls, v):
        if not re.match(r'^[a-f0-9]{40}$', v):
            raise ValueError('Hash must be exactly 40 hex characters')
        return v

    @validator('imdb_id')
    def validate_imdb_id(cls, v):
        if v is not None and not re.match(r'^tt[0-9]{7,8}$', v):
            raise ValueError('IMDB ID must match format tt followed by 7-8 digits')
        return v

    @validator('tmdb_id')
    def validate_tmdb_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('TMDB ID must be greater than 0')
        return v

    @validator('release_year')
    def validate_release_year(cls, v):
        if v is not None and (v < 1850 or v > 2100):
            raise ValueError('Release year must be between 1850 and 2100')
        return v

    @validator('budget', 'revenue')
    def validate_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Value must be non-negative')
        return v

    @validator('runtime')
    def validate_runtime(cls, v):
        if v is not None and v < 0:
            raise ValueError('Runtime must be non-negative')
        return v

    @validator('tmdb_rating')
    def validate_tmdb_rating(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('TMDB rating must be between 0 and 10')
        return v

    @validator('rt_score', 'metascore')
    def validate_percentage_scores(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Score must be between 0 and 100')
        return v

    @validator('imdb_rating')
    def validate_imdb_rating(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('IMDB rating must be between 0 and 100')
        return v

    @validator('tmdb_votes', 'imdb_votes')
    def validate_votes(cls, v):
        if v is not None and v < 0:
            raise ValueError('Votes must be non-negative')
        return v

class MediaListResponse(BaseModel):
    """Response model for the media listing endpoint."""
    data: List[MediaResponseModel]
    pagination: Dict[str, Any]

class FlywayHistoryModel(BaseModel):
    """Model for flyway schema history response."""
    installed_rank: int
    version: Optional[str] = None
    description: str
    type: str
    script: str
    checksum: Optional[int] = None
    installed_by: str
    installed_on: datetime
    execution_time: int
    success: bool

class FlywayHistoryResponse(BaseModel):
    """Response model for flyway schema history."""
    data: List[FlywayHistoryModel]