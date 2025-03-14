"""Search models for the Eventbrite scraper."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, validator

from app.models.event import Event


class DateRange(BaseModel):
    """Model for date range filter."""
    start: Optional[str] = None
    end: Optional[str] = None


class PriceRange(BaseModel):
    """Model for price range filter."""
    min: Optional[float] = None
    max: Optional[float] = None
    free_only: bool = False


class SearchRequest(BaseModel):
    """Model for search request parameters."""
    locations: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    date_range: Optional[DateRange] = None
    price_range: Optional[PriceRange] = None
    page: int = 1
    page_size: int = 20
    limit: Optional[int] = None

    @validator('page')
    def page_must_be_positive(cls, v):
        if v < 1:
            raise ValueError('page must be greater than 0')
        return v

    @validator('page_size')
    def page_size_must_be_valid(cls, v):
        if v < 1 or v > 100:
            raise ValueError('page_size must be between 1 and 100')
        return v

    @validator('limit')
    def limit_must_be_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError('limit must be greater than 0')
        return v


class SearchResponse(BaseModel):
    """Model for search response."""
    events: List[Event]
    total_count: int
    page: int
    page_size: int
    search_time_ms: int 