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
│   │   └── media.py            # Media endpoints
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
- `GET /rear-diff/media` - Retrieves all media entries from the database
- `PATCH /rear-diff/media/{hash}/rejection-status` - Updates the rejection status for a specific media item

### GET /rear-diff/media

Retrieves all media entries from the database.

**Description**: This endpoint returns a collection of all media items stored in the system. Each item contains detailed information about media files including identification, content metadata, processing status, and technical specifications.

**HTTP Method**: GET

**Parameters**: No required parameters for basic retrieval of all items.

**Optional Query Parameters**:

- `media_type`: Filter by media type (e.g., "movie", "tv")
- `pipeline_status`: Filter by processing status (e.g., "ingested", "rejected")
- `limit`: Maximum number of records to return (default: 100)
- `offset`: Number of records to skip (for pagination)
- `sort_by`: Field to sort results by (default: "created_at")
- `sort_order`: Direction of sort ("asc" or "desc", default: "desc")

**Response**:

Returns a JSON array of media objects with the following structure:

**Success Response (200 OK)**:

```json
{
  "data": [
    {
      "hash": "eb50f630702e8a59ef6ecfaf9f5eecae7a9856a1",
      "media_type": "movie",
      "media_title": "40 Under 40",
      "season": null,
      "episode": null,
      "release_year": 2013,
      "pipeline_status": "rejected",
      "error_status": false,
      "error_condition": "media ratings API status code: 401",
      "rejection_status": "rejected",
      "rejection_reason": "resolution 720p is not in allowed_values",
      "parent_path": null,
      "target_path": null,
      "original_title": "40 Under 40 (2013) [720p] [WEBRip] [YTS.MX]",
      "original_path": null,
      "original_link": "https://yts.mx/torrent/download/EB50F630702E8A59EF6ECFAF9F5EECAE7A9856A1",
      "rss_source": null,
      "uploader": null,
      "genre": ["Documentary"],
      "language": ["en"],
      "rt_score": null,
      "metascore": null,
      "imdb_rating": null,
      "imdb_votes": null,
      "imdb_id": "tt2759766",
      "resolution": "720p",
      "video_codec": null,
      "upload_type": "WEBRip",
      "audio_codec": null,
      "created_at": "2025-05-07T20:33:57.738163Z",
      "updated_at": "2025-05-07T20:33:57.738163Z",
      "tmdb_id": 802473
    }
  ],
  "pagination": {
    "total": 1245,
    "limit": 100,
    "offset": 0,
    "next": "/rear-diff/media?offset=100&limit=100",
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

### PATCH /rear-diff/media/{hash}/rejection-status

Updates the rejection status for a specific media item.

**Description**: This endpoint allows users to update the rejection_status column in the database for a media item identified by its hash.

**HTTP Method**: PATCH

**Path Parameters**:

- `hash`: The unique identifier (40-character SHA-1 hash) of the media item to update

**Request Body**:

```json
{
  "hash": "eb50f630702e8a59ef6ecfaf9f5eecae7a9856a1",
  "rejection_status": "accepted"
}
```

**Required Fields**:

- `hash`: String - The 40-character SHA-1 hash of the media item (must match the hash in the URL path)
- `rejection_status`: String - The new rejection status value
  - Valid values: "unfiltered", "accepted", "rejected", "override"

**Responses**:

**Success Response (200 OK)**:

```json
{
  "success": true,
  "message": "Rejection status updated successfully"
}
```

**Error Responses**:

**400 Bad Request**:

```json
{
  "success": false,
  "error": "Invalid request",
  "message": "Rejection status must be one of: unfiltered, accepted, rejected, override"
}
```

**400 Bad Request (Hash Mismatch)**:

```json
{
  "success": false,
  "error": "Hash mismatch",
  "message": "Path hash and body hash do not match"
}
```

**404 Not Found**:

```json
{
  "success": false,
  "error": "Media not found",
  "message": "No media found with hash: eb50f630702e8a59ef6ecfaf9f5eecae7a9856a1"
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

**Get media entries:**

```bash
# Get all media
curl http://localhost:8000/rear-diff/media
```
```powershell
Invoke-RestMethod -Uri http://localhost:8000/rear-diff/media
```

```bash
# Get movies only
curl "http://localhost:8000/rear-diff/media?media_type=movie&limit=10"
```
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/media?media_type=movie&limit=10"
```

```bash
# Get rejected media items
curl "http://localhost:8000/rear-diff/media?pipeline_status=rejected&limit=25&sort_by=updated_at&sort_order=desc"
```
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/media?pipeline_status=rejected&limit=25&sort_by=updated_at&sort_order=desc"
```

**Update rejection status:**

```bash
# Update rejection status to "accepted"
curl -X PATCH http://localhost:8000/rear-diff/media/eb50f630702e8a59ef6ecfaf9f5eecae7a9856a1/rejection-status \
  -H "Content-Type: application/json" \
  -d '{"hash": "eb50f630702e8a59ef6ecfaf9f5eecae7a9856a1", "rejection_status": "accepted"}'
```
```powershell
$body = @{
  hash = "eb50f630702e8a59ef6ecfaf9f5eecae7a9856a1"
  rejection_status = "accepted"
}
$json = ConvertTo-Json $body
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/media/eb50f630702e8a59ef6ecfaf9f5eecae7a9856a1/rejection-status" -Method Patch -Body $json -ContentType "application/json"
```

4. Access the interactive API documentation at http://localhost:8000/rear-diff/docs

5. To stop the server when finished:
```bash
# Press Ctrl+C in the terminal running the server
```

6. Kill any running instances that weren't terminated properly
```bash
pkill -9 python
```
```powershell
Get-Process -Name python | Stop-Process -Force
```

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
docker compose -f docker-compose.yaml up

# Build with no cache and start
docker compose -f docker-compose.yaml build --no-cache
docker compose -f docker-compose.yaml up

# Run in background
docker compose -f docker-compose.yaml up -d

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