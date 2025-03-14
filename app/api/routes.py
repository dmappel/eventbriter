import time
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Query, Path, HTTPException, Depends

from app.config import logger
from app.models.event import Event, SimpleEvent
from app.models.search import SearchRequest, DateRange
from app.scraper.scraper import EventbriteScraper

# Create router
router = APIRouter()

# Create a scraper instance
scraper = None

def get_scraper() -> EventbriteScraper:
    """
    Get or create a scraper instance.
    
    Returns:
        EventbriteScraper instance
    """
    global scraper
    if scraper is None:
        scraper = EventbriteScraper(use_selenium=True)
    return scraper


@router.get("/events/search", response_model=Dict[str, Any])
async def search_events(
    locations: Optional[List[str]] = Query(None, description="List of locations to search in"),
    keywords: Optional[List[str]] = Query(None, description="List of keywords to search for"),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results to return"),
    scraper: EventbriteScraper = Depends(get_scraper)
) -> Dict[str, Any]:
    """
    Search for events with filters and return structured data with only id, title, and url.
    """
    try:
        # Create date range if dates are provided
        date_range = None
        if start_date or end_date:
            date_range = DateRange(start=start_date, end=end_date)
        
        # Create search request from query parameters
        search_request = SearchRequest(
            locations=locations,
            keywords=keywords,
            date_range=date_range,
            page=page,
            page_size=page_size,
            limit=limit
        )
        
        # Search for events
        result = scraper.search_events(search_request)
        
        # Simplify the response to include only id, title, and url
        simplified_events = []
        for event in result["events"]:
            simplified_events.append({
                "id": event.id,
                "title": event.title,
                "url": event.url
            })
        
        # Return simplified response
        return {
            "events": simplified_events,
            "total_count": result["total_count"],
            "page": result["page"],
            "page_size": result["page_size"],
            "search_time_ms": result["search_time_ms"]
        }
    
    except Exception as e:
        logger.error(f"Error in search_events: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while searching for events: {str(e)}"
        )


@router.get("/events/{event_id}", response_model=SimpleEvent)
async def get_event(
    event_id: str = Path(..., description="Event ID"),
    scraper: EventbriteScraper = Depends(get_scraper)
) -> SimpleEvent:
    """
    Get simplified information about a specific event (id, title, url only).
    """
    try:
        event = scraper.get_event_details(event_id)
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        
        # Return only the simplified event data
        return SimpleEvent(
            id=event.id,
            title=event.title,
            url=event.url
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error in get_event: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving event details: {str(e)}"
        )
