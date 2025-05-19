# rear-differential

The rear-differential API provides a link between the main database of the automatic-transmission platform and the front-end layer

## Project Structure

```
rear-differential/
├── app/                        
│   ├── core/                   # Core application components
│   │   └── config.py           # Application settings
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   └── api.py              # API request/response models
│   ├── routers/                # API route handlers
│   │   └── training.py         # Training data endpoints
│   ├── services/               # Business logic
│   │   └── db_service.py       # Database service
│   └── main.py                 # FastAPI application entry point
├── .github/                    # GitHub configuration
│   └── workflows/              # GitHub Actions workflows
│       └── docker-build.yml    # Docker build workflow
├── dockerfile                  # Docker configuration
├── docker-compose.yaml         # Docker Compose configuration
├── requirements.in             # API-specific dependencies
└── requirements.txt            # Generated API dependencies
```

### API Endpoints

The API exposes the following endpoints:

- `GET /rear-diff/health` - Health check endpoint
- `GET /rear-diff/training` - Retrieves training data entries from the database
- `PATCH /rear-diff/training/{imdb_id}/label` - Updates the label for a specific training data entry

### GET /rear-diff/training

Retrieves training data entries from the database.

**Description**: This endpoint returns a collection of training data entries stored in the system. Each entry contains detailed information about media items with associated labels for training purposes.

**HTTP Method**: GET

**Parameters**: No required parameters for basic retrieval of all items.

**Optional Query Parameters**:

- `media_type`: Filter by media type (e.g., "movie", "tv_show", "tv_season")
- `label`: Filter by label (e.g., "would_watch", "would_not_watch")
- `limit`: Maximum number of records to return (default: 100)
- `offset`: Number of records to skip (for pagination)
- `sort_by`: Field to sort results by (default: "created_at")
- `sort_order`: Direction of sort ("asc" or "desc", default: "desc")

**Response**:

**Success Response (200 OK)**:

```json
{
  "data": [
    {
      "imdb_id": "tt2759766",
      "tmdb_id": 802473,
      "label": "would_watch",
      "media_type": "movie",
      "media_title": "40 Under 40",
      "season": null,
      "episode": null,
      "release_year": 2013,
      "genre": ["Documentary"],
      "language": ["en"],
      "rt_score": null,
      "metascore": null,
      "imdb_rating": 7.2,
      "imdb_votes": 1203,
      "created_at": "2025-05-07T20:33:57.738163Z",
      "updated_at": "2025-05-07T20:33:57.738163Z"
    }
  ],
  "pagination": {
    "total": 1245,
    "limit": 100,
    "offset": 0,
    "next": "/rear-diff/training?offset=100&limit=100",
    "previous": null
  }
}
```

**Error Response (500 Internal Server Error)**:

```json
{
  "error": "Database error occurred",
  "details": "Error details here"
}
```

### PATCH /rear-diff/training/{imdb_id}/label

Updates the label for a specific training data entry.

**Description**: This endpoint allows users to update the label column in the database for a training data entry identified by its IMDB ID.

**HTTP Method**: PATCH

**Path Parameters**:

- `imdb_id`: The unique identifier (format: tt followed by 7-8 digits) of the training data entry to update

**Request Body**:

```json
{
  "imdb_id": "tt2759766",
  "label": "would_watch"
}
```

**Required Fields**:

- `imdb_id`: String - The IMDB ID of the training data entry (must match the imdb_id in the URL path)
- `label`: String - The new label value
  - Valid values: "would_watch", "would_not_watch"

**Responses**:

**Success Response (200 OK)**:

```json
{
  "success": true,
  "message": "Label updated successfully"
}
```

**Error Responses**:

**400 Bad Request**:

```json
{
  "success": false,
  "error": "Invalid request",
  "message": "Label must be one of: would_watch, would_not_watch"
}
```

**400 Bad Request (IMDB ID Mismatch)**:

```json
{
  "success": false,
  "error": "IMDB ID mismatch",
  "message": "Path IMDB ID and body IMDB ID do not match"
}
```

**404 Not Found**:

```json
{
  "success": false,
  "error": "Training data not found",
  "message": "No training data found with IMDB ID: tt2759766"
}
```

**500 Internal Server Error**:

```json
{
  "success": false,
  "error": "Database error",
  "message": "Error details here"
}
```

## Testing the API Locally

To test the Rear Differential API locally before containerization:

1. Ensure required dependencies are installed:

```bash
pip install fastapi uvicorn psycopg2-binary
```

2. Start the API server:
```bash
uvicorn app.main:app --reload
```

3. Test the endpoints:

**Health check:**

```bash
curl http://localhost:8000/rear-diff/health
```
```powershell
Invoke-RestMethod -Uri http://localhost:8000/rear-diff/health
```

**Get training data:**

```bash
# Get all training data
curl http://localhost:8000/rear-diff/training
```
```powershell
Invoke-RestMethod -Uri http://localhost:8000/rear-diff/training
```

```bash
# Get movies only
curl "http://localhost:8000/rear-diff/training?media_type=movie&limit=10"
```
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/training?media_type=movie&limit=10"
```

```bash
# Get items with specific label
curl "http://localhost:8000/rear-diff/training?label=would_watch&limit=25&sort_by=updated_at&sort_order=desc"
```
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/training?label=would_watch&limit=25&sort_by=updated_at&sort_order=desc"
```

**Update label:**

```bash
# Update label to "would_watch"
curl -X PATCH http://localhost:8000/rear-diff/training/tt2759766/label \
  -H "Content-Type: application/json" \
  -d '{"imdb_id": "tt2759766", "label": "would_watch"}'
```
```powershell
$body = @{
  imdb_id = "tt2759766"
  label = "would_watch"
}
$json = ConvertTo-Json $body
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/training/tt2759766/label" -Method Patch -Body $json -ContentType "application/json"
```

4. Access the interactive API documentation at http://localhost:8000/rear-diff/docs

## Building and Running in Docker Locally

**Building the image**
```bash
# Regular build
docker build -t rear-diff-image -f dockerfile .

# Force rebuild without cache
docker build --no-cache -t rear-diff -f dockerfile .
```

**Running the container**
```bash
# Run container in foreground
docker run -p 8000:8000 --name rear-diff-container --env-file .env rear-diff-image

# Run container in background
docker run -d -p 8000:8000 --name rear-diff-container --env-file .env rear-diff-image
```

**With Docker Compose**
```bash
# Build and start services
docker compose -f docker-compose.yaml up -d

# Run in foreground
docker compose -f docker-compose.yaml up

# Build with no cache and start
docker compose -f docker-compose.yaml build --no-cache
docker compose -f docker-compose.yaml up


# Stop services
docker compose -f docker-compose.yaml down
```

**container clean-up**
```bash
# stop container
docker stop rear-diff-container

# remove container
docker rm rear-diff-container

# remove image
docker image rmi rear-diff-image

# full clean-up
docker stop rear-diff-container && docker rm rear-diff-container && docker image rmi rear-diff-image
```

**Troubleshooting**
```bash
# View logs
docker logs rear-diff-container

# Shell into container
docker exec -it rear-diff-container bash

# Check container status
docker ps -a | grep rear-diff-container
```

## Integration

This project will eventually be converted into a microservice to work alongside [automatic-transmission](https://github.com/x81k25/automatic-transmission) as an API bridge between the production database and the front-end layer 

## License

MIT License