# test/conftest.py
"""Pytest configuration and fixtures for integration tests."""
import pytest
import multiprocessing
import time
import uvicorn
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Load environment variables from .env file - same as deployed API
from dotenv import load_dotenv
load_dotenv()

from app.main import app

@pytest.fixture(scope="session")
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture(scope="session")
def base_url():
    """Base URL for the API."""
    return "http://127.0.0.1:8001"

@pytest.fixture(scope="session")
def api_server():
    """Start the API server in a separate process for integration testing."""
    def run_server():
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8001,
            log_level="info"
        )
    
    # Start server in a separate process
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    # Wait for server to start
    time.sleep(3)
    
    yield
    
    # Cleanup: terminate the server process
    server_process.terminate()
    server_process.join(timeout=5)
    if server_process.is_alive():
        server_process.kill()

@pytest.fixture(scope="session")
async def async_client(api_server, base_url):
    """Create an async HTTP client for testing."""
    async with AsyncClient(base_url=base_url) as client:
        yield client