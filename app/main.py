import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

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
