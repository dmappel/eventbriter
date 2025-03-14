"""Event models for the Eventbrite scraper."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class Coordinates(BaseModel):
    """Model for geographic coordinates."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Location(BaseModel):
    """Model for event location details."""
    venue: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    coordinates: Optional[Coordinates] = None


class Organizer(BaseModel):
    """Model for event organizer details."""
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class Price(BaseModel):
    """Model for event price details."""
    currency: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    is_free: bool = False


class Event(BaseModel):
    """Model for event details."""
    id: str
    title: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[Location] = None
    organizer: Optional[Organizer] = None
    price: Optional[Price] = None
    url: str
    image_url: Optional[str] = None
    categories: List[str] = []
    tags: List[str] = []


class SimpleEvent(BaseModel):
    """Simplified model for event details with only id, title, and url."""
    id: str
    title: str
    url: str 