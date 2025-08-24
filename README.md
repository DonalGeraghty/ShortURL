# Python REST API

A simple Flask-based REST API that handles POST requests with JSON data.

## Features

- **Single POST endpoint** at `/api/data` for submitting data
- **Health check endpoint** at `/health` for monitoring
- **Root endpoint** at `/` for API information
- **CORS enabled** for cross-origin requests
- **JSON validation** and error handling
- **Timestamp tracking** for all requests

## Setup

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. **Clone or download the project files**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

The API will start on `http://localhost:5000`

## API Endpoints

### POST /api/data
Main endpoint for submitting data via POST request.

**Request:**
- Method: `POST`
- Content-Type: `application/json`
- Body: JSON data

**Example Request:**
```bash
curl -X POST http://localhost:5000/api/data \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

**Response:**
```json
{
  "message": "Data received successfully",
  "timestamp": "2024-01-01T12:00:00Z",
  "received_data": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "status": "success"
}
```

### GET /health
Health check endpoint to verify API status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### GET /
Root endpoint providing API information.

**Response:**
```json
{
  "message": "Python REST API",
  "endpoints": {
    "POST /api/data": "Submit data via POST request",
    "GET /health": "Health check endpoint",
    "GET /": "This information endpoint"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Testing

### Using the Test Script

1. **Install requests library:**
   ```bash
   pip install requests
   ```

2. **Run the test script:**
   ```bash
   python test_api.py
   ```

### Using curl

```bash
# Test health endpoint
curl http://localhost:5000/health

# Test POST endpoint
curl -X POST http://localhost:5000/api/data \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Using Postman or similar tools

- **URL:** `http://localhost:5000/api/data`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`
- **Body:** Raw JSON with your data

## Environment Variables

- `PORT`: Server port (default: 5000)
- `FLASK_ENV`: Set to `development` for debug mode

## Error Handling

The API includes comprehensive error handling:

- **400 Bad Request:** Invalid JSON or missing data
- **500 Internal Server Error:** Server-side errors

All errors return JSON responses with error details.

## Customization

You can customize the POST endpoint in `app.py` by modifying the `handle_post()` function to:

- Add data validation rules
- Implement business logic
- Connect to databases
- Add authentication
- Process specific data types

## Project Structure

```
shortUrl/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── test_api.py        # Test script
└── README.md          # This file
```

## Troubleshooting

### Common Issues

1. **Port already in use:**
   - Change the port in `app.py` or set `PORT` environment variable
   - Kill existing processes using the port

2. **Import errors:**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`

3. **CORS issues:**
   - The API includes CORS support, but you can modify CORS settings in `app.py`

## License

This project is open source and available under the MIT License.
