import os
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import API_HOST, API_PORT, DEBUG, logger
from app.api.routes import router as api_router


# Create FastAPI app
app = FastAPI(
    title="Eventbrite Scraper API",
    description="API for scraping events from Eventbrite",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Add middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and their processing time."""
    start_time = time.time()
    
    # Generate a unique request ID
    request_id = f"{int(start_time * 1000)}"
    
    # Log the request
    logger.info(f"Request {request_id}: {request.method} {request.url.path}")
    
    # Process the request
    try:
        response = await call_next(request)
        
        # Log the response time
        process_time = time.time() - start_time
        logger.info(f"Request {request_id} completed in {process_time:.3f}s with status {response.status_code}")
        
        return response
    except Exception as e:
        # Log any unhandled exceptions
        logger.exception(f"Request {request_id} failed with error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e) if DEBUG else None}
        )

# Add rate limiting middleware (simplified version)
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # This is a very simple rate limiter
    # In a production environment, you would use a more robust solution
    # like Redis-based rate limiting
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Check if client is rate limited
    # For now, we're not implementing actual rate limiting
    
    # Process the request
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = "99"
    
    return response

# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint and redirect to API documentation."""
    return RedirectResponse(url="/docs")

# Include API routes
app.include_router(api_router)

# Run the application
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Eventbrite Scraper API on {API_HOST}:{API_PORT} (Debug: {DEBUG})")
    
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info"
    )
