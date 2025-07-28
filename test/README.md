# Integration Tests

This directory contains comprehensive integration tests for the Rear Differential API that test all endpoints against the real dev database.

## Overview

The integration test suite provides **comprehensive end-to-end validation** of the entire Rear Differential API by:

### 🏗️ **Real Environment Testing**
- ✅ Spins up the actual FastAPI server locally (port 8001)
- 🗄️ Connects to the real dev PostgreSQL database using production credentials
- 🔍 Tests every single endpoint with real data and real database constraints
- 📊 Validates complete data flow from API → Database → Response

### 🛡️ **Robust Error Detection**
- 🚨 **Server Errors**: Fails on any 5xx status codes (500, 502, 503, etc.)
- ⚠️ **Client Errors**: Detects unexpected 4xx responses  
- 🔐 **Permission Issues**: Catches database permission denied errors
- 📝 **Error Messages**: Scans response content for error indicators
- 🔗 **Infrastructure Problems**: Identifies connectivity and configuration issues

### 📋 **Comprehensive API Coverage**
- **Health & Core**: `/health`, `/`, `/docs`, `/openapi.json`
- **Training Data**: GET with filtering/pagination, PATCH label updates, PATCH reviewed status
- **Media Management**: GET with search/filters, PATCH pipeline status updates  
- **ML Predictions**: GET with filtering by prediction/cm_value/imdb_id
- **Schema History**: Flyway migration tracking
- **Error Handling**: Invalid parameters, malformed requests, edge cases

### 🔍 **Deep Validation**
- **Response Structure**: Verifies JSON schema compliance
- **Data Types**: Validates field types and constraints (probability 0-1, prediction 0/1, etc.)
- **Business Logic**: Ensures filtering, sorting, and pagination work correctly
- **CRUD Operations**: Tests both read and write operations with real data persistence

This approach catches **integration issues that unit tests miss**, including database connectivity, permissions, data validation, API contract compliance, and infrastructure configuration problems.

## Test Structure

- `conftest.py` - Pytest configuration and fixtures
- `test_integration.py` - Main integration test suite (23 comprehensive tests)
- `requirements.txt` - Test dependencies
- `pytest.ini` - Pytest configuration
- `run_tests.py` - Test runner script

## Running Tests

### Option 1: Using the test runner script
```bash
cd /infra/media/rear-differential
python test/run_tests.py
```

### Option 2: Direct pytest execution
```bash
cd /infra/media/rear-differential
pip install -r test/requirements.txt
python -m pytest test/ -v
```

### Option 3: Run specific test classes
```bash
# Test only health endpoints
python -m pytest test/test_integration.py::TestHealthAndRoot -v

# Test only training endpoints
python -m pytest test/test_integration.py::TestTrainingEndpoints -v

# Test only prediction endpoints
python -m pytest test/test_integration.py::TestPredictionEndpoints -v
```

## Test Coverage

The integration tests cover:

### Core Endpoints
- ✅ Health check (`/rear-diff/health`)
- ✅ Root endpoint (`/rear-diff/`)
- ✅ API documentation (`/rear-diff/docs`, `/rear-diff/openapi.json`)

### Training Endpoints
- ✅ GET `/rear-diff/training` with filtering, pagination, sorting
- ✅ PATCH `/rear-diff/training/{imdb_id}/label` (label updates)
- ✅ PATCH `/rear-diff/training/{imdb_id}/reviewed` (reviewed status updates)

### Media Endpoints
- ✅ GET `/rear-diff/media/` with filtering, pagination, sorting, search
- ✅ PATCH `/rear-diff/media/{hash}/pipeline` (pipeline status updates)

### Prediction Endpoints
- ✅ GET `/rear-diff/prediction/` with filtering, pagination, sorting

### Flyway Endpoint
- ✅ GET `/rear-diff/flyway` (schema history)

### Error Handling
- ✅ 404 responses for invalid endpoints
- ✅ 422 validation errors for invalid parameters
- ✅ PATCH endpoint validation

## Database Connection

Tests connect to the real dev database using these credentials:
- Host: 192.168.50.2:31434
- Username: x81-test
- Database: postgres

The tests perform read operations and some limited write operations (label/reviewed updates) but do not create or delete data.

## Test Features

- **Real API Server**: Spins up the actual FastAPI server on localhost:8001
- **Real Database**: Tests against the actual dev database
- **Comprehensive Coverage**: Tests all endpoints with various parameters
- **Data Validation**: Validates response structure and data types
- **Error Testing**: Tests error conditions and validation
- **Filtering & Pagination**: Tests all query parameters and sorting options