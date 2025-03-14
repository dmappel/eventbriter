# Eventbrite Scraper

A Python-based scraper for extracting event information from Eventbrite with a FastAPI backend.

## Features

- Search for events based on location, date range, and keywords
- Get detailed information about specific events
- Export event data in JSON and CSV formats
- RESTful API with FastAPI

## Requirements

- Python 3.9+
- Chrome/Chromium browser (for Selenium)

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

## Usage

### Running the API

Start the FastAPI server:

```
python run.py
```

The API will be available at http://localhost:8001 (or the port specified in your .env file)

### API Endpoints

- `GET /events/search` - Search for events with filters
- `GET /events/{event_id}` - Get detailed information about a specific event
- `POST /events/export` - Export event data in various formats

### API Documentation

Once the server is running, you can access the auto-generated API documentation:

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Example Requests

Search for events:
```
http://localhost:8001/events/search?location=spain--barcelona&keywords=jazz&start_date=2025-03-14&end_date=2025-03-31&limit=5
```

Get event details:
```
http://localhost:8001/events/1273996400529
```

## Docker

To run the application using Docker:

```
docker build -t eventbrite-scraper .
docker run -p 8001:8001 eventbrite-scraper
```

## License

[MIT License](LICENSE) 