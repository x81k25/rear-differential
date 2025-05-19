# app/models/api.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
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
    imdb_id: str
    tmdb_id: Optional[int] = None
    label: LabelType
    media_type: MediaType
    media_title: str
    season: Optional[int] = None
    episode: Optional[int] = None
    release_year: int
    genre: Optional[List[str]] = None
    language: Optional[List[str]] = None
    rt_score: Optional[int] = None
    metascore: Optional[int] = None
    imdb_rating: Optional[float] = None
    imdb_votes: Optional[int] = None
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