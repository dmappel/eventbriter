import time
import random
import requests
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import os
import logging
from urllib.parse import urljoin, urlparse, parse_qs

from app.config import (
    REQUEST_DELAY, 
    MAX_RETRIES, 
    USER_AGENT_ROTATION, 
    USER_AGENTS, 
    EVENTBRITE_BASE_URL,
    EVENTBRITE_SEARCH_URL,
    EVENTBRITE_EVENT_URL,
    logger
)
from app.models.event import Event, Location, Organizer, Price, Coordinates
from app.models.search import SearchRequest
from app.scraper.parser import EventParser


class EventbriteScraper:
    """
    Scraper for extracting event data from Eventbrite.
    """
    
    def __init__(self, use_selenium: bool = True):
        """
        Initialize the scraper.
        
        Args:
            use_selenium: Whether to use Selenium for scraping (required for JavaScript-rendered content)
        """
        self.session = requests.Session()
        self.use_selenium = use_selenium
        self.driver = None
        self.parser = EventParser()
        self._last_content = None  # Store the last HTML content for debugging
        self.logger = logger
        
        if use_selenium:
            self._setup_selenium()
    
    def _setup_selenium(self):
        """Set up Selenium WebDriver."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Add random user agent
            if USER_AGENT_ROTATION:
                user_agent = random.choice(USER_AGENTS)
                logger.debug(f"Using user agent: {user_agent}")
                chrome_options.add_argument(f"--user-agent={user_agent}")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for the request."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Rotate user agents if enabled
        if USER_AGENT_ROTATION:
            headers["User-Agent"] = random.choice(USER_AGENTS)
        else:
            headers["User-Agent"] = USER_AGENTS[0]

        return headers

    def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], int]:
        """
        Make a request to the given URL with retries.
        
        Args:
            url: URL to request
            params: Optional query parameters
            
        Returns:
            Tuple of (HTML content, status code)
        """
        self.logger.info(f"Making request to {url} with params: {params}")
        
        for attempt in range(MAX_RETRIES):
            try:
                # Add delay between requests to avoid being blocked
                if attempt > 0:
                    delay = REQUEST_DELAY * (1 + attempt)
                    self.logger.info(f"Retry attempt {attempt+1}/{MAX_RETRIES}. Waiting {delay:.2f} seconds...")
                    time.sleep(delay)
                
                headers = self._get_headers()
                self.logger.debug(f"Request headers: {headers}")
                
                response = self.session.get(
                    url, 
                    headers=headers, 
                    params=params,
                    timeout=30
                )
                
                status_code = response.status_code
                self.logger.info(f"Response status code: {status_code}")
                
                # Save response headers for debugging
                self.logger.debug(f"Response headers: {dict(response.headers)}")
                
                if status_code == 200:
                    content_length = len(response.text)
                    self.logger.info(f"Received response with content length: {content_length} bytes")
                    
                    # Save a sample of the response for debugging
                    sample_size = min(500, content_length)
                    self.logger.debug(f"Response sample: {response.text[:sample_size]}...")
                    
                    return response.text, status_code
                
                # Handle specific status codes
                if status_code == 403:
                    self.logger.warning("Received 403 Forbidden - possible rate limiting or IP blocking")
                elif status_code == 404:
                    self.logger.warning("Received 404 Not Found - URL may be invalid")
                elif status_code == 429:
                    self.logger.warning("Received 429 Too Many Requests - rate limited")
                    # Add longer delay for rate limiting
                    time.sleep(REQUEST_DELAY * 5)
                elif status_code >= 500:
                    self.logger.warning(f"Received server error {status_code} - server may be having issues")
                
                self.logger.error(f"Request failed with status code: {status_code}")
                
            except requests.RequestException as e:
                self.logger.error(f"Request exception on attempt {attempt+1}/{MAX_RETRIES}: {str(e)}")
            
            # If we get here, the request failed
            if attempt < MAX_RETRIES - 1:
                self.logger.info(f"Retrying request to {url}...")
            else:
                self.logger.error(f"All {MAX_RETRIES} attempts failed for URL: {url}")
        
        return None, 0
    
    def _get_with_retry(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Make a GET request with retry logic.
        
        Args:
            url: URL to request
            params: Query parameters
            
        Returns:
            Response text if successful, None otherwise
        """
        logger.debug(f"Making GET request to {url} with params {params}")
        for attempt in range(MAX_RETRIES):
            try:
                # Add delay to avoid rate limiting
                if attempt > 0:
                    time.sleep(REQUEST_DELAY * (attempt + 1))
                else:
                    time.sleep(REQUEST_DELAY)
                
                # Rotate user agent if enabled
                if USER_AGENT_ROTATION:
                    headers = {"User-Agent": random.choice(USER_AGENTS)}
                    logger.debug(f"Using user agent: {headers['User-Agent']}")
                    response = self.session.get(url, params=params, headers=headers, timeout=30)
                else:
                    response = self.session.get(url, params=params, timeout=30)
                
                response.raise_for_status()
                self._last_content = response.text  # Store content for debugging
                logger.debug(f"Request successful, received {len(response.text)} bytes")
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"All retry attempts failed for URL: {url}")
                    return None
    
    def _get_with_selenium(self, url: str) -> Optional[str]:
        """
        Load a page using Selenium and return the page source.
        
        Args:
            url: URL to load
            
        Returns:
            Page source if successful, None otherwise
        """
        logger.debug(f"Loading URL with Selenium: {url}")
        if not self.driver:
            self._setup_selenium()
            
        try:
            self.driver.get(url)
            # Wait for JavaScript to load content
            logger.debug("Waiting for page to load...")
            time.sleep(5)
            
            # Save screenshot for debugging
            try:
                self.driver.save_screenshot("eventbrite_screenshot.png")
                logger.debug("Screenshot saved to eventbrite_screenshot.png")
            except Exception as e:
                logger.warning(f"Failed to save screenshot: {e}")
            
            content = self.driver.page_source
            self._last_content = content  # Store content for debugging
            logger.debug(f"Page loaded successfully, received {len(content)} bytes")
            
            # Save HTML for debugging
            with open("eventbrite_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            logger.debug("HTML content saved to eventbrite_page.html")
            
            return content
        except Exception as e:
            logger.error(f"Selenium request failed: {e}")
            return None
    
    def build_search_url(self, search_params: SearchRequest) -> str:
        """
        Build search URL from search parameters.
        
        Args:
            search_params: Search request parameters
            
        Returns:
            Formatted search URL
        """
        # Start with base search URL
        url = EVENTBRITE_SEARCH_URL
        
        # Add location if provided
        country = "spain"  # Default country
        city = "barcelona"  # Default city
        
        if search_params.locations and len(search_params.locations) > 0:
            location = search_params.locations[0]  # Use first location
            # Check if location contains country info
            if "--" in location:
                parts = location.split("--")
                if len(parts) == 2:
                    country, city = parts
            else:
                city = location
            
            url += f"/{country}--{city}"
        else:
            url += f"/{country}--{city}"
        
        # Always add keywords to the path (not as query parameter)
        if search_params.keywords and len(search_params.keywords) > 0:
            keyword = search_params.keywords[0]
            # Use the keyword as-is in the URL path
            url += f"/{keyword}"
        
        # Start query parameters
        query_params = {}
        
        # Add date range if provided
        if search_params.date_range:
            if search_params.date_range.start:
                query_params["start_date"] = search_params.date_range.start
            if search_params.date_range.end:
                query_params["end_date"] = search_params.date_range.end
        
        # Add page number
        if search_params.page > 1:
            query_params["page"] = str(search_params.page)
        
        # Build query string
        if query_params:
            query_string = urllib.parse.urlencode(query_params)
            url += f"/?{query_string}"
        else:
            url += "/"
        
        logger.debug(f"Built search URL: {url}")
        return url
    
    def search_events_by_location(
        self, 
        location: str, 
        date: Optional[str] = None, 
        category: Optional[str] = None,
        page: int = 1
    ) -> List[Event]:
        """
        Search for events on Eventbrite by location.
        
        Args:
            location: Location to search in
            date: Date filter (optional)
            category: Category filter (optional)
            page: Page number (default: 1)
            
        Returns:
            List of Event objects
        """
        self.logger.info(f"Searching events with location={location}, date={date}, category={category}, page={page}")
        
        # Build search parameters
        params = {"page": page}
        
        # Add location to URL path
        url = f"{EVENTBRITE_SEARCH_URL}/{location}/"
        
        # Add date filter if provided
        if date:
            params["date"] = date
        
        # Add category filter if provided
        if category:
            params["category"] = category
        
        self.logger.debug(f"Search URL: {url}, params: {params}")
        
        # Make request
        html_content = self._get_with_retry(url, params)
        
        if not html_content:
            self.logger.error("Failed to get search results")
            return []
        
        # Save HTML content for debugging if needed
        if os.getenv("SAVE_HTML", "False").lower() in ("true", "1", "t"):
            with open("eventbrite_search_results.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info("Saved search results HTML to eventbrite_search_results.html")
        
        # Parse events
        try:
            events = self.parser.parse_search_results(html_content)
            self.logger.info(f"Found {len(events)} events")
            return events
        except Exception as e:
            self.logger.exception(f"Error parsing search results: {str(e)}")
            # Save HTML content for debugging when parsing fails
            with open("eventbrite_failed_parse.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info("Saved failed parse HTML to eventbrite_failed_parse.html")
            return []

    def search_events(self, search_request: SearchRequest) -> Dict[str, Any]:
        """
        Search for events using the SearchRequest model.
        
        Args:
            search_request: Search request parameters
            
        Returns:
            Dictionary with events, total count, page, page size, and search time
        """
        start_time = time.time()
        self.logger.info(f"Searching events with request: {search_request}")
        
        # Build search URL
        url = self.build_search_url(search_request)
        
        # Make request
        html_content = self._get_with_retry(url)
        
        if not html_content:
            self.logger.error("Failed to get search results")
            return {
                "events": [],
                "total_count": 0,
                "page": search_request.page,
                "page_size": search_request.page_size,
                "search_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # Save HTML content for debugging if needed
        if os.getenv("SAVE_HTML", "False").lower() in ("true", "1", "t"):
            with open("eventbrite_search_results.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info("Saved search results HTML to eventbrite_search_results.html")
        
        # Parse events
        try:
            events = self.parser.parse_search_results(html_content, search_request.page_size)
            
            # Deduplicate events by ID
            unique_events = {}
            for event in events:
                if event.id not in unique_events:
                    unique_events[event.id] = event
            
            events = list(unique_events.values())
            self.logger.info(f"Deduplicated events from {len(events)} to {len(unique_events)}")
            
            # Filter events by keywords if provided
            if search_request.keywords and len(search_request.keywords) > 0:
                filtered_events = []
                for event in events:
                    # Check if any keyword is in the title or description (case-insensitive)
                    if self._matches_keywords(event, search_request.keywords):
                        filtered_events.append(event)
                
                self.logger.info(f"Found {len(events)} events, filtered to {len(filtered_events)} events matching keywords")
                events = filtered_events
            else:
                self.logger.info(f"Found {len(events)} events")
            
            # Apply limit if provided
            if search_request.limit is not None and len(events) > search_request.limit:
                self.logger.info(f"Limiting results from {len(events)} to {search_request.limit} events")
                events = events[:search_request.limit]
            
            search_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "events": events,
                "total_count": len(events),  # This is an estimate since we don't have the actual total
                "page": search_request.page,
                "page_size": search_request.page_size,
                "search_time_ms": search_time_ms
            }
        except Exception as e:
            self.logger.exception(f"Error parsing search results: {str(e)}")
            # Save HTML content for debugging when parsing fails
            with open("eventbrite_failed_parse.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info("Saved failed parse HTML to eventbrite_failed_parse.html")
            
            return {
                "events": [],
                "total_count": 0,
                "page": search_request.page,
                "page_size": search_request.page_size,
                "search_time_ms": int((time.time() - start_time) * 1000)
            }
    
    def _matches_keywords(self, event: Event, keywords: List[str]) -> bool:
        """
        Check if an event matches any of the provided keywords.
        
        Args:
            event: Event to check
            keywords: List of keywords to match against
            
        Returns:
            True if the event matches any keyword, False otherwise
        """
        if not keywords:
            return True
        
        # Convert event title and description to lowercase for case-insensitive matching
        title = event.title.lower() if event.title else ""
        description = event.description.lower() if event.description else ""
        
        # Get categories and tags as lowercase strings
        categories = [cat.lower() for cat in event.categories] if event.categories else []
        tags = [tag.lower() for tag in event.tags] if event.tags else []
        
        # URL might contain additional information
        url = event.url.lower() if event.url else ""
        
        # Special handling for 'ai' keyword to avoid false positives
        if 'ai' in keywords and len(keywords) == 1:
            # List of common AI-related terms
            ai_terms = [
                'artificial intelligence', 
                'machine learning', 
                'deep learning', 
                'neural network',
                'data science',
                'chatgpt',
                'llm',
                'large language model',
                'generative ai',
                'computer vision',
                'nlp',
                'natural language processing'
            ]
            
            # Check for whole word 'ai' with word boundaries
            ai_whole_word = False
            
            # Check in title
            title_words = title.split()
            for word in title_words:
                if word == 'ai' or word == 'a.i.' or word == 'a.i':
                    ai_whole_word = True
                    self.logger.debug(f"Event {event.id} matches 'ai' as whole word in title")
                    break
            
            # Check in description if not found in title
            if not ai_whole_word and description:
                description_words = description.split()
                for word in description_words:
                    if word == 'ai' or word == 'a.i.' or word == 'a.i':
                        ai_whole_word = True
                        self.logger.debug(f"Event {event.id} matches 'ai' as whole word in description")
                        break
            
            # Check for AI-related terms
            ai_term_found = False
            for term in ai_terms:
                if term in title or term in description or term in url:
                    ai_term_found = True
                    self.logger.debug(f"Event {event.id} matches AI-related term '{term}'")
                    break
            
            # Return true only if we found a whole word 'ai' or an AI-related term
            return ai_whole_word or ai_term_found
        
        # Handle compound keywords (e.g., "machine-learning")
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Check if it's a compound keyword with hyphens
            if '-' in keyword_lower:
                # Split into individual words
                individual_words = keyword_lower.split('-')
                
                # Check if all individual words appear in the title or description
                all_words_in_title = all(word in title for word in individual_words)
                all_words_in_description = description and all(word in description for word in individual_words)
                
                # Check for exact compound match
                compound_match = keyword_lower in title or keyword_lower in description or keyword_lower in url
                
                if compound_match:
                    self.logger.debug(f"Event {event.id} matches compound keyword '{keyword}' (exact match)")
                    return True
                
                if all_words_in_title:
                    self.logger.debug(f"Event {event.id} matches all words from compound keyword '{keyword}' in title")
                    return True
                
                if all_words_in_description:
                    self.logger.debug(f"Event {event.id} matches all words from compound keyword '{keyword}' in description")
                    return True
            
            # For regular keywords, use the original matching logic
            # Check for exact matches
            if (keyword_lower in title or 
                keyword_lower in description or 
                keyword_lower in categories or 
                keyword_lower in tags or
                keyword_lower in url):
                self.logger.debug(f"Event {event.id} matches keyword '{keyword}' (exact match)")
                return True
            
            # Check for word boundary matches in title
            title_words = title.split()
            for word in title_words:
                if keyword_lower == word or word.startswith(keyword_lower + " ") or word.endswith(" " + keyword_lower):
                    self.logger.debug(f"Event {event.id} matches keyword '{keyword}' (word match in title)")
                    return True
            
            # Check for word boundary matches in description
            if description:
                description_words = description.split()
                for word in description_words:
                    if keyword_lower == word or word.startswith(keyword_lower + " ") or word.endswith(" " + keyword_lower):
                        self.logger.debug(f"Event {event.id} matches keyword '{keyword}' (word match in description)")
                        return True
        
        return False

    def get_event_details(self, event_id: str) -> Optional[Event]:
        """
        Get details for a specific event.
        
        Args:
            event_id: Event ID
            
        Returns:
            Event object or None if not found
        """
        self.logger.info(f"Getting details for event ID: {event_id}")
        
        # Build URL - use the event URL format instead of search URL
        url = f"{EVENTBRITE_EVENT_URL}/event-tickets-{event_id}"
        self.logger.debug(f"Fetching event details from URL: {url}")
        
        # Make request
        html_content = self._get_with_retry(url)
        
        if not html_content:
            # Try alternative URL format as fallback
            alt_url = f"{EVENTBRITE_BASE_URL}/e/tickets-{event_id}"
            self.logger.debug(f"First attempt failed, trying alternative URL: {alt_url}")
            html_content = self._get_with_retry(alt_url)
            
            if not html_content:
                self.logger.error(f"Failed to get event details for ID: {event_id}")
                return None
        
        # Save HTML content for debugging if needed
        if os.getenv("SAVE_HTML", "False").lower() in ("true", "1", "t"):
            with open(f"eventbrite_event_{event_id}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info(f"Saved event details HTML to eventbrite_event_{event_id}.html")
        
        # Parse event details
        try:
            event = self.parser.parse_event_details(html_content, event_id)
            if event:
                self.logger.info(f"Successfully parsed event: {event.title}")
            else:
                self.logger.warning(f"Failed to parse event details for ID: {event_id}")
            return event
        except Exception as e:
            self.logger.exception(f"Error parsing event details: {str(e)}")
            # Save HTML content for debugging when parsing fails
            with open(f"eventbrite_event_{event_id}_failed_parse.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info(f"Saved failed parse HTML to eventbrite_event_{event_id}_failed_parse.html")
            return None
    
    def close(self):
        """Close the scraper and release resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.session.close()
