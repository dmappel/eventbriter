import os
import logging
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Scraper Settings
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "2"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
USER_AGENT_ROTATION = os.getenv("USER_AGENT_ROTATION", "True").lower() in ("true", "1", "t")

# User Agent List for rotation
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
]

# Eventbrite Base URLs
EVENTBRITE_BASE_URL = "https://www.eventbrite.com"
EVENTBRITE_SEARCH_URL = f"{EVENTBRITE_BASE_URL}/d"
EVENTBRITE_EVENT_URL = f"{EVENTBRITE_BASE_URL}/e"

# Configure logging
def setup_logging():
    """Configure logging for the application."""
    # Always use DEBUG level for development
    log_level = logging.DEBUG
    
    # Create logger
    logger = logging.getLogger("eventbrite_scraper")
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    
    # Create console handler and set level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Create file handler for debug logs
    file_handler = logging.FileHandler("eventbrite_scraper.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logging()
