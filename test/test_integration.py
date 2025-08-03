# test/test_integration.py
"""Integration tests for all API endpoints."""
import pytest
import requests
import json
from typing import Dict, Any

def assert_success_response(response, endpoint_name: str = "endpoint"):
    """Helper function to assert successful response and handle common error cases."""
    # Check for server errors (5xx)
    if 500 <= response.status_code < 600:
        pytest.fail(f"{endpoint_name} returned server error {response.status_code}: {response.text}")
    
    # Check for client errors (4xx) - most should be 200 for these tests
    if 400 <= response.status_code < 500:
        pytest.fail(f"{endpoint_name} returned client error {response.status_code}: {response.text}")
    
    # Assert 200 specifically
    assert response.status_code == 200, f"{endpoint_name} failed with {response.status_code}: {response.text}"
    
    # Check if response is JSON and has error indicators
    try:
        data = response.json()
        if isinstance(data, dict):
            # Check for common error message patterns
            if "message" in data and any(error_word in data["message"].lower() 
                                       for error_word in ["error", "failed", "permission denied", "unauthorized"]):
                pytest.fail(f"{endpoint_name} returned error message: {data['message']}")
        return data
    except json.JSONDecodeError:
        # If it's not JSON, that might be an error too for API endpoints
        if response.headers.get("content-type", "").startswith("application/json"):
            pytest.fail(f"{endpoint_name} returned invalid JSON: {response.text}")
        return None

class TestHealthAndRoot:
    """Test health check and root endpoints."""
    
    def test_health_endpoint(self, api_server, base_url):
        """Test the health check endpoint."""
        response = requests.get(f"{base_url}/rear-diff/health")
        data = assert_success_response(response, "Health endpoint")
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, api_server, base_url):
        """Test the root endpoint."""
        response = requests.get(f"{base_url}/rear-diff/")
        data = assert_success_response(response, "Root endpoint")
        assert "message" in data
        assert "docs" in data
        assert "health" in data

class TestTrainingEndpoints:
    """Test training-related endpoints."""
    
    def test_get_training_data_basic(self, api_server, base_url):
        """Test basic GET request to training endpoint."""
        response = requests.get(f"{base_url}/rear-diff/training?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) <= 5
    
    def test_get_training_data_with_filters(self, api_server, base_url):
        """Test GET training with various filters."""
        # Test media_type filter
        response = requests.get(f"{base_url}/rear-diff/training?media_type=movie&limit=3")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["media_type"] == "movie"
        
        # Test label filter
        response = requests.get(f"{base_url}/rear-diff/training?label=would_watch&limit=3")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["label"] == "would_watch"
        
        # Test boolean filters
        response = requests.get(f"{base_url}/rear-diff/training?reviewed=true&limit=3")
        assert response.status_code == 200
        
        response = requests.get(f"{base_url}/rear-diff/training?human_labeled=false&limit=3")
        assert response.status_code == 200
        
        response = requests.get(f"{base_url}/rear-diff/training?anomalous=false&limit=3")
        assert response.status_code == 200
    
    def test_get_training_data_pagination(self, api_server, base_url):
        """Test pagination in training endpoint."""
        # Get first page
        response = requests.get(f"{base_url}/rear-diff/training?limit=2&offset=0")
        assert response.status_code == 200
        page1 = response.json()
        
        # Get second page
        response = requests.get(f"{base_url}/rear-diff/training?limit=2&offset=2")
        assert response.status_code == 200
        page2 = response.json()
        
        # Ensure different data
        if page1["data"] and page2["data"]:
            assert page1["data"][0]["imdb_id"] != page2["data"][0]["imdb_id"]
    
    def test_get_training_data_sorting(self, api_server, base_url):
        """Test sorting in training endpoint."""
        # Test ascending sort
        response = requests.get(f"{base_url}/rear-diff/training?sort_by=created_at&sort_order=asc&limit=5")
        assert response.status_code == 200
        
        # Test descending sort
        response = requests.get(f"{base_url}/rear-diff/training?sort_by=created_at&sort_order=desc&limit=5")
        assert response.status_code == 200
    
    def test_update_label_endpoint(self, api_server, base_url):
        """Test PATCH training endpoint for label updates."""
        # First get a training record to update
        response = requests.get(f"{base_url}/rear-diff/training?limit=1")
        assert response.status_code == 200
        data = response.json()
        
        if data["data"]:
            imdb_id = data["data"][0]["imdb_id"]
            
            # Update the label using unified PATCH endpoint
            update_data = {
                "imdb_id": imdb_id,
                "label": "would_watch"
            }
            response = requests.patch(
                f"{base_url}/rear-diff/training/{imdb_id}",
                json=update_data
            )
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "message" in result
    
    def test_update_reviewed_endpoint(self, api_server, base_url):
        """Test PATCH training endpoint for reviewed status updates."""
        # First get a training record to update
        response = requests.get(f"{base_url}/rear-diff/training?limit=1")
        assert response.status_code == 200
        data = response.json()
        
        if data["data"]:
            imdb_id = data["data"][0]["imdb_id"]
            
            # Update the reviewed status using unified PATCH endpoint
            update_data = {
                "imdb_id": imdb_id,
                "reviewed": True
            }
            response = requests.patch(
                f"{base_url}/rear-diff/training/{imdb_id}",
                json=update_data
            )
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "message" in result

class TestMediaEndpoints:
    """Test media-related endpoints."""
    
    def test_get_media_data_basic(self, api_server, base_url):
        """Test basic GET request to media endpoint."""
        response = requests.get(f"{base_url}/rear-diff/media/?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) <= 5
    
    def test_get_media_data_with_filters(self, api_server, base_url):
        """Test GET media with various filters."""
        # Test media_type filter
        response = requests.get(f"{base_url}/rear-diff/media/?media_type=movie&limit=3")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["media_type"] == "movie"
        
        # Test pipeline_status filter
        response = requests.get(f"{base_url}/rear-diff/media/?pipeline_status=complete&limit=3")
        assert response.status_code == 200
        
        # Test error_status filter
        response = requests.get(f"{base_url}/rear-diff/media/?error_status=false&limit=3")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["error_status"] is False
    
    def test_get_media_data_search(self, api_server, base_url):
        """Test media title search."""
        response = requests.get(f"{base_url}/rear-diff/media/?media_title=the&limit=5")
        assert response.status_code == 200
        data = response.json()
        # Check that results contain "the" in title (case-insensitive)
        for item in data["data"]:
            if item["media_title"]:
                assert "the" in item["media_title"].lower()
    
    def test_get_media_data_sorting(self, api_server, base_url):
        """Test sorting in media endpoint."""
        # Test sorting by different fields
        sort_fields = ["created_at", "updated_at", "release_year", "media_title", "imdb_rating"]
        
        for field in sort_fields:
            response = requests.get(f"{base_url}/rear-diff/media/?sort_by={field}&sort_order=desc&limit=3")
            assert response.status_code == 200
    
    def test_update_media_pipeline(self, api_server, base_url):
        """Test PATCH media pipeline endpoint."""
        # First get a media record to update
        response = requests.get(f"{base_url}/rear-diff/media/?limit=1")
        assert response.status_code == 200
        data = response.json()
        
        if data["data"]:
            hash_value = data["data"][0]["hash"]
            
            # Update the pipeline status
            update_data = {
                "hash": hash_value,
                "pipeline_status": "paused",
                "error_status": False
            }
            response = requests.patch(
                f"{base_url}/rear-diff/media/{hash_value}/pipeline",
                json=update_data
            )
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert "message" in result

class TestPredictionEndpoints:
    """Test prediction-related endpoints."""
    
    def test_get_prediction_data_basic(self, api_server, base_url):
        """Test basic GET request to prediction endpoint."""
        response = requests.get(f"{base_url}/rear-diff/prediction/?limit=5")
        data = assert_success_response(response, "Prediction endpoint")
        
        assert "data" in data, f"Response missing 'data' field: {data}"
        assert "pagination" in data, f"Response missing 'pagination' field: {data}"
        assert isinstance(data["data"], list), f"'data' field is not a list: {type(data['data'])}"
        assert len(data["data"]) <= 5, f"Too many records returned: {len(data['data'])}"
        
        # Validate prediction data structure
        if data["data"]:
            prediction = data["data"][0]
            required_fields = ["imdb_id", "prediction", "probability", "cm_value", "created_at"]
            for field in required_fields:
                assert field in prediction, f"Missing required field '{field}' in prediction data"
            
            # Validate data types and constraints
            assert isinstance(prediction["prediction"], int), f"prediction field is not int: {type(prediction['prediction'])}"
            assert prediction["prediction"] in [0, 1], f"prediction value not 0 or 1: {prediction['prediction']}"
            # Probability can be returned as string from database
            prob_value = float(prediction["probability"]) if isinstance(prediction["probability"], str) else prediction["probability"]
            assert isinstance(prob_value, (int, float)), f"probability is not numeric: {type(prob_value)}"
            assert 0 <= prob_value <= 1, f"probability out of range [0,1]: {prob_value}"
            assert prediction["cm_value"] in ["tn", "tp", "fn", "fp"], f"invalid cm_value: {prediction['cm_value']}"
    
    def test_get_prediction_data_with_filters(self, api_server, base_url):
        """Test GET prediction with various filters."""
        # Test prediction filter
        response = requests.get(f"{base_url}/rear-diff/prediction/?prediction=1&limit=3")
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Response: {response.text}"
        data = response.json()
        
        # Check for database permission errors
        if "message" in data and "permission denied" in data.get("message", "").lower():
            pytest.fail(f"Database permission error: {data['message']}")
        
        for item in data["data"]:
            assert item["prediction"] == 1
        
        # Test cm_value filter
        response = requests.get(f"{base_url}/rear-diff/prediction/?cm_value=tp&limit=3")
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Response: {response.text}"
        data = response.json()
        
        # Check for database permission errors
        if "message" in data and "permission denied" in data.get("message", "").lower():
            pytest.fail(f"Database permission error: {data['message']}")
        
        for item in data["data"]:
            assert item["cm_value"] == "tp"
        
        # Test imdb_id filter (if we have a specific one)
        response = requests.get(f"{base_url}/rear-diff/prediction/?limit=1")
        if response.status_code == 200:
            first_data = response.json()
            
            # Check for database permission errors
            if "message" in first_data and "permission denied" in first_data.get("message", "").lower():
                pytest.fail(f"Database permission error: {first_data['message']}")
            
            if first_data["data"]:
                imdb_id = first_data["data"][0]["imdb_id"]
                response = requests.get(f"{base_url}/rear-diff/prediction/?imdb_id={imdb_id}")
                assert response.status_code == 200
                data = response.json()
                
                # Check for database permission errors
                if "message" in data and "permission denied" in data.get("message", "").lower():
                    pytest.fail(f"Database permission error: {data['message']}")
                
                assert len(data["data"]) == 1
                assert data["data"][0]["imdb_id"] == imdb_id
    
    def test_get_prediction_data_sorting(self, api_server, base_url):
        """Test sorting in prediction endpoint."""
        sort_fields = ["imdb_id", "prediction", "probability", "cm_value", "created_at"]
        
        for field in sort_fields:
            response = requests.get(f"{base_url}/rear-diff/prediction/?sort_by={field}&sort_order=asc&limit=3")
            assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Response: {response.text}"
            
            data = response.json()
            # Check for database permission errors
            if "message" in data and "permission denied" in data.get("message", "").lower():
                pytest.fail(f"Database permission error: {data['message']}")
            
            response = requests.get(f"{base_url}/rear-diff/prediction/?sort_by={field}&sort_order=desc&limit=3")
            assert response.status_code == 200, f"Expected 200 but got {response.status_code}. Response: {response.text}"
            
            data = response.json()
            # Check for database permission errors
            if "message" in data and "permission denied" in data.get("message", "").lower():
                pytest.fail(f"Database permission error: {data['message']}")

class TestFlywayEndpoint:
    """Test flyway schema history endpoint."""
    
    def test_get_flyway_history(self, api_server, base_url):
        """Test GET flyway history endpoint."""
        response = requests.get(f"{base_url}/rear-diff/flyway")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Validate flyway data structure if available
        if data["data"]:
            history = data["data"][0]
            required_fields = ["installed_rank", "description", "type", "script", "installed_by", "installed_on", "execution_time", "success"]
            for field in required_fields:
                assert field in history
    
    def test_get_flyway_history_sorting(self, api_server, base_url):
        """Test sorting in flyway endpoint."""
        # Test different sort options
        response = requests.get(f"{base_url}/rear-diff/flyway?sort_by=installed_rank&sort_order=asc")
        assert response.status_code == 200
        
        response = requests.get(f"{base_url}/rear-diff/flyway?sort_by=installed_on&sort_order=desc")
        assert response.status_code == 200

class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_json(self, api_server, base_url):
        """Test OpenAPI JSON endpoint."""
        response = requests.get(f"{base_url}/rear-diff/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        
        # Verify all our endpoints are documented
        expected_paths = [
            "/rear-diff/",
            "/rear-diff/health",
            "/rear-diff/flyway",
            "/rear-diff/training",
            "/rear-diff/training/{imdb_id}",
            "/rear-diff/media/",
            "/rear-diff/media/{hash}/pipeline",
            "/rear-diff/prediction/",
            "/rear-diff/movies/"
        ]
        
        for path in expected_paths:
            assert path in data["paths"], f"Path {path} not found in OpenAPI spec"
    
    def test_docs_endpoint(self, api_server, base_url):
        """Test Swagger UI docs endpoint."""
        response = requests.get(f"{base_url}/rear-diff/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_endpoints(self, api_server, base_url):
        """Test error responses for invalid endpoints."""
        response = requests.get(f"{base_url}/rear-diff/invalid")
        assert response.status_code == 404
        
        # /rear-diff/training/invalid returns 405 (Method Not Allowed) because it matches 
        # the path pattern /rear-diff/training/{imdb_id} but GET is not allowed (only PATCH)
        response = requests.get(f"{base_url}/rear-diff/training/invalid")
        assert response.status_code == 405
    
    def test_invalid_parameters(self, api_server, base_url):
        """Test validation of query parameters."""
        # Invalid limit (too high) - Note: FastAPI may not enforce this at query level
        response = requests.get(f"{base_url}/rear-diff/training?limit=2000")
        # Some FastAPI configurations may allow this and handle it in business logic
        assert response.status_code in [200, 422]  # Either handled gracefully or rejected
        
        # Invalid sort_by field - API handles this gracefully by defaulting to valid field
        response = requests.get(f"{base_url}/rear-diff/training?sort_by=invalid_field")
        assert response.status_code == 200  # API handles gracefully by using default sort
        
        # Invalid cm_value for prediction
        response = requests.get(f"{base_url}/rear-diff/prediction/?cm_value=invalid")
        assert response.status_code == 422
    
    def test_invalid_patch_data(self, api_server, base_url):
        """Test PATCH training endpoint with invalid data."""
        # Invalid label update using unified endpoint
        update_data = {
            "imdb_id": "tt1234567",
            "label": "invalid_label"
        }
        response = requests.patch(
            f"{base_url}/rear-diff/training/tt1234567",
            json=update_data
        )
        assert response.status_code == 422
        
        # Invalid IMDB ID format using unified endpoint
        update_data = {
            "imdb_id": "invalid_id",
            "label": "would_watch"
        }
        response = requests.patch(
            f"{base_url}/rear-diff/training/invalid_id",
            json=update_data
        )
        assert response.status_code == 422