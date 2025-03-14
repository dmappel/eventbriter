#!/usr/bin/env python3
"""
Script to run the Eventbrite Scraper API.
"""

import uvicorn
from app.config import API_HOST, API_PORT, DEBUG, logger

if __name__ == "__main__":
    logger.info(f"Starting server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG
    ) 