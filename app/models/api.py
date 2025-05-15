# app/models/api.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

class MediaResponseModel(BaseModel):
    """Model for media response."""
    hash: str
    media_type: str
    media_title: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    release_year: Optional[int] = None
    pipeline_status: str
    error_status: bool = False
    error_condition: Optional[str] = None
    rejection_status: str
    rejection_reason: Optional[str] = None
    parent_path: Optional[str] = None
    target_path: Optional[str] = None
    original_title: str
    original_path: Optional[str] = None
    original_link: Optional[str] = None
    rss_source: Optional[str] = None
    uploader: Optional[str] = None
    genre: Optional[List[str]] = None
    language: Optional[List[str]] = None
    rt_score: Optional[int] = None
    metascore: Optional[int] = None
    imdb_rating: Optional[float] = None
    imdb_votes: Optional[int] = None
    imdb_id: Optional[str] = None
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    upload_type: Optional[str] = None
    audio_codec: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tmdb_id: Optional[int] = None

    @validator('hash')
    def validate_hash(cls, v):
        if not re.match(r'^[a-f0-9]+$', v) or len(v) != 40:
            raise ValueError('Hash must be a 40-character hexadecimal string')
        return v

    @validator('imdb_id')
    def validate_imdb_id(cls, v):
        if v is not None and not re.match(r'^tt[0-9]{7,8}$', v):
            raise ValueError('IMDB ID must match format tt followed by 7-8 digits')
        return v

    @validator('release_year')
    def validate_release_year(cls, v):
        if v is not None and (v < 1850 or v > 2100):
            raise ValueError('Release year must be between 1850 and 2100')
        return v

class MediaListResponse(BaseModel):
    """Response model for the media listing endpoint."""
    data: List[MediaResponseModel]
    pagination: Dict[str, Any]

class RejectionStatusUpdateRequest(BaseModel):
    """Request model for updating rejection status."""
    hash: str
    rejection_status: str

    @validator('rejection_status')
    def validate_rejection_status(cls, v):
        valid_statuses = ["unfiltered", "accepted", "rejected", "override"]
        if v not in valid_statuses:
            raise ValueError(f"Rejection status must be one of: {', '.join(valid_statuses)}")
        return v

    @validator('hash')
    def validate_hash(cls, v):
        if not re.match(r'^[a-f0-9]+$', v) or len(v) != 40:
            raise ValueError('Hash must be a 40-character hexadecimal string')
        return v

class RejectionStatusUpdateResponse(BaseModel):
    """Response model for updating rejection status."""
    success: bool
    message: str
    error: Optional[str] = None