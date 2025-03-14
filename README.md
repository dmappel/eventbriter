# Eventbrite Scraper

A Python-based scraper for extracting event information from Eventbrite with a FastAPI backend. This tool allows you to search for events, retrieve detailed event information, and export data in various formats.

## Features

- **Event Search**: Search for events based on location, date range, and keywords
- **Event Details**: Get comprehensive information about specific events
- **Data Export**: Export event data in JSON and CSV formats
- **RESTful API**: Modern API built with FastAPI
- **Rate Limiting**: Basic rate limiting to prevent abuse
- **Logging**: Comprehensive request and error logging
- **Docker Support**: Easy deployment with Docker
- **CORS Support**: Cross-Origin Resource Sharing enabled for frontend integration

## Project Structure

```
eventbrite-scraper/
├── app/                    # Main application code
│   ├── api/                # API routes and endpoints
│   │   ├── routes.py       # API endpoint definitions
│   │   └── __init__.py     # API package initialization
│   ├── models/             # Pydantic data models
│   │   ├── event.py        # Event data models
│   │   ├── search.py       # Search request/response models
│   │   └── __init__.py     # Models package initialization
│   ├── scraper/            # Scraping functionality
│   │   ├── scraper.py      # Main scraper implementation
│   │   ├── parser.py       # HTML parsing logic
│   │   └── __init__.py     # Scraper package initialization
│   ├── config.py           # Configuration settings
│   ├── main.py             # FastAPI application setup
│   └── __init__.py         # App package initialization
├── .env                    # Environment variables (not in repo)
├── .env.example            # Example environment variables
├── requirements.txt        # Python dependencies
├── run.py                  # Script to run the application
├── Dockerfile              # Docker configuration
└── README.md               # Project documentation
```

## Requirements

- Python 3.9+
- Chrome/Chromium browser (for Selenium)
- Dependencies listed in requirements.txt:
  - fastapi
  - uvicorn
  - beautifulsoup4
  - selenium
  - requests
  - pydantic
  - pytest
  - python-dotenv
  - webdriver-manager
  - pandas

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd eventbrite-scraper
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure environment variables (copy from .env.example if needed):
   ```
   cp .env.example .env  # Then edit .env with your settings
   ```

## Configuration

The application can be configured using environment variables in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| API_HOST | Host to bind the API server | 0.0.0.0 |
| API_PORT | Port for the API server | 8000 |
| DEBUG | Enable debug mode | True |
| REQUEST_DELAY | Delay between requests (seconds) | 2 |
| MAX_RETRIES | Maximum number of retry attempts | 3 |
| USER_AGENT_ROTATION | Enable user agent rotation | True |

## Usage

### Running the API

Start the FastAPI server:

```
python run.py
```

The API will be available at http://localhost:8000 (or the port specified in your .env file)

### API Endpoints

#### Search Events
```
GET /events/search
```

Query Parameters:
- `locations`: List of locations to search in (e.g., "spain--barcelona")
- `keywords`: List of keywords to search for (e.g., "jazz")
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format
- `page`: Page number (default: 1)
- `page_size`: Number of results per page (default: 20, max: 100)
- `limit`: Maximum number of results to return

#### Get Event Details
```
GET /events/{event_id}
```

Path Parameters:
- `event_id`: The ID of the event to retrieve

#### Export Events
```
POST /events/export
```

Request Body:
```json
{
  "events": ["event_id_1", "event_id_2"],
  "format": "json"  // or "csv"
}
```

### API Documentation

Once the server is running, you can access the auto-generated API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Example Requests

Search for events:
```
http://localhost:8000/events/search?locations=spain--barcelona&keywords=jazz&start_date=2025-03-14&end_date=2025-03-31&limit=5
```

Get event details:
```
http://localhost:8000/events/1273996400529
```

## Docker

To run the application using Docker:

```
docker build -t eventbrite-scraper .
docker run -p 8000:8000 eventbrite-scraper
```

For production use, consider using Docker Compose with appropriate environment variables.

## Development

### Running Tests

```
pytest
```

### Logging

Logs are written to `eventbrite_scraper.log` by default. The log level can be controlled via the DEBUG environment variable.

## Limitations

- The scraper respects Eventbrite's robots.txt and implements rate limiting to avoid being blocked
- Some event details may not be available depending on how the event organizer has configured their listing
- The scraper may break if Eventbrite significantly changes their website structure

## License

[MIT License](LICENSE) 