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
      "imdb_id": "tt21815562",
      "tmdb_id": 1013601,
      "label": "would_not_watch",
      "media_type": "movie",
      "media_title": "The Alto Knights",
      "season": null,
      "episode": null,
      "release_year": 2025,
      "budget": 45000000,
      "revenue": 9577695,
      "runtime": 123,
      "origin_country": ["US"],
      "production_companies": ["Warner Bros. Pictures", "Winkler Films", "Domain Entertainment"],
      "production_countries": ["US"],
      "production_status": "Released",
      "original_language": "en",
      "spoken_languages": ["en"],
      "genre": ["Crime", "Drama", "History"],
      "original_media_title": "The Alto Knights",
      "tagline": "The most dangerous enemy is an old friend.",
      "overview": "Two of New York's most notorious organized crime bosses, Frank Costello and Vito Genovese, vie for control of the city's streets. Once the best of friends, petty jealousies and a series of betrayals place them on a deadly collision course that will reshape the Mafia (and America) forever.",
      "tmdb_rating": 6.241,
      "tmdb_votes": 172,
      "rt_score": 39,
      "metascore": 47,
      "imdb_rating": 5.7,
      "imdb_votes": 6467,
      "human_labeled": null,
      "anomalous": null,
      "created_at": "2025-05-21T02:27:51.094287Z",
      "updated_at": "2025-05-21T02:27:51.094287Z"
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

*Get all training data*
```bash
# bash
curl http://localhost:8000/rear-diff/training
```
```powershell
# powershell
Invoke-RestMethod -Uri http://localhost:8000/rear-diff/training
```

*Get movies only*
```bash
# bash
curl "http://localhost:8000/rear-diff/training?media_type=movie&limit=10"
```
```powershell
# powershell
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/training?media_type=movie&limit=10"
```

*Get items with specific label*
```bash
# bash
curl "http://localhost:8000/rear-diff/training?label=would_watch&limit=25&sort_by=updated_at&sort_order=desc"
```
```powershell
# powershell
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/training?label=would_watch&limit=25&sort_by=updated_at&sort_order=desc"
```

**Update label:**

```bash
# bash
curl -X PATCH http://localhost:8000/rear-diff/training/tt2759766/label \
  -H "Content-Type: application/json" \
  -d '{"imdb_id": "tt2759766", "label": "would_watch"}'
```
```powershell
# powershell
$body = @{
  imdb_id = "tt2759766"
  label = "would_watch"
}
$json = ConvertTo-Json $body
Invoke-RestMethod -Uri "http://localhost:8000/rear-diff/training/tt2759766/label" -Method Patch -Body $json -ContentType "application/json"
```

4. Access the interactive API documentation at http://localhost:8000/rear-diff/docs

5. To stop the server when finished:

# Press Ctrl+C in the terminal running the server

6. Kill any running instances that weren't terminated properly

```bash
# bash
pkill -9 python
````
```powershell
# powershell
Get-Process -Name python | Stop-Process -Force
```

## building and running in docker locally

**building the image**
```bash
# regular build
docker build -t rear-diff-image -f dockerfile .

# force rebuild without cache
docker build --no-cache -t rear-diff -f dockerfile .
```

**running the container**
```bash
# run container in foreground
docker run -p 8000:8000 --name rear-diff-container --env-file .env rear-diff-image

# run container in background
docker run -d -p 8000:8000 --name rear-diff-container --env-file .env rear-diff-image
```

**with docker compose**
```bash
# build and start services
docker compose -f docker-compose.yaml up -d

# run in foreground
docker compose -f docker-compose.yaml up

# build with no cache and start
docker compose -f docker-compose.yaml build --no-cache
docker compose -f docker-compose.yaml up

# stop services
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

**troubleshooting**
```bash
# view logs
docker logs rear-diff-container

# shell into container
docker exec -it rear-diff-container bash

# check container status
docker ps -a | grep rear-diff-container
```

## integration

This project will eventually be converted into a microservice to work alongside [automatic-transmission](https://github.com/x81k25/automatic-transmission) as an API bridge between the production database and the front-end layer 

## license

MIT License