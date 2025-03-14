import re
import json
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup, Tag

from app.config import logger
from app.models.event import Event, Location, Organizer, Price, Coordinates


class EventParser:
    """
    Parser for extracting event data from Eventbrite HTML content.
    """
    
    def parse_search_results(self, html_content: str, page_size: int = 20) -> List[Event]:
        """
        Parse search results from HTML content.
        
        Args:
            html_content: HTML content of search results page
            page_size: Number of results per page (default: 20)
            
        Returns:
            List of events
        """
        events = []
        total_count = 0
        
        try:
            # Parse HTML content
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Try to find the event cards with different selectors
            event_cards = []
            selectors = [
                "div[data-testid='event-card']",
                ".search-event-card-wrapper",
                ".eds-event-card-content",
                ".eds-event-card",
                "[data-spec='event-card']",
                "article.eds-l-pad-all-4",  # Another possible selector
                "div.eds-event-card-content__content-container"  # Another possible selector
            ]
            
            for selector in selectors:
                cards = soup.select(selector)
                if cards:
                    logger.info(f"Found {len(cards)} event cards with selector: {selector}")
                    event_cards = cards
                    break
            
            if not event_cards:
                # Last resort: look for any links that might be event links
                event_links = soup.select("a[href*='/e/']")
                if event_links:
                    logger.info(f"Found {len(event_links)} event links")
                    # Try to find parent elements that might be event cards
                    for link in event_links:
                        parent = link.parent
                        for _ in range(3):  # Look up to 3 levels up
                            if parent and parent.name == 'div':
                                event_cards.append(parent)
                                break
                            parent = parent.parent if parent else None
                    
                    if event_cards:
                        logger.info(f"Extracted {len(event_cards)} potential event cards from links")
                    else:
                        logger.warning("Could not extract event cards from links")
            
            if not event_cards:
                logger.warning("No event cards found in search results")
                # Save the HTML structure for debugging
                with open("eventbrite_structure.txt", "w", encoding="utf-8") as f:
                    f.write(str(soup.prettify()))
                logger.debug("HTML structure saved to eventbrite_structure.txt")
                return []
            
            # Try to find total count with different selectors
            total_count_selectors = [
                "[data-testid='search-results-header']",
                ".eds-text-hl",
                "h1",
                ".search-results-header"
            ]
            
            for selector in total_count_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text()
                    count_match = re.search(r'(\d+)\s+events?', text)
                    if count_match:
                        total_count = int(count_match.group(1))
                        logger.info(f"Found total count: {total_count} with selector: {selector}")
                        break
                if total_count > 0:
                    break
            
            # If we couldn't find the total count, estimate based on pagination
            if total_count == 0:
                pagination_selectors = [".pagination", ".eds-pagination", "[data-spec='pagination']"]
                for selector in pagination_selectors:
                    pagination = soup.select_one(selector)
                    if pagination:
                        try:
                            last_page_elem = pagination.select("li")[-2]
                            last_page = last_page_elem.get_text().strip()
                            total_count = int(last_page) * page_size
                            logger.info(f"Estimated total count from pagination: {total_count}")
                            break
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to extract pagination info: {e}")
            
            # If we still don't have a count, use the number of cards as an estimate
            if total_count == 0:
                total_count = len(event_cards)
                logger.info(f"Using number of cards as total count: {total_count}")
            
            # Parse each event card
            for i, card in enumerate(event_cards):
                try:
                    logger.debug(f"Parsing event card {i+1}/{len(event_cards)}")
                    event = self._parse_event_card(card)
                    if event:
                        events.append(event)
                        logger.debug(f"Successfully parsed event: {event.title}")
                    else:
                        logger.warning(f"Failed to parse event card {i+1}")
                except Exception as e:
                    logger.error(f"Error parsing event card {i+1}: {e}")
                    continue
            
            logger.info(f"Parsed {len(events)} events from search results")
            return events
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_event_card(self, card: Tag) -> Optional[Event]:
        """
        Parse event data from a single event card.
        
        Args:
            card: BeautifulSoup Tag object of event card
            
        Returns:
            Event object if parsing successful, None otherwise
        """
        try:
            # Debug the card HTML
            card_html = str(card)
            logger.debug(f"Card HTML length: {len(card_html)}")
            if len(card_html) < 100:
                logger.warning("Card HTML is suspiciously short")
                logger.debug(f"Card HTML: {card_html}")
            
            # Extract event ID and URL
            link_elem = card.select_one("a[href*='/e/']")
            if not link_elem:
                logger.warning("No event link found in card")
                return None
            
            event_url = link_elem.get("href", "")
            logger.debug(f"Found event URL: {event_url}")
            
            if not event_url.startswith("http"):
                event_url = f"https://www.eventbrite.com{event_url}"
                logger.debug(f"Converted to absolute URL: {event_url}")
            
            event_id_match = re.search(r'/e/[^/]+-(\d+)', event_url)
            if not event_id_match:
                logger.warning(f"Could not extract event ID from URL: {event_url}")
                return None
            
            event_id = event_id_match.group(1)
            logger.debug(f"Extracted event ID: {event_id}")
            
            # Extract title with multiple possible selectors
            title_selectors = [
                "[data-testid='event-card-title']",
                ".eds-event-card__formatted-name--is-clamped",
                ".eds-event-card__formatted-name",
                ".card-text--truncated__one",
                "h3"
            ]
            
            title = "Unknown Event"
            for selector in title_selectors:
                title_elem = card.select_one(selector)
                if title_elem:
                    title = title_elem.get_text().strip()
                    logger.debug(f"Found title with selector '{selector}': {title}")
                    break
            
            # Extract date with multiple possible selectors
            date_selectors = [
                "[data-testid='event-card-date']",
                ".eds-event-card-content__sub-title",
                ".card-text--truncated__two",
                "time"
            ]
            
            date_str = ""
            for selector in date_selectors:
                date_elem = card.select_one(selector)
                if date_elem:
                    date_str = date_elem.get_text().strip()
                    logger.debug(f"Found date with selector '{selector}': {date_str}")
                    break
            
            # Extract location with multiple possible selectors
            location_selectors = [
                "[data-testid='event-card-location']",
                ".card-text--truncated__one",
                ".eds-event-card-content__sub-title:nth-child(2)",
                "p.location"
            ]
            
            location_str = ""
            for selector in location_selectors:
                location_elem = card.select_one(selector)
                if location_elem:
                    location_str = location_elem.get_text().strip()
                    logger.debug(f"Found location with selector '{selector}': {location_str}")
                    break
            
            # Extract image URL
            img_elem = card.select_one("img")
            image_url = ""
            if img_elem:
                image_url = img_elem.get("src", "")
                logger.debug(f"Found image URL: {image_url}")
            
            # Extract price with multiple possible selectors
            price_selectors = [
                "[data-testid='event-card-price']",
                ".eds-event-card-content__sub-title:nth-child(3)",
                ".eds-text-color--ui-600",
                "p.price"
            ]
            
            price_str = ""
            for selector in price_selectors:
                price_elem = card.select_one(selector)
                if price_elem:
                    price_str = price_elem.get_text().strip()
                    logger.debug(f"Found price with selector '{selector}': {price_str}")
                    break
            
            is_free = "free" in price_str.lower()
            
            # Create location object
            location = Location(
                venue=None,
                address=None,
                city=location_str,
                state=None,
                country=None,
                coordinates=None
            )
            
            # Create price object
            price = Price(
                currency="USD",  # Default, would need more parsing for accuracy
                min=0 if is_free else None,
                max=None,
                is_free=is_free
            )
            
            # Create event object
            event = Event(
                id=event_id,
                title=title,
                description=None,  # Would need to fetch event details for this
                start_date=None,  # Would need more parsing of date_str
                end_date=None,
                location=location,
                organizer=None,  # Would need to fetch event details for this
                price=price,
                url=event_url,
                image_url=image_url,
                categories=[],
                tags=[]
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error parsing event card: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def parse_event_details(self, html_content: str, event_id: str) -> Optional[Event]:
        """
        Parse detailed event information from event page.
        
        Args:
            html_content: HTML content of event page
            event_id: Event ID
            
        Returns:
            Event object if parsing successful, None otherwise
        """
        try:
            # Parse HTML content
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Try to extract JSON-LD data first (most reliable)
            json_ld_data = self._extract_json_ld(soup)
            if json_ld_data:
                logger.info("Found JSON-LD data, using it for parsing")
                return self._parse_from_json_ld(json_ld_data, event_id, "")
            
            # Extract title with multiple possible selectors
            title_selectors = [
                "[data-testid='event-title']",
                ".event-title",
                "h1",
                ".eds-text-hl"
            ]
            
            title = "Unknown Event"
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text().strip()
                    logger.debug(f"Found title with selector '{selector}': {title}")
                    break
            
            # Extract description with multiple possible selectors
            desc_selectors = [
                "[data-testid='event-description']",
                ".event-description",
                ".eds-text-bs",
                "section.eds-structure__content"
            ]
            
            description = None
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text().strip()
                    logger.debug(f"Found description with selector '{selector}' (length: {len(description) if description else 0})")
                    break
            
            # Extract date and time with multiple possible selectors
            date_selectors = [
                "[data-testid='event-date']",
                ".event-details__data",
                "time",
                ".date-info"
            ]
            
            date_str = ""
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_str = date_elem.get_text().strip()
                    logger.debug(f"Found date with selector '{selector}': {date_str}")
                    break
            
            # Try to parse dates (this is simplified and would need more robust parsing)
            start_date = None
            end_date = None
            
            # Extract location details with multiple possible selectors
            venue_selectors = [
                "[data-testid='venue-name']",
                ".event-details__data--venue",
                ".location-info__venue",
                "p.venue-name"
            ]
            
            venue = None
            for selector in venue_selectors:
                venue_elem = soup.select_one(selector)
                if venue_elem:
                    venue = venue_elem.get_text().strip()
                    logger.debug(f"Found venue with selector '{selector}': {venue}")
                    break
            
            address_selectors = [
                "[data-testid='venue-address']",
                ".event-details__data--address",
                ".location-info__address",
                "p.address"
            ]
            
            address = None
            for selector in address_selectors:
                address_elem = soup.select_one(selector)
                if address_elem:
                    address = address_elem.get_text().strip()
                    logger.debug(f"Found address with selector '{selector}': {address}")
                    break
            
            # Extract organizer information with multiple possible selectors
            org_selectors = [
                "[data-testid='organizer-name']",
                ".organizer-name",
                ".organizer-info__name",
                "a[href*='/o/']"
            ]
            
            org_name = None
            for selector in org_selectors:
                org_elem = soup.select_one(selector)
                if org_elem:
                    org_name = org_elem.get_text().strip()
                    logger.debug(f"Found organizer name with selector '{selector}': {org_name}")
                    break
            
            org_desc_selectors = [
                "[data-testid='organizer-description']",
                ".organizer-description",
                ".organizer-info__description"
            ]
            
            org_desc = None
            for selector in org_desc_selectors:
                org_desc_elem = soup.select_one(selector)
                if org_desc_elem:
                    org_desc = org_desc_elem.get_text().strip()
                    logger.debug(f"Found organizer description with selector '{selector}' (length: {len(org_desc) if org_desc else 0})")
                    break
            
            # Extract price information with multiple possible selectors
            price_selectors = [
                "[data-testid='ticket-price']",
                ".ticket-price",
                ".eds-text-color--ui-600",
                "span.price"
            ]
            
            price_str = ""
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_str = price_elem.get_text().strip()
                    logger.debug(f"Found price with selector '{selector}': {price_str}")
                    break
            
            is_free = "free" in price_str.lower()
            
            # Extract image URL with multiple possible selectors
            img_selectors = [
                "[data-testid='event-image']",
                ".event-header__image img",
                ".eds-event-details-page__image img",
                "img.event-image"
            ]
            
            image_url = ""
            for selector in img_selectors:
                img_elem = soup.select_one(selector)
                if img_elem:
                    image_url = img_elem.get("src", "")
                    logger.debug(f"Found image URL with selector '{selector}': {image_url}")
                    break
            
            # Extract categories and tags
            categories = []
            tags = []
            
            category_selectors = [
                "[data-testid='event-category']",
                ".event-category",
                ".eds-text-color--ui-600"
            ]
            
            for selector in category_selectors:
                category_elems = soup.select(selector)
                for elem in category_elems:
                    text = elem.get_text().strip()
                    if text and len(text) < 50:  # Avoid picking up long text
                        categories.append(text)
            
            logger.debug(f"Found categories: {categories}")
            
            tag_selectors = [
                "[data-testid='event-tag']",
                ".event-tag",
                ".eds-text-color--ui-600"
            ]
            
            for selector in tag_selectors:
                tag_elems = soup.select(selector)
                for elem in tag_elems:
                    text = elem.get_text().strip()
                    if text and len(text) < 50 and text not in categories:  # Avoid duplicates
                        tags.append(text)
            
            logger.debug(f"Found tags: {tags}")
            
            # Create location object
            location = Location(
                venue=venue,
                address=address,
                city=None,  # Would need to parse from address
                state=None,  # Would need to parse from address
                country=None,  # Would need to parse from address
                coordinates=None  # Would need to extract from page or use geocoding
            )
            
            # Create organizer object
            organizer = Organizer(
                name=org_name,
                description=org_desc,
                url=None  # Would need to extract from page
            )
            
            # Create price object
            price = Price(
                currency="USD",  # Default, would need more parsing for accuracy
                min=0 if is_free else None,  # Would need to parse from price_str
                max=None,  # Would need to parse from price_str
                is_free=is_free
            )
            
            # Create event object
            event = Event(
                id=event_id,
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location=location,
                organizer=organizer,
                price=price,
                url="",
                image_url=image_url,
                categories=categories,
                tags=tags
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error parsing event details: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract JSON-LD data from page if available.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary of JSON-LD data if found, None otherwise
        """
        try:
            # Find all JSON-LD scripts
            json_ld_scripts = soup.select("script[type='application/ld+json']")
            if not json_ld_scripts:
                logger.debug("No JSON-LD data found")
                return None
                
            logger.debug(f"Found {len(json_ld_scripts)} JSON-LD scripts")
            
            # Try to find one with event data
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Check if this is event data
                    if isinstance(data, dict):
                        event_type = data.get("@type", "")
                        if event_type in ["Event", "SocialEvent", "BusinessEvent", "EducationEvent"]:
                            logger.debug(f"Found JSON-LD data with @type: {event_type}")
                            return data
                        
                        # Some events might not have @type directly but have event properties
                        if "startDate" in data and "name" in data:
                            logger.debug("Found JSON-LD data with event properties")
                            return data
                except Exception as e:
                    logger.debug(f"Error parsing JSON-LD script: {e}")
                    continue
            
            # If no event data found, return the first JSON-LD script as fallback
            logger.debug("No event data found in JSON-LD scripts, using first script as fallback")
            return json.loads(json_ld_scripts[0].string)
            
        except Exception as e:
            logger.error(f"Error extracting JSON-LD: {e}")
            return None
    
    def _parse_from_json_ld(self, data: Dict[str, Any], event_id: str, url: str = "") -> Optional[Event]:
        """
        Parse event details from JSON-LD data.
        
        Args:
            data: JSON-LD data
            event_id: Event ID
            url: Event URL (optional)
            
        Returns:
            Event object if parsing successful, None otherwise
        """
        try:
            # Check if this is event data
            event_type = data.get("@type", "")
            valid_event_types = ["Event", "SocialEvent", "BusinessEvent", "EducationEvent"]
            
            # If @type is not a valid event type, check if it has event properties
            if event_type not in valid_event_types:
                if "startDate" not in data or "name" not in data:
                    logger.warning(f"JSON-LD data is not an Event (type: {event_type}) and doesn't have event properties")
                    return None
                logger.debug("JSON-LD data doesn't have a valid event type but has event properties")
            else:
                logger.debug(f"JSON-LD data has valid event type: {event_type}")
            
            title = data.get("name", "Unknown Event")
            description = data.get("description", None)
            
            # Parse dates
            start_date = None
            end_date = None
            if "startDate" in data:
                try:
                    start_date = datetime.fromisoformat(data["startDate"].replace("Z", "+00:00"))
                    logger.debug(f"Parsed start date: {start_date}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse start date: {e}")
            
            if "endDate" in data:
                try:
                    end_date = datetime.fromisoformat(data["endDate"].replace("Z", "+00:00"))
                    logger.debug(f"Parsed end date: {end_date}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse end date: {e}")
            
            # Parse location
            location_data = data.get("location", {})
            venue = location_data.get("name", None)
            address_data = location_data.get("address", {})
            
            address_parts = []
            if "streetAddress" in address_data:
                address_parts.append(address_data["streetAddress"])
            if "addressLocality" in address_data:
                address_parts.append(address_data["addressLocality"])
            if "addressRegion" in address_data:
                address_parts.append(address_data["addressRegion"])
            if "postalCode" in address_data:
                address_parts.append(address_data["postalCode"])
            
            address = ", ".join(address_parts) if address_parts else None
            city = address_data.get("addressLocality", None)
            state = address_data.get("addressRegion", None)
            country = address_data.get("addressCountry", None)
            
            # Parse coordinates
            coordinates = None
            geo = location_data.get("geo", {})
            if "latitude" in geo and "longitude" in geo:
                coordinates = Coordinates(
                    latitude=float(geo["latitude"]),
                    longitude=float(geo["longitude"])
                )
            
            # Create location object
            location = Location(
                venue=venue,
                address=address,
                city=city,
                state=state,
                country=country,
                coordinates=coordinates
            )
            
            # Parse organizer
            organizer_data = data.get("organizer", {})
            org_name = organizer_data.get("name", None)
            org_url = organizer_data.get("url", None)
            
            # Create organizer object
            organizer = Organizer(
                name=org_name,
                description=None,
                url=org_url
            )
            
            # Parse price
            offers = data.get("offers", [])
            if not isinstance(offers, list):
                offers = [offers]
            
            price_min = None
            price_max = None
            currency = "USD"
            is_free = False
            
            for offer in offers:
                if "price" in offer:
                    try:
                        price = float(offer["price"])
                        if price_min is None or price < price_min:
                            price_min = price
                        if price_max is None or price > price_max:
                            price_max = price
                    except (ValueError, TypeError):
                        pass
                
                if "priceCurrency" in offer:
                    currency = offer["priceCurrency"]
                
                if "availability" in offer and offer["availability"] == "http://schema.org/InStock":
                    if "price" in offer and float(offer["price"]) == 0:
                        is_free = True
            
            # Create price object
            price = Price(
                currency=currency,
                min=price_min,
                max=price_max,
                is_free=is_free
            )
            
            # Parse image
            image_url = ""
            if "image" in data:
                if isinstance(data["image"], list) and data["image"]:
                    image_url = data["image"][0]
                else:
                    image_url = data["image"]
            
            # Parse categories and tags
            categories = []
            if "eventAttendanceMode" in data:
                categories.append(data["eventAttendanceMode"])
            if "eventStatus" in data:
                categories.append(data["eventStatus"])
            
            # Create event object
            event = Event(
                id=event_id,
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                location=location,
                organizer=organizer,
                price=price,
                url=url,
                image_url=image_url,
                categories=categories,
                tags=[]
            )
            
            return event
            
        except Exception as e:
            logger.error(f"Error parsing from JSON-LD: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
