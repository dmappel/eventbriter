import time
import json
import io
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Path, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
import pandas as pd

from app.config import logger
from app.models.event import Event, SimpleEvent
from app.models.search import SearchRequest, SearchResponse, ExportFormat, ExportRequest, ErrorResponse
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


@router.get("/events/search", response_model=List[SimpleEvent])
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
    Search for events with filters.
    """
    try:
        # Create search request from query parameters
        search_request = SearchRequest(
            locations=locations,
            keywords=keywords,
            date_range={
                "start": start_date,
                "end": end_date
            } if start_date or end_date else None,
            page=page,
            page_size=page_size,
            limit=limit
        )
        
        # Search for events
        result = scraper.search_events(search_request)
        
        # Convert to SimpleEvent objects
        simple_events = [SimpleEvent(id=event.id, title=event.title, url=event.url) for event in result["events"]]
        
        return simple_events
    
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
    Get detailed information about a specific event.
    """
    try:
        event = scraper.get_event_details(event_id)
        
        if not event:
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        
        # Convert to SimpleEvent
        simple_event = SimpleEvent(id=event.id, title=event.title, url=event.url)
        
        return simple_event
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error in get_event: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving event details: {str(e)}"
        )


@router.post("/events/export")
async def export_events(
    export_request: ExportRequest,
    scraper: EventbriteScraper = Depends(get_scraper)
) -> Response:
    """
    Export event data in various formats.
    """
    try:
        # Search for events
        result = scraper.search_events(export_request.search_params)
        events = result["events"]
        
        # Convert to SimpleEvent objects
        simple_events = [SimpleEvent(id=event.id, title=event.title, url=event.url) for event in events]
        
        if export_request.format == ExportFormat.JSON:
            # Convert events to JSON
            events_json = json.dumps([event.dict() for event in simple_events], default=str, indent=2)
            
            # Create response with JSON file
            return StreamingResponse(
                io.StringIO(events_json),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=events.json"
                }
            )
        
        elif export_request.format == ExportFormat.CSV:
            # Convert events to DataFrame
            events_data = [event.dict() for event in simple_events]
            
            # Create DataFrame
            df = pd.DataFrame(events_data)
            
            # Convert to CSV
            csv_data = df.to_csv(index=False)
            
            # Create response with CSV file
            return StreamingResponse(
                io.StringIO(csv_data),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=events.csv"
                }
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {export_request.format}"
            )
    
    except Exception as e:
        logger.error(f"Error in export_events: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while exporting events: {str(e)}"
        )
